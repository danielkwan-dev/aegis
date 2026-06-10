import numpy as np

from app.services.entity_extraction import extract_entities
from app.services.ner_inference import (
    ID2LABEL,
    NERExtractor,
    decode_bio_tags,
    extract_entities_hybrid,
    tokenize_with_spans,
)


def test_decode_bio_tags_groups_consecutive_b_i_words_into_one_entity():
    spans = tokenize_with_spans("Market Street")
    tags = ["B-STREET", "I-STREET"]

    result = decode_bio_tags(spans, tags)

    assert result["streets"] == ["Market Street"]


def test_decode_bio_tags_splits_separate_b_tagged_entities():
    spans = tokenize_with_spans("gym then Starbucks")
    tags = ["B-ACTIVITY", "O", "B-BUSINESS"]

    result = decode_bio_tags(spans, tags)

    assert result["activities"] == ["gym"]
    assert result["businesses"] == ["Starbucks"]


def test_decode_bio_tags_ignores_o_tags():
    spans = tokenize_with_spans("just a normal caption")
    tags = ["O", "O", "O", "O"]

    result = decode_bio_tags(spans, tags)

    assert all(v == [] for v in result.values())


def test_decode_bio_tags_treats_orphan_i_tag_as_a_new_entity():
    # A malformed sequence (I- with no preceding matching B-) shouldn't crash
    # or get silently dropped -- treat it as starting a new entity.
    spans = tokenize_with_spans("Main Street")
    tags = ["O", "I-STREET"]

    result = decode_bio_tags(spans, tags)

    assert result["streets"] == ["Street"]


def test_decode_bio_tags_covers_every_extract_entities_category():
    # decode_bio_tags's output must be a subset of extract_entities()'s keys
    # so extract_entities_hybrid can merge them without KeyErrors.
    baseline_keys = set(extract_entities("").keys())
    result_keys = set(decode_bio_tags([], []).keys())

    assert result_keys.issubset(baseline_keys)


def test_extractor_unavailable_without_a_model_dir():
    extractor = NERExtractor(model_dir=None)

    assert extractor.available is False
    assert all(v == [] for v in extractor.extract("some text").values())


def test_extractor_unavailable_when_model_dir_does_not_exist():
    extractor = NERExtractor(model_dir="C:/nonexistent/ner-model")

    assert extractor.available is False


def test_extractor_loads_optimum_quantized_filename(tmp_path, monkeypatch):
    # optimum's ORTQuantizer names its output "model_quantized.onnx", not
    # the "model.onnx" name a naive glob might assume -- the loader must
    # recognize both real Colab output shapes.
    (tmp_path / "model_quantized.onnx").write_bytes(b"fake-onnx-bytes")
    (tmp_path / "tokenizer.json").write_text("{}")

    calls = {}

    class _FakeOrt:
        class InferenceSession:
            def __init__(self, path, providers=None):
                calls["onnx_path"] = path

    class _FakeTokenizerModule:
        class Tokenizer:
            @staticmethod
            def from_file(path):
                calls["tokenizer_path"] = path
                return object()

    monkeypatch.setitem(__import__("sys").modules, "onnxruntime", _FakeOrt)
    monkeypatch.setitem(__import__("sys").modules, "tokenizers", _FakeTokenizerModule)

    extractor = NERExtractor(model_dir=tmp_path)

    assert extractor.available is True
    assert calls["onnx_path"].endswith("model_quantized.onnx")


class _FakeInput:
    def __init__(self, name):
        self.name = name


class _FakeEncoding:
    def __init__(self, ids, attention_mask, word_ids):
        self.ids = ids
        self.attention_mask = attention_mask
        self.word_ids = word_ids


class _FakeTokenizer:
    def __init__(self, encoding: _FakeEncoding):
        self._encoding = encoding
        self.last_words = None

    def encode(self, words, is_pretokenized=True):
        self.last_words = words
        return self._encoding


class _FakeSession:
    def __init__(self, logits: np.ndarray):
        self._logits = logits

    def get_inputs(self):
        return [_FakeInput("input_ids"), _FakeInput("attention_mask")]

    def run(self, output_names, input_feed):
        assert "input_ids" in input_feed and "attention_mask" in input_feed
        return [self._logits]


def test_extractor_extract_maps_model_output_to_entity_categories():
    # Two words: "Market", "Street". Tokenizer emits [CLS] Market Street [SEP]
    # as 4 subword tokens (one each, one-to-one for simplicity), word_ids
    # [None, 0, 1, None]. Model should predict B-STREET / I-STREET for them.
    encoding = _FakeEncoding(
        ids=[101, 2001, 2002, 102],
        attention_mask=[1, 1, 1, 1],
        word_ids=[None, 0, 1, None],
    )
    b_street = list(ID2LABEL.values()).index("B-STREET")
    i_street = list(ID2LABEL.values()).index("I-STREET")
    o_tag = list(ID2LABEL.values()).index("O")
    n_labels = len(ID2LABEL)

    logits = np.zeros((1, 4, n_labels), dtype=np.float32)
    logits[0, 0, o_tag] = 10.0       # [CLS] -> O (ignored anyway)
    logits[0, 1, b_street] = 10.0    # "Market" -> B-STREET
    logits[0, 2, i_street] = 10.0    # "Street" -> I-STREET
    logits[0, 3, o_tag] = 10.0       # [SEP] -> O (ignored anyway)

    extractor = NERExtractor(model_dir=None, session=_FakeSession(logits), tokenizer=_FakeTokenizer(encoding))

    assert extractor.available is True
    result = extractor.extract("Market Street")

    assert result["streets"] == ["Market Street"]


def test_extract_entities_hybrid_falls_back_to_pure_regex_without_a_model():
    text = "Coffee at Market Street around 8am, 37.774,-122.419"

    hybrid = extract_entities_hybrid(text, extractor=NERExtractor(model_dir=None))
    baseline = extract_entities(text)

    assert hybrid == baseline


def test_extract_entities_hybrid_prefers_ml_output_for_covered_categories(monkeypatch):
    class _StubExtractor:
        available = True

        def extract(self, text):
            return {"streets": ["ML Street"], "places": [], "businesses": [], "times": [], "activities": []}

    text = "regex would find something totally different here on Main St"
    result = extract_entities_hybrid(text, extractor=_StubExtractor())

    assert result["streets"] == ["ML Street"]


def test_extract_entities_hybrid_keeps_regex_only_categories_even_with_a_model():
    class _StubExtractor:
        available = True

        def extract(self, text):
            return {"streets": [], "places": [], "businesses": [], "times": [], "activities": []}

    text = "Sunday morning at 37.774,-122.419"
    result = extract_entities_hybrid(text, extractor=_StubExtractor())

    # coordinates/days/time_context aren't part of the NER label schema --
    # always come from the regex extractor regardless of model availability.
    assert result["coordinates"] == [{"lat": 37.774, "lon": -122.419}]
    assert "sunday" in result["days"]
