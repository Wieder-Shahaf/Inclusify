"""Training overrides for the Achva-v2 LoRA retrain.

Imports the original base CONFIG (ml/training/config.py) for the bits we keep
(target modules, seed) and overrides everything the retrain and the
production-format alignment change. Heavy artifacts live outside the repo, since
the working checkout is kept small.

Consumed by ml/training/train_retrain.py. Do NOT edit the hardcoded paths in
config.py — they are the original training record; this file supersedes them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Tuple

# Values mirrored from the T4-era config.py (kept identical for adapter shape compat):
_MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"
_TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "up_proj", "down_proj", "gate_proj"]
_SEED = 42

# --- Repo root (this file is ml/training/config_retrain.py) ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# --- External work root on /data (see ml/retrain_run/EXTERNAL_PATHS.md) ---
EXT_ROOT = "/data/shahafw_home/inclusify_retrain"
BASE_MODEL_PATH = os.path.join(EXT_ROOT, "base_model", "Qwen2.5-3B-Instruct")
OUTPUT_DIR = os.path.join(EXT_ROOT, "adapters_new")        # final candidate adapters
CHECKPOINT_DIR = os.path.join(EXT_ROOT, "checkpoints")     # trainer intermediate checkpoints
LOG_DIR = os.path.join(EXT_ROOT, "logs")                   # tensorboard

# --- Curated, production-format training data (Phase 2 output) ---
# Rendered JSONL repeats the ~1.9k-token system prompt in every example (~280MB total),
# so it lives on /data, not in git. Regenerable from ml/data_curated/curated.jsonl.
TRAIN_JSONL = os.path.join(EXT_ROOT, "curated_data", "train.jsonl")
VAL_JSONL = os.path.join(EXT_ROOT, "curated_data", "val.jsonl")

SEED = _SEED  # 42


@dataclass
class RetrainConfig:
    # Model — local bf16 base, NO quantization (3B fits easily in 80GB)
    model_path: str = BASE_MODEL_PATH
    model_name: str = _MODEL_NAME  # "Qwen/Qwen2.5-3B-Instruct"

    # Precision: the training GPU supports bf16 natively, so no need to disable it.
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

    # Batch — effective 32. Sequences are long (~2.4k tok: the ~1.9k-token production
    # system prompt sits in every example), so batch 8 + accum 4 + checkpointing keeps
    # VRAM safe on the training GPU.
    per_device_train_batch_size: int = 8   # batch 16 OOMs at seq 2432 (20GB spike); 8 is stable ~54GB
    gradient_accumulation_steps: int = 4
    per_device_eval_batch_size: int = 8
    gradient_checkpointing: bool = True  # needed at this seq length

    # Sequence: TRUE max formatted example is 2350 tokens (measured). 1024/2048 would
    # truncate the assistant target. Set above the real max.
    max_seq_length: int = 2432

    # Eval / logging / checkpointing
    logging_steps: int = 10
    eval_strategy: str = "steps"
    eval_steps: int = 0          # set per-run to ~0.25 epoch in train_retrain.py
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
    target_modules: List[str] = field(default_factory=lambda: list(_TARGET_MODULES))


CONFIG_RETRAIN = RetrainConfig()

# --- Candidate grid (rank <= 16 hard cap for T4 --max-lora-rank 16 serving) ---
# Primary: prior winner r8/d0.2. Second: r16/d0.1 (larger rank may help Hebrew).
# (rank, alpha, dropout)  — alpha = 2*rank
GRID_RETRAIN: List[Tuple[int, int, float]] = [
    (8, 16, 0.2),
    (16, 32, 0.1),
]
