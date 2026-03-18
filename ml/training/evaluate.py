#!/usr/bin/env python3
"""
Post-training evaluation for Qwen2.5 LoRA adapters.
Computes accuracy, F1 scores, confusion matrix for trained adapters.

Usage:
    python ml/training/evaluate.py --adapter ./adapters/qwen_r16_d0.1/
    python ml/training/evaluate.py --all-configs
    python ml/training/evaluate.py --adapter ./adapters/best_config/ --threshold 0.80
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.training.config import CONFIG
from ml.training.prepare_data import load_dataset, stratified_split


def load_adapter_model(adapter_path: str, base_model_path: str):
    """Load base model with LoRA adapter."""
    print(f"Loading base model: {base_model_path}")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype="auto",
        device_map="auto"
    )

    print(f"Loading adapter: {adapter_path}")
    model = PeftModel.from_pretrained(base_model, adapter_path)
    model.eval()

    return model


def evaluate_adapter(
    adapter_path: str,
    val_df: pd.DataFrame,
    tokenizer,
    sample_size: int = None
) -> dict:
    """Evaluate single adapter on validation set."""

    # Load model with adapter
    model = load_adapter_model(adapter_path, CONFIG.model_path)

    # Sample if requested
    if sample_size and sample_size < len(val_df):
        val_df = val_df.sample(n=sample_size, random_state=42)

    print(f"\nEvaluating on {len(val_df)} validation samples...")

    # Predict
    predictions = []
    ground_truth = val_df["Severity Label"].tolist()

    for idx, row in val_df.iterrows():
        sentence = row["Sentence"]

        # Format prompt using Qwen2.5 chat template
        messages = [
            {
                "role": "system",
                "content": "You are an LGBTQ+ language analyzer. Classify severity: Correct, Outdated, Biased, Potentially Offensive, or Factually Incorrect."
            },
            {
                "role": "user",
                "content": sentence
            }
        ]

        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.1,
                do_sample=False
            )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract severity from response (simple heuristic)
        # Response should contain JSON with "severity" field
        try:
            if "Correct" in response:
                pred = "Correct"
            elif "Outdated" in response:
                pred = "Outdated"
            elif "Biased" in response:
                pred = "Biased"
            elif "Potentially Offensive" in response or "Offensive" in response:
                pred = "Potentially Offensive"
            elif "Factually Incorrect" in response or "Incorrect" in response:
                pred = "Factually Incorrect"
            else:
                pred = "Unknown"
        except Exception as e:
            pred = "Unknown"

        predictions.append(pred)

        if (idx + 1) % 20 == 0:
            print(f"  Processed {idx + 1}/{len(val_df)} samples...")

    # Compute metrics
    accuracy = accuracy_score(ground_truth, predictions)
    f1_macro = f1_score(ground_truth, predictions, average="macro", zero_division=0)
    f1_micro = f1_score(ground_truth, predictions, average="micro", zero_division=0)

    # Classification report
    report = classification_report(ground_truth, predictions, zero_division=0)

    # Confusion matrix
    cm = confusion_matrix(ground_truth, predictions)

    results = {
        "adapter_path": adapter_path,
        "num_samples": len(val_df),
        "accuracy": round(accuracy, 4),
        "f1_macro": round(f1_macro, 4),
        "f1_micro": round(f1_micro, 4),
        "classification_report": report,
        "confusion_matrix": cm.tolist()
    }

    # Clean up
    del model
    torch.cuda.empty_cache()

    return results


def evaluate_all_configs(output_dir: str, val_df: pd.DataFrame, tokenizer) -> list:
    """Evaluate all trained adapters in output directory."""

    adapter_dirs = sorted(Path(output_dir).glob("qwen_r*"))
    print(f"\nFound {len(adapter_dirs)} adapters to evaluate")

    results = []
    for i, adapter_path in enumerate(adapter_dirs, 1):
        print(f"\n{'='*60}")
        print(f"Evaluating {i}/{len(adapter_dirs)}: {adapter_path.name}")
        print(f"{'='*60}")

        try:
            eval_results = evaluate_adapter(str(adapter_path), val_df, tokenizer, sample_size=50)
            eval_results["config_name"] = adapter_path.name
            results.append(eval_results)

            print(f"Accuracy: {eval_results['accuracy']:.2%}")
            print(f"F1 (macro): {eval_results['f1_macro']:.4f}")

        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "config_name": adapter_path.name,
                "error": str(e)
            })

    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate Qwen2.5 LoRA adapters")
    parser.add_argument("--adapter", type=str, help="Path to specific adapter directory")
    parser.add_argument("--all-configs", action="store_true", help="Evaluate all adapters")
    parser.add_argument("--threshold", type=float, default=0.80, help="Accuracy threshold for pass/fail")
    parser.add_argument("--sample", type=int, help="Sample size for quick evaluation")
    args = parser.parse_args()

    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(CONFIG.model_path)

    # Load validation dataset
    print("Loading validation dataset...")
    df = load_dataset(CONFIG.csv_path)
    _, val_df = stratified_split(df, test_size=CONFIG.test_size)
    print(f"Validation samples: {len(val_df)}")

    # Run evaluation
    if args.all_configs:
        results = evaluate_all_configs(CONFIG.output_dir, val_df, tokenizer)

        # Save results
        results_path = Path(CONFIG.output_dir) / "evaluation_results.json"
        with open(results_path, "w") as f:
            # Convert numpy arrays to lists for JSON serialization
            serializable_results = []
            for r in results:
                r_copy = r.copy()
                if "confusion_matrix" in r_copy:
                    del r_copy["confusion_matrix"]  # Too large for JSON
                if "classification_report" in r_copy:
                    del r_copy["classification_report"]  # Text format
                serializable_results.append(r_copy)
            json.dump(serializable_results, f, indent=2)

        print(f"\n{'='*60}")
        print("Evaluation complete!")
        print(f"Results saved to: {results_path}")
        print(f"{'='*60}\n")

    elif args.adapter:
        results = evaluate_adapter(args.adapter, val_df, tokenizer, sample_size=args.sample)

        print(f"\n{'='*60}")
        print("Evaluation Results")
        print(f"{'='*60}")
        print(f"Adapter: {results['adapter_path']}")
        print(f"Accuracy: {results['accuracy']:.2%}")
        print(f"F1 (macro): {results['f1_macro']:.4f}")
        print(f"F1 (micro): {results['f1_micro']:.4f}")
        print(f"\nClassification Report:\n{results['classification_report']}")

        # Threshold check
        if results['accuracy'] >= args.threshold:
            print(f"\nPASS: Accuracy {results['accuracy']:.2%} >= {args.threshold:.2%}")
            sys.exit(0)
        else:
            print(f"\nFAIL: Accuracy {results['accuracy']:.2%} < {args.threshold:.2%}")
            sys.exit(1)

    else:
        print("Error: Specify --adapter or --all-configs")
        sys.exit(1)


if __name__ == "__main__":
    main()
