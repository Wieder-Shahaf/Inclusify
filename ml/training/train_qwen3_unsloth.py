#!/usr/bin/env python3
"""
Fixed Qwen3.5-0.8B training script using Unsloth framework.
Based on research from:
- https://unsloth.ai/docs/models/qwen3.5/fine-tune
- https://sonusahani.com/blogs/fine-tune-qwen3-5-8b-locally
- https://huggingface.co/Qwen/Qwen3.5-27B/discussions/26

Key fixes:
1. Use Unsloth instead of direct transformers (handles GDN architecture)
2. Correct target modules for Gated Delta Net
3. FP16 only (no 4-bit quantization)
4. Transformers v5+ requirement (5.3.0 installed)
"""

import argparse
import json
import sys
import time
from pathlib import Path

import torch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.training.config import get_grid
from ml.training.prepare_data import prepare_datasets


class Qwen3Config:
    """Configuration for Qwen3.5-0.8B training with Unsloth."""

    # Model
    model_name: str = "Qwen/Qwen3.5-0.8B"

    # Data
    csv_path: str = "/home/azureuser/inclusify/data/augmented_dataset.csv"
    test_size: float = 0.2

    # Training hyperparameters (optimized for 0.8B model)
    num_epochs: int = 3
    batch_size: int = 8  # Qwen3.5-0.8B can handle larger batches
    learning_rate: float = 2e-4
    warmup_steps: int = 50
    max_seq_length: int = 2048  # Safe ceiling for training

    # Logging
    logging_steps: int = 50
    eval_steps: int = 50
    save_strategy: str = "steps"
    save_steps: int = 500

    # Output
    output_dir: str = "/home/azureuser/inclusify/ml/adapters/qwen3"
    log_dir: str = "/home/azureuser/inclusify/ml/logs/qwen3"

    # LoRA target modules for Qwen3.5 Gated Delta Net architecture
    # Based on: https://huggingface.co/Qwen/Qwen3.5-27B/discussions/26
    target_modules: list = [
        # Gated Delta Net projections (NEW in Qwen3.5)
        "in_proj_qkv", "in_proj_z", "in_proj_b", "in_proj_a", "out_proj",
        # MLP projections (standard)
        "gate_proj", "up_proj", "down_proj"
    ]


def train_single_config_unsloth(
    tokenizer,
    train_dataset,
    val_dataset,
    rank: int,
    alpha: int,
    dropout: float,
    config_name: str,
    config_num: int,
    total_configs: int,
) -> dict:
    """Train single LoRA configuration using Unsloth framework."""

    print(f"\n{'='*70}")
    print(f"Training config {config_num}/{total_configs}: {config_name}")
    print(f"  Rank: {rank}, Alpha: {alpha}, Dropout: {dropout}")
    print(f"  Framework: Unsloth (optimized for Qwen3.5)")
    print(f"{'='*70}\n")

    try:
        # Import Unsloth here to avoid issues if not installed
        from unsloth import FastLanguageModel
        from trl import SFTTrainer, SFTConfig

    except ImportError as e:
        print(f"ERROR: Unsloth not installed. Please run:")
        print(f"  pip install 'unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git'")
        raise e

    start_time = time.time()

    # Load model with Unsloth (handles Gated Delta Net correctly)
    print("Loading model with Unsloth FastLanguageModel...")

    # Check if BF16 is supported
    supports_bf16 = torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 8
    dtype = torch.bfloat16 if supports_bf16 else torch.float16

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=Qwen3Config.model_name,
        max_seq_length=Qwen3Config.max_seq_length,
        dtype=dtype,
        load_in_4bit=False,  # CRITICAL: Do NOT use 4-bit for Qwen3.5
    )

    # Apply LoRA using Unsloth's optimized implementation
    print(f"Applying LoRA (r={rank}, alpha={alpha}, dropout={dropout})...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=rank,
        target_modules=Qwen3Config.target_modules,
        lora_alpha=alpha,
        lora_dropout=dropout,
        bias="none",
        use_gradient_checkpointing="unsloth",  # Unsloth's optimized checkpointing
        random_state=3407,
        max_seq_length=Qwen3Config.max_seq_length,
    )

    model.print_trainable_parameters()

    # Training arguments
    output_dir = Path(Qwen3Config.output_dir) / config_name

    training_args = SFTConfig(
        output_dir=str(output_dir),
        run_name=config_name,
        num_train_epochs=Qwen3Config.num_epochs,
        per_device_train_batch_size=Qwen3Config.batch_size,
        per_device_eval_batch_size=Qwen3Config.batch_size,
        learning_rate=Qwen3Config.learning_rate,
        warmup_steps=Qwen3Config.warmup_steps,
        logging_steps=Qwen3Config.logging_steps,
        eval_strategy="steps",
        eval_steps=Qwen3Config.eval_steps,
        save_strategy=Qwen3Config.save_strategy,
        save_steps=Qwen3Config.save_steps,
        fp16=not supports_bf16,
        bf16=supports_bf16,
        optim="adamw_8bit",  # 8-bit AdamW for memory efficiency
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        dataset_text_field="text",
        max_seq_length=Qwen3Config.max_seq_length,
        packing=False,  # Don't pack sequences for better data quality
    )

    # Create trainer with Unsloth optimizations
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        processing_class=tokenizer,
    )

    # Train
    print("Starting training...")
    trainer.train()

    # Evaluate
    print("\nEvaluating...")
    eval_results = trainer.evaluate()

    # Calculate duration
    duration_min = (time.time() - start_time) / 60

    # Extract metrics
    val_loss = eval_results.get("eval_loss", float("nan"))
    val_accuracy = eval_results.get("eval_accuracy", 0.0)

    # Get trainable parameter count
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())

    print(f"\n{'='*70}")
    print(f"Completed: {config_name}")
    print(f"  Validation loss: {val_loss:.4f}")
    if val_accuracy > 0:
        print(f"  Validation accuracy: {val_accuracy:.2%}")
    print(f"  Duration: {duration_min:.2f} min")
    print(f"{'='*70}\n")

    return {
        "model": "Qwen3.5-0.8B",
        "config": config_name,
        "rank": rank,
        "alpha": alpha,
        "dropout": dropout,
        "framework": "Unsloth",
        "val_loss": val_loss,
        "val_accuracy": val_accuracy,
        "duration_min": round(duration_min, 2),
        "trainable_params": trainable_params,
        "total_params": total_params,
    }


def main():
    parser = argparse.ArgumentParser(description="Qwen3.5-0.8B grid search with Unsloth")
    args = parser.parse_args()

    print("="*70)
    print("Qwen3.5-0.8B QLoRA Grid Search (Unsloth Framework)")
    print(f"Precision: FP16/BF16 (NO 4-bit quantization)")
    print(f"Batch Size: {Qwen3Config.batch_size}")
    print("="*70)

    # Load tokenizer (Unsloth will handle model loading)
    from transformers import AutoTokenizer

    print("\n[1/3] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(Qwen3Config.model_name, trust_remote_code=True)
    print(f"Tokenizer loaded: {Qwen3Config.model_name}")

    # Prepare datasets
    print("\n[2/3] Preparing datasets...")
    train_dataset, val_dataset = prepare_datasets(
        csv_path=Qwen3Config.csv_path,
        tokenizer=tokenizer,
        test_size=Qwen3Config.test_size
    )
    print(f"Train samples: {len(train_dataset)}, Validation samples: {len(val_dataset)}")

    # Run grid search
    print("\n[3/3] Starting grid search...")
    grid = get_grid()
    results = []

    for i, (rank, alpha, dropout) in enumerate(grid, 1):
        config_name = f"qwen3_r{rank}_d{dropout}"

        try:
            config_results = train_single_config_unsloth(
                tokenizer=tokenizer,
                train_dataset=train_dataset,
                val_dataset=val_dataset,
                rank=rank,
                alpha=alpha,
                dropout=dropout,
                config_name=config_name,
                config_num=i,
                total_configs=len(grid),
            )
            results.append(config_results)

            # Save results incrementally
            results_path = Path(Qwen3Config.output_dir) / "grid_search_results.json"
            results_path.parent.mkdir(parents=True, exist_ok=True)
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2)
            print(f"Progress saved: {len(results)}/{len(grid)} configs")

        except Exception as e:
            print(f"\n{'='*70}")
            print(f"ERROR in {config_name}: {e}")
            print(f"{'='*70}\n")
            results.append({
                "model": "Qwen3.5-0.8B",
                "config": config_name,
                "rank": rank,
                "alpha": alpha,
                "dropout": dropout,
                "framework": "Unsloth",
                "error": str(e)
            })
            continue

    # Save final results
    results_path = Path(Qwen3Config.output_dir) / "grid_search_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    # Find best config
    successful_results = [r for r in results if "error" not in r]
    if successful_results:
        best = min(successful_results, key=lambda x: x["val_loss"])

        print("\n" + "="*70)
        print("Grid Search Complete!")
        print("="*70)
        print(f"Best config: {best['config']}")
        print(f"  Rank: {best['rank']}, Alpha: {best['alpha']}, Dropout: {best['dropout']}")
        print(f"  Validation loss: {best['val_loss']:.4f}")
        if best['val_accuracy'] > 0:
            print(f"  Validation accuracy: {best['val_accuracy']:.2%}")
        print(f"\nResults saved to: {results_path}")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("WARNING: All configs failed!")
        print("="*70 + "\n")


if __name__ == "__main__":
    main()
