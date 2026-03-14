#!/usr/bin/env python3
"""
Evaluate precision, recall, and F1 scores for trained models.
This script loads the best adapters and evaluates them on the validation set.
"""

import json
import sys
from pathlib import Path
import pandas as pd
import torch
from sklearn.metrics import precision_recall_fscore_support, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_validation_data(csv_path: str, test_size: float = 0.2):
    """Load and split validation data."""
    from sklearn.model_selection import train_test_split

    print(f"Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path)

    # Map columns to expected names
    df = df.rename(columns={'Sentence': 'text', 'Severity Label': 'label'})

    # Convert labels to binary: "Correct" = 0 (appropriate), anything else = 1 (problematic)
    df['label'] = df['label'].apply(lambda x: 0 if x == 'Correct' else 1)

    # Split to get validation set (same split as training)
    train_df, val_df = train_test_split(
        df,
        test_size=test_size,
        random_state=42,
        stratify=df['label']
    )

    print(f"Validation set size: {len(val_df)}")
    print(f"  Appropriate (0): {(val_df['label'] == 0).sum()}")
    print(f"  Problematic (1): {(val_df['label'] == 1).sum()}")
    return val_df


def load_model_and_adapter(model_name: str, adapter_path: str):
    """Load base model with LoRA adapter."""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    print(f"\nLoading {model_name}...")

    # Determine base model path
    if "Qwen2.5" in model_name or "qwen_r" in adapter_path:
        base_model_name = "Qwen/Qwen2.5-3B-Instruct"
        use_unsloth = False
    else:  # Qwen3.5
        base_model_name = "Qwen/Qwen3.5-0.8B"
        use_unsloth = True  # CRITICAL: Qwen3.5 requires Unsloth for correct loading

    print(f"  Base model: {base_model_name}")
    print(f"  Adapter: {adapter_path}")
    print(f"  Framework: {'Unsloth' if use_unsloth else 'Standard Transformers'}")

    # Load based on framework
    if use_unsloth:
        try:
            from unsloth import FastLanguageModel

            # Load with Unsloth (required for Qwen3.5 Gated Delta Net architecture)
            base_model, _ = FastLanguageModel.from_pretrained(
                model_name=base_model_name,
                max_seq_length=2048,
                dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                load_in_4bit=False,
            )

            # Use standard tokenizer to avoid multimodal processing
            tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)

            # Load adapter
            model = PeftModel.from_pretrained(base_model, adapter_path)
            model.eval()

        except ImportError:
            print("  ⚠️  Unsloth not available! Qwen3.5 may not work correctly.")
            print("  Falling back to standard loading...")
            tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
            )
            model = PeftModel.from_pretrained(base_model, adapter_path)
            model.eval()
    else:
        # Standard loading for Qwen2.5
        tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
        )
        model = PeftModel.from_pretrained(base_model, adapter_path)
        model.eval()

    print(f"  ✓ Model loaded")
    return model, tokenizer


def predict_sample(model, tokenizer, text: str, max_length: int = 512):
    """Run inference on a single text sample."""
    system_prompt = """You are an LGBTQ+ inclusive language analyzer. Analyze the following academic text and determine if it contains problematic language.

Respond with ONLY ONE WORD:
- "problematic" if the text contains LGBTQphobic, outdated, biased, or pathologizing language
- "appropriate" if the text uses inclusive and respectful language"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
    ]

    # Format with chat template
    formatted = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(
        formatted,
        return_tensors="pt",
        max_length=max_length,
        truncation=True,
        padding=True
    )

    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}

    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=10,
            temperature=0.1,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    # Decode
    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    response = response.strip().lower()

    # Map to label
    if "problematic" in response:
        return 1
    elif "appropriate" in response:
        return 0
    else:
        # Default to appropriate if unclear
        return 0


def evaluate_model(model, tokenizer, val_df, model_name: str):
    """Evaluate model on validation set."""
    print(f"\nEvaluating {model_name}...")

    y_true = []
    y_pred = []

    total = len(val_df)
    for idx, row in val_df.iterrows():
        if (idx + 1) % 10 == 0:
            print(f"  Progress: {idx + 1}/{total}", end='\r')

        text = row['text']
        true_label = row['label']

        pred_label = predict_sample(model, tokenizer, text)

        y_true.append(true_label)
        y_pred.append(pred_label)

    print(f"  Progress: {total}/{total} - Complete!")

    # Calculate metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average='binary', zero_division=0
    )

    # Also get per-class metrics
    precision_per_class, recall_per_class, f1_per_class, support_per_class = \
        precision_recall_fscore_support(y_true, y_pred, average=None, zero_division=0)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)

    results = {
        'model': model_name,
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'support': int(support) if support is not None else len(y_true),
        'precision_per_class': precision_per_class.tolist(),
        'recall_per_class': recall_per_class.tolist(),
        'f1_per_class': f1_per_class.tolist(),
        'support_per_class': support_per_class.tolist(),
        'confusion_matrix': cm.tolist(),
        'y_true': y_true,
        'y_pred': y_pred,
    }

    print(f"\n  Precision: {precision:.4f}")
    print(f"  Recall: {recall:.4f}")
    print(f"  F1 Score: {f1:.4f}")

    return results


def plot_metrics_comparison(qwen25_results, qwen3_results, output_path):
    """Create visualization comparing model metrics."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Model Evaluation: Qwen2.5-3B vs Qwen3.5-0.8B', fontsize=16, fontweight='bold')

    # 1. Bar chart: Precision, Recall, F1
    ax1 = axes[0, 0]
    metrics = ['Precision', 'Recall', 'F1-Score']
    qwen25_values = [qwen25_results['precision'], qwen25_results['recall'], qwen25_results['f1']]
    qwen3_values = [qwen3_results['precision'], qwen3_results['recall'], qwen3_results['f1']]

    x = np.arange(len(metrics))
    width = 0.35

    bars1 = ax1.bar(x - width/2, qwen25_values, width, label='Qwen2.5-3B', color='#2E86AB', alpha=0.8)
    bars2 = ax1.bar(x + width/2, qwen3_values, width, label='Qwen3.5-0.8B', color='#A23B72', alpha=0.8)

    ax1.set_ylabel('Score', fontweight='bold')
    ax1.set_title('Overall Metrics Comparison', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics)
    ax1.legend()
    ax1.set_ylim([0, 1.0])
    ax1.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}',
                    ha='center', va='bottom', fontsize=8)

    # 2. Confusion Matrix - Qwen2.5
    ax2 = axes[0, 1]
    cm_qwen25 = np.array(qwen25_results['confusion_matrix'])
    sns.heatmap(cm_qwen25, annot=True, fmt='d', cmap='Blues', ax=ax2,
                xticklabels=['Appropriate', 'Problematic'],
                yticklabels=['Appropriate', 'Problematic'])
    ax2.set_title('Qwen2.5-3B Confusion Matrix', fontweight='bold')
    ax2.set_ylabel('True Label', fontweight='bold')
    ax2.set_xlabel('Predicted Label', fontweight='bold')

    # 3. Confusion Matrix - Qwen3
    ax3 = axes[1, 0]
    cm_qwen3 = np.array(qwen3_results['confusion_matrix'])
    sns.heatmap(cm_qwen3, annot=True, fmt='d', cmap='Purples', ax=ax3,
                xticklabels=['Appropriate', 'Problematic'],
                yticklabels=['Appropriate', 'Problematic'])
    ax3.set_title('Qwen3.5-0.8B Confusion Matrix', fontweight='bold')
    ax3.set_ylabel('True Label', fontweight='bold')
    ax3.set_xlabel('Predicted Label', fontweight='bold')

    # 4. Per-class metrics comparison
    ax4 = axes[1, 1]
    classes = ['Appropriate', 'Problematic']
    metric_types = ['Precision', 'Recall', 'F1']

    # Prepare data for grouped bar chart
    qwen25_appropriate = [
        qwen25_results['precision_per_class'][0],
        qwen25_results['recall_per_class'][0],
        qwen25_results['f1_per_class'][0]
    ]
    qwen25_problematic = [
        qwen25_results['precision_per_class'][1],
        qwen25_results['recall_per_class'][1],
        qwen25_results['f1_per_class'][1]
    ]
    qwen3_appropriate = [
        qwen3_results['precision_per_class'][0],
        qwen3_results['recall_per_class'][0],
        qwen3_results['f1_per_class'][0]
    ]
    qwen3_problematic = [
        qwen3_results['precision_per_class'][1],
        qwen3_results['recall_per_class'][1],
        qwen3_results['f1_per_class'][1]
    ]

    x = np.arange(len(metric_types))
    width = 0.2

    ax4.bar(x - 1.5*width, qwen25_appropriate, width, label='Q2.5 Appropriate', color='#2E86AB', alpha=0.6)
    ax4.bar(x - 0.5*width, qwen25_problematic, width, label='Q2.5 Problematic', color='#2E86AB', alpha=1.0)
    ax4.bar(x + 0.5*width, qwen3_appropriate, width, label='Q3.5 Appropriate', color='#A23B72', alpha=0.6)
    ax4.bar(x + 1.5*width, qwen3_problematic, width, label='Q3.5 Problematic', color='#A23B72', alpha=1.0)

    ax4.set_ylabel('Score', fontweight='bold')
    ax4.set_title('Per-Class Metrics Comparison', fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(metric_types)
    ax4.legend(fontsize=8, loc='lower right')
    ax4.set_ylim([0, 1.0])
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Metrics plot saved to: {output_path}")

    return fig


def main():
    analysis_dir = Path(__file__).parent
    project_root = analysis_dir.parent.parent

    # Paths
    csv_path = project_root / "data" / "augmented_dataset.csv"

    # Note: Update these paths based on where adapters are actually stored
    # For Qwen2.5, we need to download from VM or use local if available
    # For Qwen3, we just downloaded to ml/adapters/qwen3/qwen3_r32_d0.05

    print("="*70)
    print("MODEL EVALUATION: Precision, Recall, F1 Scores")
    print("="*70)

    # Check if running with CPU or GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nDevice: {device}")

    if device == "cpu":
        print("\n⚠️  WARNING: Running on CPU. This will be very slow!")
        print("For faster evaluation, run this script on the Azure VM with GPU.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            return

    # Load validation data
    val_df = load_validation_data(str(csv_path))

    # Define adapter paths
    qwen25_adapter = project_root / "ml" / "adapters" / "qwen_r8_d0.2"
    qwen3_adapter_base = project_root / "ml" / "adapters" / "qwen3" / "qwen3_r32_d0.05"

    # Qwen3 adapter is in checkpoint subdirectory
    qwen3_adapter = qwen3_adapter_base / "checkpoint-150"

    # Check if it's the root directory instead (VM structure vs local)
    if not qwen3_adapter.exists() and qwen3_adapter_base.exists():
        # Check for adapter_config.json in base dir
        if (qwen3_adapter_base / "adapter_config.json").exists():
            qwen3_adapter = qwen3_adapter_base

    # Determine which models to evaluate
    has_qwen25 = qwen25_adapter.exists() and (qwen25_adapter / "adapter_config.json").exists()
    has_qwen3 = qwen3_adapter.exists() and (qwen3_adapter / "adapter_config.json").exists()

    if not has_qwen25 and not has_qwen3:
        print("\n❌ No adapters found!")
        print(f"  Qwen2.5 expected at: {qwen25_adapter}")
        print(f"  Qwen3.5 expected at: {qwen3_adapter}")
        return

    # Evaluate available models
    results = {}

    if has_qwen25:
        print("\nEvaluating Qwen2.5-3B...")
        model25, tokenizer25 = load_model_and_adapter("Qwen2.5-3B", str(qwen25_adapter))
        results['qwen25'] = evaluate_model(model25, tokenizer25, val_df, "Qwen2.5-3B")
        del model25, tokenizer25
        torch.cuda.empty_cache()

    if has_qwen3:
        print("\nEvaluating Qwen3.5-0.8B...")
        model3, tokenizer3 = load_model_and_adapter("Qwen3.5-0.8B", str(qwen3_adapter))
        results['qwen3'] = evaluate_model(model3, tokenizer3, val_df, "Qwen3.5-0.8B")
        del model3, tokenizer3
        torch.cuda.empty_cache()

    # Save results
    results_path = analysis_dir / "evaluation_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved to: {results_path}")

    # Create visualization if both models evaluated
    if 'qwen25' in results and 'qwen3' in results:
        plot_path = analysis_dir / "metrics_comparison.png"
        plot_metrics_comparison(results['qwen25'], results['qwen3'], plot_path)

    print("\n" + "="*70)
    print("Evaluation complete!")
    print("="*70)


if __name__ == '__main__':
    main()
