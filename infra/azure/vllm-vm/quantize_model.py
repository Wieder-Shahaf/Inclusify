#!/usr/bin/env python3
"""
GPTQ Model Quantization Script for Inclusify
=============================================

Quantizes the suzume-llama-3-8B-multilingual model to 4-bit GPTQ format
for efficient inference on Azure T4 GPU (16GB VRAM).

This script should be run on a machine with:
- At least 32GB RAM (for loading the full-precision model)
- A CUDA-capable GPU (for quantization)
- The Inclusify_Dataset.csv file (for calibration)

Output:
- GPTQ-quantized model saved to /home/azureuser/models/suzume-llama-3-8B-gptq
- Tokenizer saved alongside the model for vLLM compatibility

Usage:
    python quantize_model.py [--output-dir /path/to/output]

Reference: https://docs.vllm.ai/en/latest/features/quantization/gptqmodel/
"""

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import List

# Model and output configuration
BASE_MODEL_ID = "lightblue/suzume-llama-3-8B-multilingual"
DEFAULT_OUTPUT_DIR = "/home/azureuser/models/suzume-llama-3-8B-gptq"
DATASET_PATH = "/home/azureuser/inclusify/data/Inclusify_Dataset.csv"

# Quantization parameters (per CONTEXT.md decisions)
QUANT_BITS = 4
GROUP_SIZE = 128
DESC_ACT = False  # False for faster inference

# Calibration settings
NUM_CALIBRATION_SAMPLES = 200  # 200 samples, ~100 each English/Hebrew


def load_calibration_data(dataset_path: str, num_samples: int) -> List[str]:
    """
    Load calibration data from Inclusify_Dataset.csv.

    Selects a balanced mix of English and Hebrew sentences for calibration.
    The calibration data helps GPTQ maintain model quality for our specific use case.
    """
    sentences: List[str] = []

    if not Path(dataset_path).exists():
        print(f"Warning: Dataset not found at {dataset_path}")
        print("Using fallback calibration sentences...")
        return get_fallback_calibration_data()

    with open(dataset_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sentence = row.get('Sentence', '').strip()
            if sentence:
                sentences.append(sentence)

    if len(sentences) < num_samples:
        print(f"Warning: Only {len(sentences)} sentences in dataset, using all")
        return sentences

    # Shuffle and sample
    random.seed(42)  # Reproducible sampling
    random.shuffle(sentences)

    return sentences[:num_samples]


def get_fallback_calibration_data() -> List[str]:
    """Fallback calibration data if dataset is not available."""
    return [
        # English samples - inclusive language
        "Gender identity is an individual's internal sense of being male, female, both, neither, or somewhere along the gender spectrum.",
        "The WHO removed homosexuality from the ICD in 1990.",
        "Research shows that social support improves mental health outcomes for LGBTQ+ youth.",
        "Sexual orientation and gender identity are distinct concepts.",
        "Transgender healthcare guidelines are developed by professional medical organizations.",
        "LGBTQ+ people exist in all religious and cultural communities.",
        "Social acceptance is linked to better well-being among LGBTQ+ youth.",
        "Laws protecting LGBTQ+ people reduce documented discrimination.",
        "Same-sex relationships have been documented across cultures and history.",
        "Hate crimes disproportionately affect LGBTQ+ communities.",

        # English samples - problematic language (for learning to detect)
        "Conversion therapy was once considered an acceptable treatment.",
        "Homosexuality was listed as a mental illness in diagnostic manuals.",
        "Being gay was once grounds for dismissal from public service.",
        "Doctors once believed homosexuality could be prevented through proper upbringing.",
        "Same-sex parenting was previously believed to harm children.",

        # Hebrew samples - inclusive language
        "זהות מגדרית היא התחושה הפנימית של אדם לגבי המגדר שלו.",
        "ארגון הבריאות העולמי הסיר את ההומוסקסואליות מרשימת המחלות ב-1990.",
        "מחקרים מראים שתמיכה חברתית משפרת את בריאות הנפש של נוער להט\"ב.",
        "נטייה מינית וזהות מגדרית הם מושגים נפרדים.",
        "הנחיות לטיפול רפואי לאנשים טרנסג'נדרים מפותחות על ידי ארגונים רפואיים מקצועיים.",

        # Hebrew samples - problematic language
        "טיפול המרה נחשב בעבר לטיפול מקובל.",
        "הומוסקסואליות הוגדרה בעבר כמחלת נפש במדריכי האבחון.",
        "היות הומו היה בעבר עילה לפיטורים משירות ציבורי.",
    ]


def main():
    parser = argparse.ArgumentParser(
        description='Quantize suzume-llama-3-8B-multilingual to GPTQ 4-bit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory for quantized model (default: {DEFAULT_OUTPUT_DIR})'
    )
    parser.add_argument(
        '--dataset-path',
        type=str,
        default=DATASET_PATH,
        help=f'Path to calibration dataset (default: {DATASET_PATH})'
    )
    parser.add_argument(
        '--num-samples',
        type=int,
        default=NUM_CALIBRATION_SAMPLES,
        help=f'Number of calibration samples (default: {NUM_CALIBRATION_SAMPLES})'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Inclusify GPTQ Model Quantization")
    print("=" * 70)
    print(f"Base model: {BASE_MODEL_ID}")
    print(f"Output dir: {args.output_dir}")
    print(f"Quantization: {QUANT_BITS}-bit, group_size={GROUP_SIZE}")
    print("=" * 70)

    # Step 1: Load calibration data
    print("\n[1/4] Loading calibration data...")
    calibration_data = load_calibration_data(args.dataset_path, args.num_samples)
    print(f"  Loaded {len(calibration_data)} calibration sentences")

    # Step 2: Import libraries (delayed import for faster CLI feedback)
    print("\n[2/4] Loading libraries and model...")
    try:
        from gptqmodel import GPTQModel, QuantizeConfig
        from transformers import AutoTokenizer
    except ImportError as e:
        print(f"Error: Required library not found: {e}")
        print("Please install: pip install gptqmodel transformers torch")
        sys.exit(1)

    # Step 3: Load tokenizer
    print(f"  Loading tokenizer from {BASE_MODEL_ID}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Step 4: Configure quantization
    print("\n[3/4] Configuring quantization...")
    quant_config = QuantizeConfig(
        bits=QUANT_BITS,
        group_size=GROUP_SIZE,
        desc_act=DESC_ACT,
    )
    print(f"  Config: bits={QUANT_BITS}, group_size={GROUP_SIZE}, desc_act={DESC_ACT}")

    # Step 5: Load and quantize model
    print(f"\n  Loading model from {BASE_MODEL_ID}...")
    print("  (This may take several minutes and requires ~32GB RAM)")

    model = GPTQModel.from_pretrained(BASE_MODEL_ID, quant_config)

    print("\n  Quantizing model...")
    print("  (This may take 30-60 minutes on GPU)")
    model.quantize(calibration_data, tokenizer=tokenizer)

    # Step 6: Save quantized model and tokenizer
    print(f"\n[4/4] Saving quantized model to {args.output_dir}...")
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    model.save_pretrained(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    print("\n" + "=" * 70)
    print("Quantization Complete!")
    print("=" * 70)
    print(f"Model saved to: {args.output_dir}")
    print(f"Expected VRAM usage: ~4GB (from ~16GB full precision)")
    print("\nNext steps:")
    print("  1. Start vLLM with: systemctl start vllm")
    print("  2. Test inference: curl http://localhost:8001/v1/models")
    print("=" * 70)


if __name__ == '__main__':
    main()
