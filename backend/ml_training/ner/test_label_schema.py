from ner.label_schema import entities_to_bio, tokenize_with_spans


def test_tokenize_with_spans_basic():
    tokens = tokenize_with_spans("Market Street coffee")
    assert [t[0] for t in tokens] == ["Market", "Street", "coffee"]
    assert tokens[0][1:] == (0, 6)
    assert tokens[1][1:] == (7, 13)


def test_single_word_entity_gets_b_tag():
    text = "Grabbing coffee before work"
    entities = {"activities": ["coffee"]}
    words, tags = entities_to_bio(text, entities)
    assert words == ["Grabbing", "coffee", "before", "work"]
    assert tags == ["O", "B-ACTIVITY", "O", "O"]


def test_multi_word_entity_gets_b_then_i_tags():
    text = "Coffee on Market Street this morning"
    entities = {"streets": ["Market Street"], "activities": ["coffee"]}
    words, tags = entities_to_bio(text, entities)
    assert words == ["Coffee", "on", "Market", "Street", "this", "morning"]
    assert tags == ["B-ACTIVITY", "O", "B-STREET", "I-STREET", "O", "O"]


def test_overlapping_entities_longest_span_wins():
    text = "Meet me at the farmers market"
    # "market" alone would match as a spurious STREET-suffix-style entity in
    # some regex configs; "farmers market" as a LANDMARK should win since
    # it's the longer match.
    entities = {"streets": ["market"], "places": ["farmers market"]}
    words, tags = entities_to_bio(text, entities)
    assert tags[-2:] == ["B-LANDMARK", "I-LANDMARK"]


def test_repeated_entity_tags_every_occurrence():
    text = "Coffee at Starbucks, then more coffee, always Starbucks"
    entities = {"businesses": ["Starbucks"], "activities": ["coffee"]}
    words, tags = entities_to_bio(text, entities)
    starbucks_tags = [tag for word, tag in zip(words, tags) if word.startswith("Starbucks")]
    assert starbucks_tags == ["B-BUSINESS", "B-BUSINESS"]


def test_no_entities_all_o():
    words, tags = entities_to_bio("Just a normal day", {})
    assert tags == ["O"] * len(words)


def test_empty_text():
    words, tags = entities_to_bio("", {"streets": ["Market Street"]})
    assert words == []
    assert tags == []
