"""Test suite for data preparation pipeline.

Tests validate:
1. Dataset loading from augmented_dataset.csv
2. Stratified splitting preserves class proportions
3. Chat template formatting produces correct Qwen2.5 ChatML format
"""

import os
import sys
import pytest
import pandas as pd
from transformers import AutoTokenizer

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ml.training.prepare_data import load_dataset, stratified_split, format_example_qwen


# Dataset path relative to project root
DATASET_PATH = "data/augmented_dataset.csv"


def test_dataset_loads():
    """Test that augmented_dataset.csv loads correctly with expected structure."""
    df = load_dataset(DATASET_PATH)

    # Verify row count: 988 unique samples (12 duplicates removed)
    assert len(df) == 988, f"Expected 988 unique rows, got {len(df)}"

    # Verify required columns exist
    required_columns = ["Sentence", "Severity Label", "Explanation"]
    for col in required_columns:
        assert col in df.columns, f"Missing required column: {col}"

    # Verify no null values in required columns
    null_counts = df[required_columns].isnull().sum()
    assert null_counts.sum() == 0, f"Found null values: {null_counts[null_counts > 0].to_dict()}"

    # Print class distribution for visibility
    print("\nClass distribution:")
    print(df["Severity Label"].value_counts())
    print(f"\nTotal samples: {len(df)}")


def test_stratified_split():
    """Test that stratified split preserves class proportions in train/val sets."""
    df = load_dataset(DATASET_PATH)

    # Perform 80/20 split
    train_df, val_df = stratified_split(df, test_size=0.2, random_state=42)

    # Verify split sizes (988 unique samples: ~790 train / ~198 val)
    assert len(train_df) + len(val_df) == len(df), "Train + val should equal original dataset size"
    assert 740 <= len(train_df) <= 840, f"Train set should be ~790 rows, got {len(train_df)}"
    assert 148 <= len(val_df) <= 248, f"Val set should be ~198 rows, got {len(val_df)}"

    # Verify no data leakage (no overlap between train/val sentences)
    train_sentences = set(train_df["Sentence"].values)
    val_sentences = set(val_df["Sentence"].values)
    overlap = train_sentences & val_sentences
    assert len(overlap) == 0, f"Found {len(overlap)} overlapping sentences between train/val"

    # Verify class proportions are preserved (within 5% tolerance)
    print("\nClass proportion comparison:")
    for severity_class in df["Severity Label"].unique():
        # Calculate proportions
        original_prop = (df["Severity Label"] == severity_class).mean()
        train_prop = (train_df["Severity Label"] == severity_class).mean()
        val_prop = (val_df["Severity Label"] == severity_class).mean()

        print(f"\n{severity_class}:")
        print(f"  Original: {original_prop:.3f}")
        print(f"  Train:    {train_prop:.3f} (diff: {abs(train_prop - original_prop):.3f})")
        print(f"  Val:      {val_prop:.3f} (diff: {abs(val_prop - original_prop):.3f})")

        # Assert proportions match within 5% tolerance
        assert abs(train_prop - original_prop) < 0.05, \
            f"Train proportion for {severity_class} deviates by {abs(train_prop - original_prop):.3f}"
        assert abs(val_prop - original_prop) < 0.05, \
            f"Val proportion for {severity_class} deviates by {abs(val_prop - original_prop):.3f}"


def test_chat_template_formatting():
    """Test that chat template formatting produces correct Qwen2.5 ChatML format."""
    # Load tokenizer (uses cached model if available)
    print("\nLoading Qwen2.5 tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-3B-Instruct")

    # Format a single example
    test_sentence = "Gender identity and sexual orientation are distinct concepts."
    test_severity = "Correct"
    test_explanation = "Accurate distinction between identity and orientation."

    formatted_text = format_example_qwen(
        test_sentence,
        test_severity,
        test_explanation,
        tokenizer
    )

    print("\nFormatted example:")
    print(formatted_text)

    # Verify ChatML special tokens present
    assert "<|im_start|>" in formatted_text, "Missing ChatML start token"
    assert "<|im_end|>" in formatted_text, "Missing ChatML end token"

    # Verify role markers present
    assert "system" in formatted_text, "Missing system role marker"
    assert "user" in formatted_text, "Missing user role marker"
    assert "assistant" in formatted_text, "Missing assistant role marker"

    # Verify content is present
    assert test_sentence in formatted_text, "Input sentence not found in formatted text"
    assert test_severity in formatted_text, "Severity label not found in formatted text"
    assert test_explanation in formatted_text, "Explanation not found in formatted text"

    # Verify JSON structure in assistant response
    assert '"severity"' in formatted_text, "JSON severity key not found"
    assert '"explanation"' in formatted_text, "JSON explanation key not found"

    print("\nChat template validation: PASSED")
