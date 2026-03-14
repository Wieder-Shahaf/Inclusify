#!/usr/bin/env python3
"""
Automated grid search for Qwen3.5-0.8B QLoRA hyperparameters.
Trains 9 configurations (3 ranks × 3 dropout values) sequentially.

Key differences from Qwen2.5-3B:
- Thinking mode enabled for reasoning tasks
- Larger batch sizes (0.8B vs 3B)
- Optional 4-bit quantization with BitsAndBytes
- Optimized sampling parameters for Qwen3.5

Usage:
    python ml/training/train_qwen3_grid.py [--quantize]

Estimated time: ~45 min per config × 9 configs = 6-7 hours total
"""

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.training.config import get_grid
from ml.training.prepare_data import prepare_datasets


class Qwen3Config:
    """Configuration for Qwen3.5-0.8B training."""

    # Model
    model_name: str = "Qwen/Qwen3.5-0.8B"
    model_path: str = "/home/azureuser/models/Qwen3.5-0.8B"  # VM path (or use HF directly)

    # Data
    csv_path: str = "/home/azureuser/inclusify/data/augmented_dataset.csv"
    test_size: float = 0.2
    random_state: int = 42

    # Training (optimized for 0.8B - can use larger batches)
    num_epochs: int = 3
    batch_size: int = 8  # 4x larger than 3B (0.8B fits in ~2GB)
    learning_rate: float = 2e-4
    warmup_steps: int = 100
    max_seq_length: int = 512

    # Optimizer
    optim: str = "paged_adamw_8bit"

    # Precision
    fp16: bool = True

    # Logging
    logging_steps: int = 10
    eval_steps: int = 50
    save_strategy: str = "steps"

    # Output
    output_dir: str = "/home/azureuser/inclusify/ml/adapters/qwen3"
    log_dir: str = "/home/azureuser/inclusify/ml/logs/qwen3"

    # LoRA target modules (Qwen3.5 uses Gated Delta Net architecture, different from Qwen2.5)
    target_modules: list = [
        "in_proj_qkv", "out_proj",  # Attention projections
        "up_proj", "down_proj", "gate_proj"  # MLP projections (same as Qwen2.5)
    ]

    # Note: "Thinking mode" is an inference-time feature, not used during training
    # Training uses same data format as Qwen2.5 (system prompt in prepare_data.py)


def create_lora_config(rank: int, alpha: int, dropout: float) -> LoraConfig:
    """Create PEFT LoRA configuration."""
    return LoraConfig(
        r=rank,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=Qwen3Config.target_modules,
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
    total_configs: int,
    use_quantization: bool = False
) -> dict:
    """Train single LoRA configuration and return metrics."""

    print(f"\n{'='*70}")
    print(f"Training config {config_num}/{total_configs}: {config_name}")
    print(f"  Rank: {rank}, Alpha: {alpha}, Dropout: {dropout}")
    print(f"  Quantization: {'4-bit' if use_quantization else 'FP16'}")
    print(f"{'='*70}\n")

    start_time = time.time()

    # Load model (with optional quantization)
    if use_quantization:
        print("Loading model with 4-bit quantization...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        base_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        base_model = prepare_model_for_kbit_training(base_model)
    else:
        print("Loading model in FP16...")
        base_model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float16,
        )
        # Enable gradient checkpointing for memory efficiency
        base_model.gradient_checkpointing_enable()

    # Resize embeddings to match tokenizer (critical for Qwen3.5)
    # Tokenizer has special tokens (e.g., EOS=248046) beyond base vocab size
    base_model.resize_token_embeddings(len(tokenizer))

    # Create LoRA config
    lora_config = create_lora_config(rank, alpha, dropout)

    # Attach LoRA adapter
    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    # Training arguments
    output_dir = Path(Qwen3Config.output_dir) / config_name
    log_dir = Path(Qwen3Config.log_dir) / config_name

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        run_name=config_name,
        num_train_epochs=Qwen3Config.num_epochs,
        per_device_train_batch_size=Qwen3Config.batch_size,
        per_device_eval_batch_size=Qwen3Config.batch_size,
        learning_rate=Qwen3Config.learning_rate,
        warmup_steps=Qwen3Config.warmup_steps,
        logging_dir=str(log_dir),
        logging_steps=Qwen3Config.logging_steps,
        eval_strategy="steps",
        eval_steps=Qwen3Config.eval_steps,
        save_strategy=Qwen3Config.save_strategy,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        fp16=Qwen3Config.fp16,
        optim=Qwen3Config.optim,
        report_to="tensorboard",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )

    # Create trainer
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
    results = {
        "model": "Qwen3.5-0.8B",
        "config": config_name,
        "rank": rank,
        "alpha": alpha,
        "dropout": dropout,
        "quantized": use_quantization,
        "val_loss": eval_metrics["eval_loss"],
        "val_accuracy": eval_metrics.get("eval_mean_token_accuracy", 0.0),
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

    parser = argparse.ArgumentParser()
    parser.add_argument('--quantize', action='store_true',
                       help='Use 4-bit quantization (reduces memory, slightly slower)')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("Qwen3.5-0.8B QLoRA Grid Search")
    print(f"Quantization: {'Enabled (4-bit)' if args.quantize else 'Disabled (FP16)'}")
    print(f"Batch Size: {Qwen3Config.batch_size} (4x larger than 3B)")
    print("="*70)

    # Determine model path (download from HF if not cached on VM)
    model_path = Qwen3Config.model_path
    if not Path(model_path).exists():
        print(f"\nModel not found at {model_path}, will download from HuggingFace...")
        model_path = Qwen3Config.model_name

    # Load tokenizer
    print("\n[1/3] Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    print(f"Tokenizer loaded: {model_path}")

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
            config_results = train_single_config(
                model_path=model_path,
                tokenizer=tokenizer,
                train_dataset=train_dataset,
                val_dataset=val_dataset,
                rank=rank,
                alpha=alpha,
                dropout=dropout,
                config_name=config_name,
                config_num=i,
                total_configs=len(grid),
                use_quantization=args.quantize
            )
            results.append(config_results)

            # Save results incrementally after each config
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
                "quantized": args.quantize,
                "error": str(e)
            })
            continue

    # Save results
    results_path = Path(Qwen3Config.output_dir) / "grid_search_results.json"
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
