"""Unit tests for JSON extraction utility."""

import pytest
from ml.data_synthesis.utils.json_extractor import extract_json, validate_sample_schema


class TestExtractJSON:
    """Test JSON extraction from various LLM response formats."""

    def test_direct_json(self):
        """Test extraction of direct JSON response."""
        text = '{"sentence": "Test sentence", "severity_label": "Correct", "explanation": "This is a valid explanation"}'
        result = extract_json(text)
        assert result["sentence"] == "Test sentence"
        assert result["severity_label"] == "Correct"
        assert result["explanation"] == "This is a valid explanation"

    def test_json_with_whitespace(self):
        """Test extraction with extra whitespace."""
        text = '''

        {"sentence": "Test sentence", "severity_label": "Biased", "explanation": "Explanation here"}

        '''
        result = extract_json(text)
        assert result["sentence"] == "Test sentence"
        assert result["severity_label"] == "Biased"

    def test_markdown_wrapped_json(self):
        """Test extraction from markdown code block."""
        text = '''```json
{"sentence": "Test sentence", "severity_label": "Outdated", "explanation": "Old terminology used"}
```'''
        result = extract_json(text)
        assert result["sentence"] == "Test sentence"
        assert result["severity_label"] == "Outdated"

    def test_markdown_without_language_tag(self):
        """Test extraction from markdown block without 'json' tag."""
        text = '''```
{"sentence": "Test sentence", "severity_label": "Potentially Offensive", "explanation": "Potentially harmful"}
```'''
        result = extract_json(text)
        assert result["sentence"] == "Test sentence"
        assert result["severity_label"] == "Potentially Offensive"

    def test_json_with_surrounding_text(self):
        """Test extraction when JSON is embedded in other text."""
        text = '''Here is the result:
{"sentence": "Test sentence", "severity_label": "Factually Incorrect", "explanation": "Contradicts evidence"}
End of response.'''
        result = extract_json(text)
        assert result["sentence"] == "Test sentence"
        assert result["severity_label"] == "Factually Incorrect"

    def test_invalid_json(self):
        """Test that invalid JSON raises ValueError."""
        text = "This is not JSON at all"
        with pytest.raises(ValueError, match="Failed to extract JSON"):
            extract_json(text)

    def test_malformed_json(self):
        """Test that malformed JSON raises ValueError."""
        text = '{"sentence": "Missing closing brace", "severity_label": "Correct"'
        with pytest.raises(ValueError, match="Failed to extract JSON"):
            extract_json(text)


class TestValidateSampleSchema:
    """Test schema validation for generated samples."""

    def test_valid_sample(self):
        """Test validation of a valid sample."""
        sample = {
            "sentence": "This is a valid test sentence.",
            "severity_label": "Correct",
            "explanation": "This is a valid explanation with sufficient length."
        }
        assert validate_sample_schema(sample) is True

    def test_all_severity_labels(self):
        """Test validation accepts all valid severity labels."""
        valid_labels = [
            "Correct",
            "Outdated",
            "Biased",
            "Potentially Offensive",
            "Factually Incorrect"
        ]

        for label in valid_labels:
            sample = {
                "sentence": "Test sentence with enough length.",
                "severity_label": label,
                "explanation": "Valid explanation with sufficient content."
            }
            assert validate_sample_schema(sample) is True

    def test_missing_field(self):
        """Test validation fails when required field is missing."""
        sample = {
            "sentence": "Test sentence",
            "severity_label": "Correct"
            # Missing "explanation"
        }
        assert validate_sample_schema(sample) is False

    def test_invalid_severity_label(self):
        """Test validation fails for invalid severity label."""
        sample = {
            "sentence": "Test sentence with enough length.",
            "severity_label": "InvalidLabel",
            "explanation": "Valid explanation with sufficient content."
        }
        assert validate_sample_schema(sample) is False

    def test_wrong_field_type(self):
        """Test validation fails when field has wrong type."""
        sample = {
            "sentence": 123,  # Should be string
            "severity_label": "Correct",
            "explanation": "Valid explanation with sufficient content."
        }
        assert validate_sample_schema(sample) is False

    def test_sentence_too_short(self):
        """Test validation fails for very short sentence."""
        sample = {
            "sentence": "Short",  # Less than 10 chars
            "severity_label": "Correct",
            "explanation": "Valid explanation with sufficient content."
        }
        assert validate_sample_schema(sample) is False

    def test_explanation_too_short(self):
        """Test validation fails for very short explanation."""
        sample = {
            "sentence": "This is a valid test sentence.",
            "severity_label": "Correct",
            "explanation": "Too short"  # Less than 20 chars
        }
        assert validate_sample_schema(sample) is False

    def test_empty_strings(self):
        """Test validation fails for empty strings."""
        sample = {
            "sentence": "",
            "severity_label": "Correct",
            "explanation": ""
        }
        assert validate_sample_schema(sample) is False

    def test_whitespace_only(self):
        """Test validation fails for whitespace-only content."""
        sample = {
            "sentence": "   ",
            "severity_label": "Correct",
            "explanation": "   "
        }
        assert validate_sample_schema(sample) is False
