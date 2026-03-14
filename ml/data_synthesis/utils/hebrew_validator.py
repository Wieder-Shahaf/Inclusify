"""
Lenient validator for Hebrew translations.

Focus: Translation quality, not strict schema adherence.
We can normalize field names post-processing.
"""

from typing import Dict, Any


def validate_hebrew_translation(data: Dict[str, Any]) -> bool:
    """
    Validate Hebrew translation output (lenient).

    Accepts various field name formats:
    - hebrew_sentence, hebrew_explanation
    - sentence, explanation
    - hebrew, explanation_hebrew
    - Any fields with substantive Hebrew content

    Args:
        data: Parsed JSON from DictaLM

    Returns:
        True if has valid Hebrew content, False otherwise
    """
    if not isinstance(data, dict):
        return False

    # Find sentence field (flexible matching)
    sentence = None
    sentence_keys = ['hebrew_sentence', 'sentence', 'hebrew', 'translated_sentence']
    for key in sentence_keys:
        if key in data and data[key]:
            sentence = data[key]
            break

    # Also check first non-empty string value
    if not sentence:
        for value in data.values():
            if isinstance(value, str) and len(value.strip()) > 10:
                sentence = value
                break

    if not sentence:
        return False

    # Minimum length check (translation should be substantive)
    if len(sentence.strip()) < 10:
        return False

    # Basic Hebrew character check (should contain SOME Hebrew)
    hebrew_chars = sum(1 for c in sentence if 0x0590 <= ord(c) <= 0x05FF)
    if hebrew_chars < 5:  # At least 5 Hebrew characters
        return False

    # Success if we got here
    return True


def extract_hebrew_fields(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract Hebrew sentence and explanation from flexible JSON format.

    Args:
        data: Parsed JSON from DictaLM

    Returns:
        Dict with normalized fields: {'sentence': '...', 'explanation': '...'}
    """
    result = {}

    # Extract sentence (try multiple field names)
    sentence_keys = ['hebrew_sentence', 'sentence', 'hebrew', 'translated_sentence']
    for key in sentence_keys:
        if key in data and data[key]:
            result['sentence'] = data[key].strip()
            break

    # Extract explanation (try multiple field names)
    explanation_keys = ['hebrew_explanation', 'explanation', 'explanation_hebrew', 'translated_explanation']
    for key in explanation_keys:
        if key in data and data[key]:
            result['explanation'] = data[key].strip()
            break

    # If we didn't find explicit fields, use first two string values
    if 'sentence' not in result or 'explanation' not in result:
        string_values = [v for v in data.values() if isinstance(v, str) and len(v.strip()) > 10]
        if len(string_values) >= 2:
            if 'sentence' not in result:
                result['sentence'] = string_values[0].strip()
            if 'explanation' not in result:
                result['explanation'] = string_values[1].strip()

    return result


def quick_hebrew_quality_check(hebrew_text: str) -> Dict[str, Any]:
    """
    Quick quality check for Hebrew text.

    Args:
        hebrew_text: Hebrew text to validate

    Returns:
        Dict with quality metrics
    """
    # Character composition
    total_chars = len(hebrew_text)
    hebrew_chars = sum(1 for c in hebrew_text if 0x0590 <= ord(c) <= 0x05FF)
    english_chars = sum(1 for c in hebrew_text if ord('a') <= ord(c) <= ord('z') or ord('A') <= ord(c) <= ord('Z'))
    arabic_chars = sum(1 for c in hebrew_text if 0x0600 <= ord(c) <= 0x06FF)
    chinese_chars = sum(1 for c in hebrew_text if 0x4E00 <= ord(c) <= 0x9FFF)

    # Allow LGBTQ+ as English exception
    english_exceptions = hebrew_text.count('LGBTQ+') * 6  # "LGBTQ+" = 6 chars
    adjusted_english = max(0, english_chars - english_exceptions)

    hebrew_purity = hebrew_chars / total_chars if total_chars > 0 else 0

    return {
        'hebrew_chars': hebrew_chars,
        'english_chars': adjusted_english,
        'arabic_chars': arabic_chars,
        'chinese_chars': chinese_chars,
        'hebrew_purity': hebrew_purity,
        'has_mixed_languages': (adjusted_english > 5 or arabic_chars > 0 or chinese_chars > 0),
        'quality': 'EXCELLENT' if hebrew_purity > 0.85 and not (adjusted_english > 5 or arabic_chars > 0 or chinese_chars > 0) else
                   'GOOD' if hebrew_purity > 0.70 else
                   'POOR'
    }
