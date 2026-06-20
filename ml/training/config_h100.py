"""H100 training overrides for the Achva-v2 LoRA retrain.

Imports the T4-era base CONFIG (ml/training/config.py) for the bits we keep
(target modules, seed) and overrides everything the H100 + production-format
alignment changes. Heavy artifacts live on /data (root fs is tight).

Consumed by ml/training/train_h100.py. Do NOT edit config.py's hardcoded
/home/azureuser paths — they are the T4 record; this file supersedes them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Tuple

from .config import CONFIG as _BASE  # reuse target_modules, seed, etc.

# --- Repo root (this file is ml/training/config_h100.py) ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# --- External work root on /data (see ml/retrain_run/EXTERNAL_PATHS.md) ---
EXT_ROOT = "/data/shahafw_home/inclusify_retrain"
BASE_MODEL_PATH = os.path.join(EXT_ROOT, "base_model", "Qwen2.5-3B-Instruct")
OUTPUT_DIR = os.path.join(EXT_ROOT, "adapters_new")        # final candidate adapters
CHECKPOINT_DIR = os.path.join(EXT_ROOT, "checkpoints")     # trainer intermediate checkpoints
LOG_DIR = os.path.join(EXT_ROOT, "logs")                   # tensorboard

# --- Curated, production-format training data (Phase 2 output, in-repo) ---
TRAIN_JSONL = os.path.join(REPO_ROOT, "data", "curated", "train.jsonl")
VAL_JSONL = os.path.join(REPO_ROOT, "data", "curated", "val.jsonl")

SEED = _BASE.random_state  # 42


@dataclass
class H100Config:
    # Model — local bf16 base, NO quantization (3B fits easily in 80GB)
    model_path: str = BASE_MODEL_PATH
    model_name: str = _BASE.model_name  # "Qwen/Qwen2.5-3B-Instruct"

    # Precision: H100 does bf16 natively (T4 reason for disabling is gone)
    bf16: bool = True
    fp16: bool = False
    tf32: bool = True
    load_in_4bit: bool = False  # drop NF4 QLoRA — train LoRA on bf16 base

    # Optimizer (no 8-bit memory hack needed)
    optim: str = "adamw_torch"
    learning_rate: float = 2e-4
    warmup_ratio: float = 0.03
    lr_scheduler_type: str = "cosine"
    num_epochs: int = 3

    # Batch — effective ~32-64; raise per_device if VRAM allows
    per_device_train_batch_size: int = 16
    gradient_accumulation_steps: int = 2
    per_device_eval_batch_size: int = 32
    gradient_checkpointing: bool = False  # have the memory; off for speed

    # Sequence: prod system prompt (~1.9k tok) + passage exceeds 512; need room
    max_seq_length: int = 1024

    # Eval / logging / checkpointing
    logging_steps: int = 10
    eval_strategy: str = "steps"
    eval_steps: int = 0          # set per-run to ~0.25 epoch in train_h100.py
    save_strategy: str = "steps"
    metric_for_best_model: str = "eval_loss"  # picks best checkpoint WITHIN a run only
    load_best_model_at_end: bool = True

    seed: int = SEED

    # Paths
    output_dir: str = OUTPUT_DIR
    checkpoint_dir: str = CHECKPOINT_DIR
    log_dir: str = LOG_DIR
    train_jsonl: str = TRAIN_JSONL
    val_jsonl: str = VAL_JSONL

    # LoRA target modules — MUST match the current prod adapter (shape compat)
    target_modules: List[str] = field(default_factory=lambda: list(_BASE.target_modules))


CONFIG_H100 = H100Config()

# --- Candidate grid (rank <= 16 hard cap for T4 --max-lora-rank 16 serving) ---
# Primary: prior winner r8/d0.2. Second: r16/d0.1 (larger rank may help Hebrew).
# (rank, alpha, dropout)  — alpha = 2*rank
GRID_H100: List[Tuple[int, int, float]] = [
    (8, 16, 0.2),
    (16, 32, 0.1),
]
