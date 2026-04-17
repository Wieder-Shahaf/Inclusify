"""
Sentence splitter with character offset tracking.

Uses pysbd for multilingual sentence boundary detection.
Returns sentences with their start/end character offsets in the original text.
"""

import pysbd


# Languages supported by pysbd
SUPPORTED_LANGUAGES = {
    'bg', 'fa', 'nl', 'am', 'de', 'zh', 'ur', 'en', 'sk', 'da',
    'hi', 'my', 'ru', 'kk', 'pl', 'es', 'hy', 'el', 'ja', 'ar', 'it', 'fr', 'mr'
}


def split_with_offsets(text: str, language: str = "en") -> list[tuple[str, int, int]]:
    """
    Split text into sentences with character offsets.

    Args:
        text: Input text to split
        language: Language code ('en', 'he', etc.)

    Returns:
        List of (sentence, start_offset, end_offset) tuples.
        Offsets are character positions in the original text.
    """
    if not text:
        return []

    # Fall back to English for unsupported languages (Hebrew 'he' not supported)
    lang_code = language if language in SUPPORTED_LANGUAGES else "en"

    # Use pysbd with clean=False to preserve original text
    segmenter = pysbd.Segmenter(language=lang_code, clean=False)
    sentences = segmenter.segment(text)

    # Calculate offsets by finding each sentence in the original text
    results = []
    search_start = 0

    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue

        # Find where the exact unstripped sentence starts in the original text
        raw_start_idx = text.find(sentence, search_start)
        if raw_start_idx == -1:
            # Fallback: use the current search position
            raw_start_idx = search_start

        # Calculate exact offsets for the stripped portion
        leading_spaces = sentence.find(stripped)
        start_idx = raw_start_idx + leading_spaces
        end_idx = start_idx + len(stripped)

        results.append((stripped, start_idx, end_idx))

        # Move search position past the entire raw sentence
        search_start = raw_start_idx + len(sentence)

    return results


__all__ = ["split_with_offsets"]
