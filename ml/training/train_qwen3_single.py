#!/usr/bin/env python3
"""
Quick test of Qwen3.5-0.8B for Inclusify task comparison.
Single config (rank=16, dropout=0.1) to compare with Qwen2.5-3B.

Usage:
    python ml/training/train_qwen3_single.py
"""

import json
import sys
import time
from pathlib import Path

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ml.training.prepare_data import prepare_datasets


def train_qwen3():
    """Train Qwen3.5-0.8B with single configuration for comparison."""

    print("\n" + "="*70)
    print("Qwen3.5-0.8B Comparison Test")
    print("="*70)

    # Paths
    model_path = "Qwen/Qwen3.5-0.8B"
    csv_path = "/home/azureuser/inclusify/data/augmented_dataset.csv"
    output_dir = "/home/azureuser/inclusify/ml/adapters/qwen3_r16_d0.1"

    # Load tokenizer and model
    print("\n[1/4] Loading Qwen3.5-0.8B...")
    tokenizer = AutoTokenizer.from_pretrained(model_path)

    base_model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype=torch.float16,
    )

    # Prepare datasets
    print("\n[2/4] Preparing datasets...")
    train_dataset, val_dataset = prepare_datasets(
        csv_path=csv_path,
        tokenizer=tokenizer,
        test_size=0.2
    )
    print(f"Train: {len(train_dataset)}, Val: {len(val_dataset)}")

    # Create LoRA config (rank=16 middle ground)
    print("\n[3/4] Configuring LoRA...")
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                       "up_proj", "down_proj", "gate_proj"],
        task_type="CAUSAL_LM",
        bias="none"
    )

    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    # Training arguments (larger batch size possible with 0.8B)
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=8,  # 4x larger than 3B!
        per_device_eval_batch_size=8,
        learning_rate=2e-4,
        warmup_steps=100,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        fp16=True,
        optim="paged_adamw_8bit",
        report_to="tensorboard",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )

    # Train
    print("\n[4/4] Training...")
    start = time.time()

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )

    trainer.train()
    eval_metrics = trainer.evaluate()

    duration_min = (time.time() - start) / 60

    # Save
    trainer.save_model(output_dir)

    # Results
    results = {
        "model": "Qwen3.5-0.8B",
        "config": "r16_d0.1",
        "val_loss": eval_metrics["eval_loss"],
        "val_accuracy": eval_metrics.get("eval_mean_token_accuracy", 0.0),
        "duration_min": round(duration_min, 2),
        "trainable_params": model.num_parameters(only_trainable=True),
        "total_params": model.num_parameters(),
    }

    results_path = Path(output_dir) / "results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*70)
    print("Qwen3.5-0.8B Training Complete!")
    print("="*70)
    print(f"Validation loss: {results['val_loss']:.4f}")
    print(f"Duration: {results['duration_min']:.2f} min")
    print(f"Results: {results_path}")
    print("="*70 + "\n")


if __name__ == "__main__":
    train_qwen3()
