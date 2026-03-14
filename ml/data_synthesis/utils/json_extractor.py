"""
Robust JSON extraction from LLM responses.

Handles multiple output formats:
- Direct JSON
- Markdown-wrapped JSON (```json...```)
- Extra whitespace
"""

import json
import re
from typing import Dict, Any


def extract_json(text: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response using multi-strategy approach.

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON dictionary

    Raises:
        ValueError: If all extraction strategies fail
    """
    # Strategy 1: Direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_block_pattern, text, re.DOTALL)

    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Strategy 3: Regex extract first JSON object
    json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_object_pattern, text, re.DOTALL)

    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # All strategies failed
    raise ValueError(f"Failed to extract JSON from response: {text[:200]}...")


def validate_sample_schema(data: Dict[str, Any]) -> bool:
    """
    Validate that extracted JSON matches expected schema.

    Expected schema:
    {
        "sentence": str,
        "severity_label": str (one of: Correct, Outdated, Biased, Potentially Offensive, Factually Incorrect),
        "explanation": str
    }

    Args:
        data: Parsed JSON dictionary

    Returns:
        True if valid, False otherwise
    """
    required_fields = {"sentence", "severity_label", "explanation"}
    valid_severity_labels = {
        "Correct",
        "Outdated",
        "Biased",
        "Potentially Offensive",
        "Factually Incorrect"
    }

    # Check required fields exist
    if not all(field in data for field in required_fields):
        return False

    # Check field types
    if not all(isinstance(data[field], str) for field in required_fields):
        return False

    # Check severity label is valid
    if data["severity_label"] not in valid_severity_labels:
        return False

    # Check minimum content length
    if len(data["sentence"].strip()) < 10:
        return False

    if len(data["explanation"].strip()) < 20:
        return False

    return True
