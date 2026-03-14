#!/usr/bin/env python3
"""Verification script for vLLM implementation.

Tests key components without requiring pytest:
1. JSON extractor with various input formats
2. Schema validation
3. Configuration loading

Usage:
    python scripts/test_vllm_implementation.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly from modules to avoid dependency issues
import importlib.util

# Load json_extractor
spec = importlib.util.spec_from_file_location(
    "json_extractor",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "ml/data_synthesis/utils/json_extractor.py")
)
json_extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(json_extractor_module)
extract_json = json_extractor_module.extract_json
validate_sample_schema = json_extractor_module.validate_sample_schema

# Load config
spec = importlib.util.spec_from_file_location(
    "config",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "ml/data_synthesis/config.py")
)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
VLLM_ENABLED = config_module.VLLM_ENABLED
VLLM_ENDPOINT = config_module.VLLM_ENDPOINT
VLLM_MODEL = config_module.VLLM_MODEL
VLLM_BATCH_SIZE = config_module.VLLM_BATCH_SIZE
VLLM_MAX_THROUGHPUT = config_module.VLLM_MAX_THROUGHPUT
MODEL = config_module.MODEL
MAX_TOKENS = config_module.MAX_TOKENS
TEMPERATURE = config_module.TEMPERATURE


def test_json_extractor():
    """Test JSON extraction functionality."""
    print("Testing JSON Extractor...")
    print("=" * 60)

    # Test 1: Direct JSON
    print("\n1. Testing direct JSON extraction...")
    text1 = '{"sentence": "Test sentence", "severity_label": "Correct", "explanation": "This is a valid explanation"}'
    try:
        result = extract_json(text1)
        assert result["sentence"] == "Test sentence"
        assert result["severity_label"] == "Correct"
        print("   ✓ Direct JSON extraction works")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Test 2: Markdown-wrapped JSON
    print("\n2. Testing markdown-wrapped JSON...")
    text2 = '''```json
{"sentence": "Test sentence", "severity_label": "Biased", "explanation": "Valid explanation here"}
```'''
    try:
        result = extract_json(text2)
        assert result["severity_label"] == "Biased"
        print("   ✓ Markdown-wrapped JSON extraction works")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Test 3: JSON with surrounding text
    print("\n3. Testing JSON with surrounding text...")
    text3 = '''Here is the result:
{"sentence": "Test sentence", "severity_label": "Outdated", "explanation": "Valid explanation text"}
End of response.'''
    try:
        result = extract_json(text3)
        assert result["severity_label"] == "Outdated"
        print("   ✓ JSON extraction from mixed text works")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

    # Test 4: Invalid JSON should raise error
    print("\n4. Testing invalid JSON handling...")
    text4 = "This is not JSON at all"
    try:
        extract_json(text4)
        print("   ✗ Failed: Should have raised ValueError")
        return False
    except ValueError:
        print("   ✓ Invalid JSON correctly raises ValueError")

    print("\n" + "=" * 60)
    print("✓ All JSON extractor tests passed")
    return True


def test_schema_validation():
    """Test schema validation functionality."""
    print("\n\nTesting Schema Validation...")
    print("=" * 60)

    # Test 1: Valid sample
    print("\n1. Testing valid sample...")
    valid_sample = {
        "sentence": "This is a valid test sentence.",
        "severity_label": "Correct",
        "explanation": "This is a valid explanation with sufficient length."
    }
    if validate_sample_schema(valid_sample):
        print("   ✓ Valid sample passes validation")
    else:
        print("   ✗ Valid sample failed validation")
        return False

    # Test 2: All severity labels
    print("\n2. Testing all severity labels...")
    valid_labels = [
        "Correct", "Outdated", "Biased",
        "Potentially Offensive", "Factually Incorrect"
    ]
    for label in valid_labels:
        sample = {
            "sentence": "Test sentence with enough length.",
            "severity_label": label,
            "explanation": "Valid explanation with sufficient content."
        }
        if not validate_sample_schema(sample):
            print(f"   ✗ Failed for label: {label}")
            return False
    print(f"   ✓ All {len(valid_labels)} severity labels validated")

    # Test 3: Missing field
    print("\n3. Testing missing field detection...")
    invalid_sample = {
        "sentence": "Test sentence",
        "severity_label": "Correct"
        # Missing "explanation"
    }
    if not validate_sample_schema(invalid_sample):
        print("   ✓ Missing field correctly detected")
    else:
        print("   ✗ Failed to detect missing field")
        return False

    # Test 4: Invalid severity label
    print("\n4. Testing invalid severity label...")
    invalid_label_sample = {
        "sentence": "Test sentence with enough length.",
        "severity_label": "InvalidLabel",
        "explanation": "Valid explanation with sufficient content."
    }
    if not validate_sample_schema(invalid_label_sample):
        print("   ✓ Invalid severity label correctly rejected")
    else:
        print("   ✗ Failed to reject invalid severity label")
        return False

    # Test 5: Too short sentence
    print("\n5. Testing minimum length requirements...")
    short_sentence = {
        "sentence": "Short",  # Less than 10 chars
        "severity_label": "Correct",
        "explanation": "Valid explanation with sufficient content."
    }
    if not validate_sample_schema(short_sentence):
        print("   ✓ Too-short sentence correctly rejected")
    else:
        print("   ✗ Failed to reject short sentence")
        return False

    print("\n" + "=" * 60)
    print("✓ All schema validation tests passed")
    return True


def test_configuration():
    """Test configuration loading."""
    print("\n\nTesting Configuration...")
    print("=" * 60)

    print(f"\nVLLM_ENABLED: {VLLM_ENABLED}")
    print(f"VLLM_ENDPOINT: {VLLM_ENDPOINT}")
    print(f"VLLM_MODEL: {VLLM_MODEL}")
    print(f"VLLM_BATCH_SIZE: {VLLM_BATCH_SIZE}")
    print(f"VLLM_MAX_THROUGHPUT: {VLLM_MAX_THROUGHPUT}")
    print(f"\nActive MODEL: {MODEL}")
    print(f"Active MAX_TOKENS: {MAX_TOKENS}")
    print(f"Active TEMPERATURE: {TEMPERATURE}")

    if VLLM_ENABLED:
        if MODEL == VLLM_MODEL:
            print("\n✓ Configuration correctly set to vLLM mode")
        else:
            print(f"\n✗ Configuration mismatch: MODEL={MODEL}, expected {VLLM_MODEL}")
            return False
    else:
        print("\n✓ Configuration set to Claude mode (VLLM_ENABLED=false)")

    print("=" * 60)
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("vLLM Implementation Verification")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("JSON Extractor", test_json_extractor()))
    results.append(("Schema Validation", test_schema_validation()))
    results.append(("Configuration", test_configuration()))

    # Summary
    print("\n\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All tests passed! Implementation is ready.")
        print("\nNext steps:")
        print("1. Start vLLM server")
        print("2. Run: python scripts/quick_qwen_test.py")
        print("3. Run: python ml/data_synthesis/synthesize_english.py")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    exit(main())
