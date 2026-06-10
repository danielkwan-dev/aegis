"""Fine-tuned DistilBERT NER inference (ONNX + BIO decode) -- the "NER" stage
of the detect->crop->preprocess->OCR->NER cascade, and also run directly on
caption text.

Deliberately uses onnxruntime + the standalone `tokenizers` library, not
`transformers`/`optimum` -- the serving app only ever loads exported ONNX
weights, it never needs torch/transformers/datasets at request time (those
stay training-only, in ml_training/requirements.txt). That means the BIO
label schema and word-level tokenization here are a small, deliberate
duplication of ml_training/ner/label_schema.py -- the two must stay in sync
by hand since they live in separate venvs/packages; label_schema.py is the
source of truth (it's what the model was actually trained against).

Falls back entirely to the regex/keyword extractor in entity_extraction.py
when no fine-tuned model has been trained/published yet (`ner_model_dir`
unset, or the exported files aren't there) -- same graceful-degradation
pattern as app.services.detection.SignageDetector.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

from app.services.entity_extraction import extract_entities

# Mirrors ml_training/ner/label_schema.py -- must match what the model was
# trained on exactly (this determines how logits get decoded into tags).
LABEL_LIST = [
    "O",
    "B-STREET", "I-STREET",
    "B-LANDMARK", "I-LANDMARK",
    "B-BUSINESS", "I-BUSINESS",
    "B-TIME", "I-TIME",
    "B-ACTIVITY", "I-ACTIVITY",
]
ID2LABEL = {i: label for i, label in enumerate(LABEL_LIST)}

# Same category names entity_extraction.extract_entities() uses. "places" is
# NER's LANDMARK (parks/stations/schools/etc, matching entity_extraction's
# use of "places" for that bucket).
CATEGORY_TO_TAG = {
    "streets": "STREET",
    "places": "LANDMARK",
    "businesses": "BUSINESS",
    "times": "TIME",
    "activities": "ACTIVITY",
}
TAG_TO_CATEGORY = {tag: category for category, tag in CATEGORY_TO_TAG.items()}

WORD_PATTERN = re.compile(r"\S+")


def tokenize_with_spans(text: str) -> list[tuple[str, int, int]]:
    """Whitespace tokenization with character offsets -- must match
    ml_training/ner/label_schema.py's tokenize_with_spans() exactly, since
    that's the word-level granularity the model's labels were aligned to."""
    return [(m.group(), m.start(), m.end()) for m in WORD_PATTERN.finditer(text)]


def decode_bio_tags(word_spans: list[tuple[str, int, int]], tags: list[str]) -> dict:
    """Group consecutive B-/I- tagged words into entities, keyed by the same
    category names entity_extraction.extract_entities() uses.

    `word_spans`: (word, char_start, char_end) tuples, e.g. from
    tokenize_with_spans(). `tags`: one BIO tag per word, same length/order.
    Malformed sequences (an "I-" with no preceding matching "B-") are
    treated leniently as starting a new entity rather than dropped.
    """
    result: dict[str, list[str]] = {category: [] for category in TAG_TO_CATEGORY.values()}
    current_words: list[str] = []
    current_tag: str | None = None

    def flush() -> None:
        if current_words and current_tag in TAG_TO_CATEGORY:
            result[TAG_TO_CATEGORY[current_tag]].append(" ".join(current_words))

    for (word, _, _), tag in zip(word_spans, tags):
        if tag == "O":
            flush()
            current_words, current_tag = [], None
        elif tag.startswith("B-"):
            flush()
            current_tag, current_words = tag[2:], [word]
        elif tag.startswith("I-") and tag[2:] == current_tag:
            current_words.append(word)
        else:
            # Orphan I- tag, or I- for a different category than the run in
            # progress -- start a fresh entity rather than silently merging
            # or dropping it.
            flush()
            current_tag, current_words = tag[2:], [word]
    flush()

    return result


class NERExtractor:
    """Runs the fine-tuned DistilBERT NER model, if one is configured and
    present.

    `session`/`tokenizer` are injectable for testing (pass an object
    exposing `.get_inputs()`/`.run()` like onnxruntime.InferenceSession, and
    an object exposing `.encode(words, is_pretokenized=True)` like
    tokenizers.Tokenizer) -- production code just passes `model_dir` and
    lets it load lazily.
    """

    def __init__(self, model_dir: str | Path | None, *, session: Any | None = None, tokenizer: Any | None = None):
        self._model_dir = Path(model_dir) if model_dir else None
        self._session = session
        self._tokenizer = tokenizer
        self._loaded = session is not None and tokenizer is not None

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._model_dir or not self._model_dir.exists():
            return

        # optimum's ORTQuantizer names its output "model_quantized.onnx", not
        # "model.onnx" -- check both rather than assuming a single fixed name.
        onnx_path = next(
            (p for p in (self._model_dir / "model.onnx", self._model_dir / "model_quantized.onnx") if p.exists()),
            None,
        )
        tokenizer_path = self._model_dir / "tokenizer.json"
        if onnx_path is None or not tokenizer_path.exists():
            return

        import onnxruntime as ort
        from tokenizers import Tokenizer

        self._session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))

    @property
    def available(self) -> bool:
        self._ensure_loaded()
        return self._session is not None and self._tokenizer is not None

    def extract(self, text: str) -> dict:
        """Returns the same category-dict shape as entity_extraction's
        extract_entities(), for the categories the NER model covers
        (streets/places/businesses/times/activities). Coordinates/days/
        time_context aren't in the model's label schema -- callers merge
        those in from the regex extractor separately (see
        extract_entities_hybrid)."""
        self._ensure_loaded()
        empty = {category: [] for category in TAG_TO_CATEGORY.values()}
        if self._session is None or self._tokenizer is None:
            return empty

        word_spans = tokenize_with_spans(text)
        if not word_spans:
            return empty
        words = [w for w, _, _ in word_spans]

        encoding = self._tokenizer.encode(words, is_pretokenized=True)
        input_ids = np.array([encoding.ids], dtype=np.int64)
        attention_mask = np.array([encoding.attention_mask], dtype=np.int64)

        input_names = {inp.name for inp in self._session.get_inputs()}
        feed = {k: v for k, v in {"input_ids": input_ids, "attention_mask": attention_mask}.items() if k in input_names}

        logits = self._session.run(None, feed)[0]  # (1, seq_len, num_labels)
        tag_ids = np.argmax(logits[0], axis=-1)

        # Only the first subword token of each word carries that word's tag
        # (mirrors training's -100-masking of non-first subwords).
        word_tags: dict[int, str] = {}
        for token_idx, word_id in enumerate(encoding.word_ids):
            if word_id is None or word_id in word_tags:
                continue
            word_tags[word_id] = ID2LABEL.get(int(tag_ids[token_idx]), "O")

        tags = [word_tags.get(i, "O") for i in range(len(words))]
        return decode_bio_tags(word_spans, tags)


_default_extractor: NERExtractor | None = None


def _get_default_extractor() -> NERExtractor:
    global _default_extractor
    if _default_extractor is None:
        from app.core.config import get_settings

        _default_extractor = NERExtractor(get_settings().ner_model_dir)
    return _default_extractor


def extract_entities_hybrid(text: str, *, extractor: NERExtractor | None = None) -> dict:
    """extract_entities(), upgraded to use the fine-tuned NER model for the
    categories it covers, once one is available -- falls back to the plain
    regex extractor entirely (identical output to calling extract_entities()
    directly) until a trained model is configured."""
    baseline = extract_entities(text)
    extractor = extractor or _get_default_extractor()
    if not extractor.available:
        return baseline

    ml_entities = extractor.extract(text)
    merged = dict(baseline)
    merged.update(ml_entities)
    return merged
