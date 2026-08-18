"""BIO label schema + the text<->span<->BIO conversion shared by every stage
of the NER pipeline: weak-label bootstrapping, hand-correction, fine-tuning,
and the regex-vs-model benchmark all tag against this exact schema.
"""

from __future__ import annotations

import re

LABEL_LIST = [
    "O",
    "B-STREET", "I-STREET",
    "B-LANDMARK", "I-LANDMARK",
    "B-BUSINESS", "I-BUSINESS",
    "B-TIME", "I-TIME",
    "B-ACTIVITY", "I-ACTIVITY",
]
LABEL2ID = {label: i for i, label in enumerate(LABEL_LIST)}
ID2LABEL = {i: label for i, label in enumerate(LABEL_LIST)}

# Maps the regex extractor's dict keys (app.services.entity_extraction) to
# our NER tag categories. "places" -> LANDMARK because the regex extractor
# uses "places" for parks/stations/schools/etc., which is what LANDMARK means
# here.
CATEGORY_TO_TAG = {
    "streets": "STREET",
    "places": "LANDMARK",
    "businesses": "BUSINESS",
    "times": "TIME",
    "activities": "ACTIVITY",
}

WORD_PATTERN = re.compile(r"\S+")


def tokenize_with_spans(text: str) -> list[tuple[str, int, int]]:
    """Whitespace tokenization with character offsets.

    Deliberately simple (word-level, not subword) -- the fine-tuning script
    re-tokenizes with the model's own tokenizer and aligns subwords back to
    these word-level tags via word_ids(), which is the standard way to train
    a transformer token classifier without hand-rolling subword alignment
    here too.
    """
    return [(m.group(), m.start(), m.end()) for m in WORD_PATTERN.finditer(text)]


def _find_spans(text: str, needle: str) -> list[tuple[int, int]]:
    if not needle:
        return []
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    return [(m.start(), m.end()) for m in pattern.finditer(text)]


def weak_label_spans(text: str, entities: dict) -> list[tuple[int, int, str]]:
    """Turn extract_entities()'s output into (start, end, TAG) character spans.

    Overlaps are resolved by preferring the longest match (e.g. "farmers
    market" as LANDMARK should win over a spurious partial "market" match
    under a different category).
    """
    candidates: list[tuple[int, int, str]] = []
    for category, tag in CATEGORY_TO_TAG.items():
        for value in entities.get(category, []):
            for start, end in _find_spans(text, value):
                candidates.append((start, end, tag))

    candidates.sort(key=lambda c: c[1] - c[0], reverse=True)

    taken = [False] * len(text)
    accepted: list[tuple[int, int, str]] = []
    for start, end, tag in candidates:
        if any(taken[start:end]):
            continue
        for i in range(start, end):
            taken[i] = True
        accepted.append((start, end, tag))

    accepted.sort(key=lambda c: c[0])
    return accepted


def spans_to_bio(text: str, spans: list[tuple[int, int, str]]) -> tuple[list[str], list[str]]:
    """Tokenize `text` and assign a BIO tag to each token from `spans`."""
    tokens = tokenize_with_spans(text)
    tags = ["O"] * len(tokens)

    for s_start, s_end, s_tag in spans:
        overlapping = [
            i for i, (_, w_start, w_end) in enumerate(tokens)
            if w_start < s_end and w_end > s_start
        ]
        for j, idx in enumerate(overlapping):
            tags[idx] = ("B-" if j == 0 else "I-") + s_tag

    words = [w for w, _, _ in tokens]
    return words, tags


def entities_to_bio(text: str, entities: dict) -> tuple[list[str], list[str]]:
    spans = weak_label_spans(text, entities)
    return spans_to_bio(text, spans)
