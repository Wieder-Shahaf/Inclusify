#!/usr/bin/env python3
"""
QLoRA training for Qwen2.5-3B using bitsandbytes 4-bit NF4 quantization.

Approach:
- Loads FP16 base model (Qwen2.5-3B-Instruct)
- Quantizes to 4-bit NF4 on-the-fly using bitsandbytes
- Trains LoRA adapters in FP16
- Uses proven optimal config: rank=8, dropout=0.2

Dataset: 20K multilingual samples (10K English + 10K Hebrew)

Usage:
    python ml/training/train_qwen_grid.py

Estimated time: ~6-10 hours (vs 51 hours for FP16 training)
"""

import json
import sys
import time
from pathlib import Path

import torch
import numpy as np
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.training.config import get_grid, CONFIG
from ml.training.prepare_data import prepare_datasets


def compute_metrics(eval_pred):
    """Compute token-level accuracy for evaluation.

    Args:
        eval_pred: Tuple of (predictions, labels) from trainer

    Returns:
        Dict with accuracy metric
    """
    predictions, labels = eval_pred

    # predictions shape: (batch_size, seq_len, vocab_size)
    # Get predicted token IDs (argmax over vocab dimension)
    if len(predictions.shape) == 3:
        predictions = np.argmax(predictions, axis=-1)

    # Flatten both arrays for token-level comparison
    predictions = predictions.flatten()
    labels = labels.flatten()

    # Ignore padding tokens (label = -100)
    mask = labels != -100
    predictions = predictions[mask]
    labels = labels[mask]

    # Calculate accuracy: percentage of correctly predicted tokens
    accuracy = (predictions == labels).astype(np.float32).mean()

    return {"accuracy": float(accuracy)}


def create_lora_config(rank: int, alpha: int, dropout: float) -> LoraConfig:
    """Create PEFT LoRA configuration."""
    return LoraConfig(
        r=rank,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=CONFIG.target_modules,
        task_type="CAUSAL_LM",
        bias="none"
    )


def train_single_config(
    model_path: str,
    tokenizer,
    train_dataset,
    val_dataset,
    rank: int,
    alpha: int,
    dropout: float,
    config_name: str,
    config_num: int,
    total_configs: int
) -> dict:
    """Train single LoRA configuration and return metrics."""

    print(f"\n{'='*70}")
    print(f"Training config {config_num}/{total_configs}: {config_name}")
    print(f"  Rank: {rank}, Alpha: {alpha}, Dropout: {dropout}")
    print(f"{'='*70}\n")

    start_time = time.time()

    # Configure bitsandbytes 4-bit quantization (QLoRA)
    print("Configuring 4-bit NF4 quantization with bitsandbytes...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,                      # Enable 4-bit quantization
        bnb_4bit_use_double_quant=True,         # Double quantization for extra memory savings
        bnb_4bit_quant_type="nf4",              # NormalFloat 4-bit (optimal for normally distributed weights)
        bnb_4bit_compute_dtype=torch.float16   # Compute in FP16 (T4 compatible)
    )

    # Load FP16 base model and quantize to 4-bit on-the-fly
    print(f"Loading base model from {model_path}")
    print("(FP16 on disk → 4-bit NF4 in GPU memory)")
    base_model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=bnb_config,  # Apply 4-bit quantization during load
        device_map="auto",
    )

    print(f"✓ Model loaded and quantized to 4-bit NF4")
    print(f"  VRAM usage: ~1.5-2 GB (vs ~6-7 GB for FP16)")

    # Enable gradient checkpointing for memory efficiency
    base_model.gradient_checkpointing_enable()

    # Create LoRA config
    lora_config = create_lora_config(rank, alpha, dropout)

    # Attach LoRA adapter
    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    # Training arguments
    output_dir = Path(CONFIG.output_dir) / config_name
    log_dir = Path(CONFIG.log_dir) / config_name

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        run_name=config_name,
        num_train_epochs=CONFIG.num_epochs,
        per_device_train_batch_size=CONFIG.batch_size,
        per_device_eval_batch_size=1,  # Reduced to 1 to avoid OOM during eval
        learning_rate=CONFIG.learning_rate,
        warmup_steps=CONFIG.warmup_steps,
        logging_dir=str(log_dir),
        logging_steps=CONFIG.logging_steps,
        eval_strategy="steps",
        eval_steps=CONFIG.eval_steps,
        save_strategy=CONFIG.save_strategy,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        fp16=CONFIG.fp16,
        bf16=False,  # Explicitly disable BF16 (T4 only emulates it, causes errors with optimizer)
        optim=CONFIG.optim,
        report_to="tensorboard",
        gradient_checkpointing=True,  # Enable for QLoRA memory efficiency
        gradient_checkpointing_kwargs={"use_reentrant": False},  # Recommended for newer PyTorch
    )

    # Create trainer
    # Note: TRL 0.29.0 - we already applied PEFT via get_peft_model() above
    # Do NOT pass peft_config again (would error: "PeftModel with peft_config")
    # Note: compute_metrics disabled (causes OOM), use mean_token_accuracy from logs instead
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )

    # Train
    trainer.train()

    # Evaluate
    eval_metrics = trainer.evaluate()

    # Save adapter
    trainer.save_model(str(output_dir))

    # Calculate duration
    duration_min = (time.time() - start_time) / 60

    # Collect results
    # Note: val_accuracy comes from trainer's built-in mean_token_accuracy during eval
    results = {
        "config": config_name,
        "rank": rank,
        "alpha": alpha,
        "dropout": dropout,
        "val_loss": eval_metrics["eval_loss"],
        "val_accuracy": eval_metrics.get("eval_mean_token_accuracy", 0.0),  # Built-in metric
        "duration_min": round(duration_min, 2),
        "trainable_params": model.num_parameters(only_trainable=True),
        "total_params": model.num_parameters(),
    }

    print(f"\n{'='*70}")
    print(f"Completed: {config_name}")
    print(f"  Validation loss: {results['val_loss']:.4f}")
    if results['val_accuracy'] > 0:
        print(f"  Validation accuracy: {results['val_accuracy']:.2%}")
    print(f"  Duration: {results['duration_min']:.2f} min")
    print(f"{'='*70}\n")

    # Clean up to free GPU memory before next config
    del model, trainer, base_model
    torch.cuda.empty_cache()

    return results


def main():
    """Run grid search training."""

    print("\n" + "="*70)
    print("Qwen2.5 QLoRA Grid Search")
    print("="*70)

    # Load tokenizer (model will be loaded fresh for each config)
    print("\n[1/3] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(CONFIG.model_path)
    print(f"Tokenizer loaded: {CONFIG.model_path}")

    # Prepare datasets
    print("\n[2/3] Preparing datasets...")
    train_dataset, val_dataset = prepare_datasets(
        csv_path=CONFIG.csv_path,
        tokenizer=tokenizer,
        test_size=CONFIG.test_size
    )
    print(f"Train samples: {len(train_dataset)}, Validation samples: {len(val_dataset)}")

    # Run grid search
    print("\n[3/3] Starting grid search...")
    grid = get_grid()
    results = []

    for i, (rank, alpha, dropout) in enumerate(grid, 1):
        config_name = f"qwen_r{rank}_d{dropout}"

        try:
            config_results = train_single_config(
                model_path=CONFIG.model_path,
                tokenizer=tokenizer,
                train_dataset=train_dataset,
                val_dataset=val_dataset,
                rank=rank,
                alpha=alpha,
                dropout=dropout,
                config_name=config_name,
                config_num=i,
                total_configs=len(grid)
            )
            results.append(config_results)

            # Save results incrementally after each config
            results_path = Path(CONFIG.output_dir) / "grid_search_results.json"
            results_path.parent.mkdir(parents=True, exist_ok=True)
            with open(results_path, "w") as f:
                json.dump(results, f, indent=2)
            print(f"Progress saved: {len(results)}/{len(grid)} configs")

        except Exception as e:
            print(f"\n{'='*70}")
            print(f"ERROR in {config_name}: {e}")
            print(f"{'='*70}\n")
            results.append({
                "config": config_name,
                "rank": rank,
                "alpha": alpha,
                "dropout": dropout,
                "error": str(e)
            })
            continue

    # Save results
    results_path = Path(CONFIG.output_dir) / "grid_search_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
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
        print(f"  Validation accuracy: {best['val_accuracy']:.2%}")
        print(f"\nResults saved to: {results_path}")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("WARNING: All configs failed!")
        print("="*70 + "\n")


if __name__ == "__main__":
    main()
