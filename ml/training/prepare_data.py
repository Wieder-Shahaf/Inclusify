"""Data preparation pipeline for Qwen2.5 QLoRA training.

This module loads the augmented Inclusify dataset, performs stratified train/validation
splitting, and formats examples using Qwen2.5 chat templates for fine-tuning.
"""

import json
import pandas as pd
from sklearn.model_selection import train_test_split
from datasets import Dataset
from typing import Tuple


def load_dataset(csv_path: str) -> pd.DataFrame:
    """Load Inclusify augmented dataset and validate required columns.

    Args:
        csv_path: Path to augmented_dataset.csv

    Returns:
        DataFrame with validated columns

    Raises:
        ValueError: If required columns are missing or data has null values
    """
    df = pd.read_csv(csv_path)

    required_columns = ["Sentence", "Severity Label", "Explanation"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Check for null values in required columns
    null_counts = df[required_columns].isnull().sum()
    if null_counts.any():
        raise ValueError(f"Null values found in required columns: {null_counts[null_counts > 0].to_dict()}")

    return df


def stratified_split(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Perform stratified train/validation split preserving class proportions.

    Args:
        df: Input DataFrame with "Severity Label" column
        test_size: Proportion for validation set (default 0.2 = 20%)
        random_state: Random seed for reproducibility

    Returns:
        Tuple of (train_df, val_df)
    """
    train_df, val_df = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=df["Severity Label"]
    )

    return train_df, val_df


def format_example_qwen(
    sentence: str,
    severity: str,
    explanation: str,
    tokenizer
) -> str:
    """Format a single example using Qwen2.5 chat template.

    Args:
        sentence: Input sentence to classify
        severity: Ground truth severity label
        explanation: Explanation for the classification
        tokenizer: Qwen2.5 tokenizer with apply_chat_template method

    Returns:
        Formatted string with ChatML special tokens
    """
    # System prompt for Inclusify classification task
    system_prompt = (
        "You are an expert academic editor for the Inclusify project. "
        "Analyze sentences for LGBTQ+ inclusive language compliance. "
        "Classify each sentence by severity: Correct, Outdated, Biased, "
        "Potentially Offensive, or Factually Incorrect. "
        "Provide detailed reasoning for your classification."
    )

    # User provides the sentence to analyze
    user_message = sentence

    # Assistant responds with JSON containing severity and explanation
    assistant_response = json.dumps({
        "severity": severity,
        "explanation": explanation
    }, ensure_ascii=False)

    # Build messages list for chat template
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_response}
    ]

    # Apply Qwen2.5 chat template (ChatML format with <|im_start|> and <|im_end|>)
    formatted_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False
    )

    return formatted_text


def prepare_datasets(
    csv_path: str,
    tokenizer,
    test_size: float = 0.2
) -> Tuple[Dataset, Dataset]:
    """Prepare train and validation datasets for QLoRA training.

    Args:
        csv_path: Path to augmented_dataset.csv
        tokenizer: Qwen2.5 tokenizer
        test_size: Proportion for validation set

    Returns:
        Tuple of (train_dataset, val_dataset) as HuggingFace Dataset objects
    """
    # Load and split data
    df = load_dataset(csv_path)
    train_df, val_df = stratified_split(df, test_size=test_size)

    # Format examples using chat template
    train_texts = [
        format_example_qwen(row["Sentence"], row["Severity Label"], row["Explanation"], tokenizer)
        for _, row in train_df.iterrows()
    ]

    val_texts = [
        format_example_qwen(row["Sentence"], row["Severity Label"], row["Explanation"], tokenizer)
        for _, row in val_df.iterrows()
    ]

    # Convert to HuggingFace Dataset format
    train_dataset = Dataset.from_dict({"text": train_texts})
    val_dataset = Dataset.from_dict({"text": val_texts})

    return train_dataset, val_dataset
