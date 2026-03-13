"""Configuration for data synthesis pipeline.

Environment variables:
- ANTHROPIC_API_KEY: API key for Claude (required)
- BATCH_SIZE: Number of requests per batch (default 2000)
"""

import os
from typing import Dict

# Claude API configuration
MODEL = "claude-opus-4-20250514"  # Claude Opus 4.6
MAX_TOKENS = 500
TEMPERATURE = 0.9  # Higher temperature for diversity

# API credentials
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Batch processing
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "2000"))  # Requests per batch

# Generation targets
TOTAL_TARGET = 11000  # 10% buffer for deduplication (target is 10K after filtering)

# Class distribution targets (approximate from augmented_dataset.csv)
# ~20% appropriate, ~80% problematic
CLASS_DISTRIBUTION = {
    "Correct": 0.20,
    "Outdated": 0.20,
    "Biased": 0.20,
    "Potentially Offensive": 0.20,
    "Factually Incorrect": 0.20,
}

# File paths
INPUT_CSV = "data/augmented_dataset.csv"
OUTPUT_CSV = "data/english_10k.csv"
INTERMEDIATE_DIR = "data/intermediate/"

# Quality thresholds
MIN_SIMILARITY_THRESHOLD = 0.85  # For deduplication
TARGET_DIVERSITY_SCORE = 0.7  # Average pairwise cosine distance

def get_per_class_targets(current_counts: Dict[str, int]) -> Dict[str, int]:
    """Calculate per-class generation targets based on stratified sampling.

    Args:
        current_counts: Dictionary mapping severity labels to current counts

    Returns:
        Dictionary mapping severity labels to target generation counts
    """
    total_current = sum(current_counts.values())
    targets = {}

    for label, count in current_counts.items():
        # Stratified: maintain same proportion when scaling to TOTAL_TARGET
        proportion = count / total_current
        target_total = int(TOTAL_TARGET * proportion)
        # Generate delta (new samples needed)
        targets[label] = target_total - count

    return targets
