#!/usr/bin/env python3
"""
Combine English and Hebrew datasets for multilingual QLoRA training.

Creates a balanced 50/50 English/Hebrew dataset with stratified sampling:
- Training: 16K samples (8K English + 8K Hebrew)
- Validation: 4K samples (2K English + 2K Hebrew)
- Total: 20K samples

Maintains class distribution across severity labels.
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from collections import Counter
import sys

def load_and_check_dataset(path: str, lang: str) -> pd.DataFrame:
    """Load dataset and validate structure."""
    print(f"\n{'='*60}")
    print(f"Loading {lang} dataset: {path}")
    print(f"{'='*60}")

    df = pd.read_csv(path)
    print(f"Total rows: {len(df):,}")

    # Check required columns
    required_cols = ['sentence', 'severity_label', 'explanation']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Show class distribution
    print(f"\nClass distribution:")
    dist = df['severity_label'].value_counts().sort_index()
    for label, count in dist.items():
        pct = count / len(df) * 100
        print(f"  {label:25s}: {count:5d} ({pct:5.2f}%)")

    # Add language tag
    df['language'] = lang

    return df

def stratified_sample(df: pd.DataFrame, n_samples: int, random_state: int = 42) -> pd.DataFrame:
    """Sample n_samples while maintaining class distribution."""
    # Calculate target per class (proportional)
    total = len(df)
    class_counts = df['severity_label'].value_counts()

    samples = []
    for label in class_counts.index:
        # Proportional sampling
        target_count = int(n_samples * (class_counts[label] / total))
        label_df = df[df['severity_label'] == label]

        # Sample (or take all if not enough)
        if len(label_df) >= target_count:
            sampled = label_df.sample(n=target_count, random_state=random_state)
        else:
            sampled = label_df
            print(f"  WARNING: Only {len(label_df)} samples for '{label}', need {target_count}")

        samples.append(sampled)

    result = pd.concat(samples, ignore_index=True)

    # Shuffle
    result = result.sample(frac=1, random_state=random_state).reset_index(drop=True)

    return result

def main():
    # Paths
    english_path = "data/english_10k.csv"
    hebrew_path = "data/hebrew_10k.csv"

    # Load datasets
    df_en = load_and_check_dataset(english_path, "en")
    df_he = load_and_check_dataset(hebrew_path, "he")

    print(f"\n{'='*60}")
    print("Sampling 10K from each language (8K train + 2K val)")
    print(f"{'='*60}")

    # Split each language: 80% train, 20% val
    en_train, en_val = train_test_split(
        df_en,
        test_size=0.2,  # 2K validation
        random_state=42,
        stratify=df_en['severity_label']
    )

    he_train, he_val = train_test_split(
        df_he,
        test_size=0.2,  # 2K validation
        random_state=42,
        stratify=df_he['severity_label']
    )

    print(f"\nEnglish: {len(en_train):,} train, {len(en_val):,} val")
    print(f"Hebrew:  {len(he_train):,} train, {len(he_val):,} val")

    # Combine
    train_combined = pd.concat([en_train, he_train], ignore_index=True)
    val_combined = pd.concat([en_val, he_val], ignore_index=True)
    all_combined = pd.concat([train_combined, val_combined], ignore_index=True)

    # Shuffle
    train_combined = train_combined.sample(frac=1, random_state=42).reset_index(drop=True)
    val_combined = val_combined.sample(frac=1, random_state=42).reset_index(drop=True)
    all_combined = all_combined.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"\n{'='*60}")
    print("Combined dataset statistics")
    print(f"{'='*60}")
    print(f"Training:   {len(train_combined):,} samples")
    print(f"Validation: {len(val_combined):,} samples")
    print(f"Total:      {len(all_combined):,} samples")

    # Class distribution in combined training set
    print(f"\nCombined training class distribution:")
    dist = train_combined['severity_label'].value_counts().sort_index()
    for label, count in dist.items():
        pct = count / len(train_combined) * 100
        print(f"  {label:25s}: {count:5d} ({pct:5.2f}%)")

    # Language distribution
    print(f"\nLanguage distribution:")
    lang_dist = train_combined['language'].value_counts()
    for lang, count in lang_dist.items():
        pct = count / len(train_combined) * 100
        print(f"  {lang:5s}: {count:5d} ({pct:5.2f}%)")

    # Save datasets
    print(f"\n{'='*60}")
    print("Saving datasets...")
    print(f"{'='*60}")

    # Save for manual train/val split (if needed)
    train_path = "data/combined_multilingual_train_16k.csv"
    val_path = "data/combined_multilingual_val_4k.csv"
    all_path = "data/combined_multilingual_20k.csv"

    train_combined.to_csv(train_path, index=False)
    print(f"✓ Training set:   {train_path}")

    val_combined.to_csv(val_path, index=False)
    print(f"✓ Validation set: {val_path}")

    all_combined.to_csv(all_path, index=False)
    print(f"✓ Combined set:   {all_path}")

    print(f"\n{'='*60}")
    print("SUCCESS: Datasets created!")
    print(f"{'='*60}")
    print(f"\nNext steps:")
    print(f"1. Review the datasets:")
    print(f"   head {all_path}")
    print(f"\n2. Update ml/training/config.py:")
    print(f"   csv_path = '/home/azureuser/inclusify/data/combined_multilingual_20k.csv'")
    print(f"\n3. Copy to VM:")
    print(f"   scp {all_path} azureuser@52.224.246.238:~/inclusify/data/")
    print(f"\n4. Run training on VM:")
    print(f"   ssh azureuser@52.224.246.238")
    print(f"   cd ~/inclusify && python ml/training/train_qwen_grid.py")

if __name__ == "__main__":
    main()
