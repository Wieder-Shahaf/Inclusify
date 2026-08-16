#!/usr/bin/env python3
"""LoRA retraining — production-format SFT with completion-only loss.

Trains Qwen2.5-3B + LoRA on the curated production-format data (data/curated/*.jsonl).
Key changes vs the earlier train_qwen_grid.py:
  - bf16 base, NO 4-bit quantization (a 3B model fits without it here).
  - completion-only loss via assistant_only_loss=True (Qwen2.5 template supports
    {% generation %}); the full ~1.9k-token system prompt is identical across rows, so
    masking it is mandatory. The applied mask is VERIFIED on one batch before training.
  - candidates: r8/d0.2 (prior winner) and r16/d0.1, both rank<=16 (T4 serving cap).

Run pinned to a single GPU:  CUDA_VISIBLE_DEVICES=1 python ml/training/train_retrain.py
"""
import json
import os
import sys
import time

import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer, DataCollatorForCompletionOnlyLM

# Qwen2.5's chat template lacks {% generation %} markers, so assistant_only_loss can't be
# used. Mask the prompt with the assistant-header response template instead.
RESPONSE_TEMPLATE = "<|im_start|>assistant\n"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_retrain import CONFIG_RETRAIN as C, GRID_RETRAIN, REPO_ROOT


def load_base(tok):
    model = AutoModelForCausalLM.from_pretrained(
        C.model_path, dtype=torch.bfloat16, device_map={"": 0})
    model.config.use_cache = False
    return model


def verify_mask(trainer, tag):
    """Assert completion-only mask applied: prompt tokens == -100, only completion scored."""
    dl = trainer.get_train_dataloader()
    batch = next(iter(dl))
    labels = batch["labels"]
    total = labels.numel()
    unmasked = (labels != -100).sum().item()
    frac = unmasked / total
    print(f"[{tag}] MASK CHECK: unmasked={unmasked}/{total} ({frac:.1%}) "
          f"-> {'OK' if frac < 0.25 else 'FAIL'}", flush=True)
    assert unmasked > 0, "all tokens masked — nothing to learn"
    assert frac < 0.25, f"mask not applied: {frac:.1%} of tokens unmasked (system prompt likely scored)"
    return frac


def train_one(rank, alpha, dropout, train_ds, eval_ds, tok):
    name = f"qwen_r{rank}_d{dropout}_achva"
    ckpt_dir = os.path.join(C.checkpoint_dir, name)
    final_dir = os.path.join(C.output_dir, name)
    steps_per_epoch = max(1, len(train_ds) // (C.per_device_train_batch_size *
                                               C.gradient_accumulation_steps))
    eval_steps = max(10, steps_per_epoch // 4)
    print(f"\n===== TRAIN {name} | steps/epoch~{steps_per_epoch} eval_steps={eval_steps} =====",
          flush=True)

    model = load_base(tok)
    peft_cfg = LoraConfig(r=rank, lora_alpha=alpha, lora_dropout=dropout,
                          target_modules=C.target_modules, bias="none", task_type="CAUSAL_LM")
    args = SFTConfig(
        output_dir=ckpt_dir,
        num_train_epochs=C.num_epochs,
        per_device_train_batch_size=C.per_device_train_batch_size,
        gradient_accumulation_steps=C.gradient_accumulation_steps,
        per_device_eval_batch_size=C.per_device_eval_batch_size,
        learning_rate=C.learning_rate,
        warmup_ratio=C.warmup_ratio,
        lr_scheduler_type=C.lr_scheduler_type,
        bf16=True, fp16=False, tf32=C.tf32,
        optim=C.optim,
        max_seq_length=C.max_seq_length,
        packing=False,
        dataset_text_field="text",         # pre-rendered chat text; collator masks the prompt
        gradient_checkpointing=C.gradient_checkpointing,
        logging_steps=C.logging_steps,
        eval_strategy="steps", eval_steps=eval_steps,
        save_strategy="steps", save_steps=eval_steps, save_total_limit=2,
        load_best_model_at_end=True, metric_for_best_model="eval_loss", greater_is_better=False,
        report_to="tensorboard", logging_dir=os.path.join(C.log_dir, name),
        seed=C.seed, dataset_num_proc=8,
    )
    collator = DataCollatorForCompletionOnlyLM(
        response_template=tok.encode(RESPONSE_TEMPLATE, add_special_tokens=False), tokenizer=tok)
    trainer = SFTTrainer(model=model, args=args, train_dataset=train_ds,
                         eval_dataset=eval_ds, peft_config=peft_cfg, processing_class=tok,
                         data_collator=collator)
    mask_frac = verify_mask(trainer, name)

    t0 = time.time()
    trainer.train()
    wall = time.time() - t0
    trainer.save_model(final_dir)
    tok.save_pretrained(final_dir)

    metrics = trainer.state.log_history
    final_eval = next((m["eval_loss"] for m in reversed(metrics) if "eval_loss" in m), None)
    final_train = next((m["loss"] for m in reversed(metrics) if "loss" in m), None)
    peak_vram = round(torch.cuda.max_memory_allocated() / 1e9, 2)
    meta = {
        "name": name, "rank": rank, "alpha": alpha, "dropout": dropout,
        "base_model": C.model_path, "max_seq_length": C.max_seq_length,
        "epochs": C.num_epochs, "lr": C.learning_rate,
        "eff_batch": C.per_device_train_batch_size * C.gradient_accumulation_steps,
        "train_examples": len(train_ds), "val_examples": len(eval_ds),
        "final_eval_loss": final_eval, "final_train_loss": final_train,
        "mask_unmasked_frac": round(mask_frac, 4),
        "wall_clock_sec": round(wall, 1), "peak_vram_gb": peak_vram, "seed": C.seed,
    }
    json.dump(meta, open(os.path.join(final_dir, "train_meta.json"), "w"), indent=2)
    print(f"[{name}] DONE eval_loss={final_eval} wall={wall:.0f}s vram={peak_vram}GB -> {final_dir}",
          flush=True)
    del trainer, model
    torch.cuda.empty_cache()
    return meta


def main():
    assert os.path.exists(C.train_jsonl), f"missing {C.train_jsonl} (run Phase 2 first)"
    tok = AutoTokenizer.from_pretrained(C.model_path)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    ds = load_dataset("json", data_files={"train": C.train_jsonl, "val": C.val_jsonl})
    # use the pre-rendered chat text; the collator handles prompt masking
    train_ds = ds["train"].select_columns(["text"])
    eval_ds = ds["val"].select_columns(["text"])
    print(f"train={len(train_ds)} val={len(eval_ds)}", flush=True)

    all_meta = []
    for rank, alpha, dropout in GRID_RETRAIN:
        try:
            all_meta.append(train_one(rank, alpha, dropout, train_ds, eval_ds, tok))
        except Exception as e:
            print(f"CANDIDATE r{rank} FAILED: {type(e).__name__}: {e}", flush=True)
            all_meta.append({"rank": rank, "error": str(e)[:300]})
    json.dump(all_meta, open(os.path.join(C.output_dir, "train_summary.json"), "w"), indent=2)
    print("\nALL DONE:", json.dumps(all_meta, indent=2))


if __name__ == "__main__":
    main()
