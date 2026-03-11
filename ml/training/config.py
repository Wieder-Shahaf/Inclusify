"""Hyperparameter grid configuration for Qwen2.5 QLoRA training."""

import itertools
from dataclasses import dataclass
from typing import List, Tuple

# Grid search space (user decision from CONTEXT.md)
RANKS = [8, 16, 32]
DROPOUTS = [0.05, 0.1, 0.2]

# Alpha scaling rule: alpha = 2 * rank
def get_alpha(rank: int) -> int:
    return 2 * rank

# Generate all 9 configurations
def get_grid() -> List[Tuple[int, int, float]]:
    """Returns list of (rank, alpha, dropout) tuples."""
    grid = []
    for rank, dropout in itertools.product(RANKS, DROPOUTS):
        alpha = get_alpha(rank)
        grid.append((rank, alpha, dropout))
    return grid

@dataclass
class TrainingConfig:
    """Fixed training hyperparameters."""

    # Model
    model_name: str = "Qwen/Qwen2.5-3B-Instruct-GPTQ-Int4"
    model_path: str = "/home/azureuser/models/Qwen2.5-3B-Instruct-GPTQ-Int4"  # VM path

    # Data
    csv_path: str = "/home/azureuser/inclusify/data/augmented_dataset.csv"  # VM path
    test_size: float = 0.2
    random_state: int = 42

    # Training
    num_epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-4
    warmup_steps: int = 100
    max_seq_length: int = 512

    # Optimizer
    optim: str = "paged_adamw_8bit"  # Critical for T4 VRAM

    # Precision
    fp16: bool = True  # T4 doesn't support bf16

    # Logging
    logging_steps: int = 10
    eval_steps: int = 50
    save_strategy: str = "epoch"

    # Output
    output_dir: str = "/home/azureuser/inclusify/ml/adapters"  # VM path
    log_dir: str = "/home/azureuser/inclusify/ml/logs"  # VM path

    # LoRA target modules (from suzume config)
    target_modules: List[str] = None

    def __post_init__(self):
        if self.target_modules is None:
            self.target_modules = [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "up_proj", "down_proj", "gate_proj"
            ]

# Singleton instance
CONFIG = TrainingConfig()
