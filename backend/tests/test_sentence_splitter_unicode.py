from app.modules.analysis.sentence_splitter import split_with_offsets

def test_mixed_hebrew_english():
    """
    Test edge-case: A mix of Hebrew and English.
    Ensures that multi-byte language characters combined with Latin alphabet
    do not interfere with offset accuracy.
    """
    text = 'שלום עולם! This is a test.'
    results = split_with_offsets(text, language='he')

    assert len(results) > 0
    for sentence, start, end in results:
        # Assert slicing original text matches the stripped string exactly
        assert text[start:end] == sentence


def test_multiple_spaces():
    """
    Test edge-case: Multiple spaces between sentences.
    Verifies that excess whitespace doesn't skew index logic.
    """
    text = 'משפט ראשון.      משפט שני.'
    results = split_with_offsets(text, language='he')

    assert len(results) > 0
    for sentence, start, end in results:
        # Assert slicing original text matches the stripped string exactly
        assert text[start:end] == sentence


def test_punctuation_within_hebrew():
    """
    Test edge-case: Punctuation within Hebrew.
    Ensures punctuation acts cleanly within a non-Latin string.
    """
    text = 'האם זה עובד? כן, זה עובד!'
    results = split_with_offsets(text, language='he')

    assert len(results) > 0
    for sentence, start, end in results:
        # Assert slicing original text matches the stripped string exactly
        assert text[start:end] == sentence


def test_mixed_rtl_ltr_with_numbers():
    """
    Test edge-case: Mixed RTL/LTR with Numbers
    Checks how it handles numbers and quotes within Hebrew.
    """
    text = 'המחיר הוא 100 ש"ח לכל יחידה. Delivery is free.'
    results = split_with_offsets(text, language='he')

    assert len(results) > 0
    for sentence, start, end in results:
        assert text[start:end] == sentence


def test_parentheses_and_punctuation():
    """
    Test edge-case: Parentheses and Punctuation
    Ensures brackets don't throw off the offset.
    """
    text = 'זה משפט (עם סוגריים). וזה עוד משפט!'
    results = split_with_offsets(text, language='he')

    assert len(results) > 0
    for sentence, start, end in results:
        assert text[start:end] == sentence


def test_sentence_starting_english_ending_hebrew():
    """
    Test edge-case: Sentence starting with English and ending with Hebrew
    """
    text = 'Wait a minute, זה אמור לעבוד.'
    results = split_with_offsets(text, language='he')

    assert len(results) > 0
    for sentence, start, end in results:
        assert text[start:end] == sentence


def test_only_hebrew_punctuation():
    """
    Test edge-case: Only Hebrew Punctuation
    """
    text = '...מה? באמת!!!'
    results = split_with_offsets(text, language='he')

    assert len(results) > 0
    for sentence, start, end in results:
        assert text[start:end] == sentence
