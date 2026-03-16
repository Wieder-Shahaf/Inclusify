"""Hyperparameter grid configuration for Qwen2.5 QLoRA training."""

import itertools
from dataclasses import dataclass
from typing import List, Tuple

# Grid search space
# Using only the proven best config from Phase 05.4: rank=8, dropout=0.2
RANKS = [8]  # Best performer: 90% F1, lowest val_loss (0.4937)
DROPOUTS = [0.2]  # Best performer with rank=8

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
    model_name: str = "Qwen/Qwen2.5-3B-Instruct"
    model_path: str = "/home/azureuser/models/Qwen2.5-3B-Instruct"  # VM path (FP16, quantized to 4-bit NF4 at load time)

    # Data
    csv_path: str = "/home/azureuser/inclusify/data/combined_multilingual_20k.csv"  # VM path (20K: 16K train + 4K val)
    test_size: float = 0.2  # 80% train (15.9K), 20% val (4K)
    random_state: int = 42

    # Training
    num_epochs: int = 3
    batch_size: int = 2  # Reduced to 2 for GPTQ memory constraints
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
    save_strategy: str = "steps"  # Must match eval_strategy for load_best_model_at_end

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
