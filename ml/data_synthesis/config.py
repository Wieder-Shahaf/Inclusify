"""Configuration for data synthesis pipeline.

Environment variables:
- ANTHROPIC_API_KEY: API key for Claude (required if VLLM_ENABLED=false)
- VLLM_ENABLED: Use vLLM instead of Claude (default: true)
- VLLM_ENDPOINT: vLLM API endpoint (default: http://localhost:8000/v1)
- VLLM_MODEL: Model name (default: Qwen/Qwen2.5-3B-Instruct)
- VLLM_BATCH_SIZE: Requests per batch for vLLM (default: 64)
- VLLM_MAX_THROUGHPUT: Max requests per second (default: 30)
- BATCH_SIZE: Number of requests per batch for Claude (default 2000)
"""

import os
from typing import Dict

# Backend selection
VLLM_ENABLED = os.getenv("VLLM_ENABLED", "true").lower() == "true"

# vLLM configuration
VLLM_ENDPOINT = os.getenv("VLLM_ENDPOINT", "http://localhost:8000/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-3B-Instruct")
VLLM_LORA_PATH = None  # Use base model for maximum diversity
VLLM_BATCH_SIZE = int(os.getenv("VLLM_BATCH_SIZE", "64"))
VLLM_MAX_THROUGHPUT = int(os.getenv("VLLM_MAX_THROUGHPUT", "30"))  # req/sec

# Qwen-specific generation parameters
QWEN_MAX_TOKENS = int(os.getenv("QWEN_MAX_TOKENS", "1500"))
QWEN_TEMPERATURE = float(os.getenv("QWEN_TEMPERATURE", "0.9"))

# Claude API configuration (legacy)
CLAUDE_MODEL = "claude-opus-4-20250514"  # Claude Opus 4.6
CLAUDE_MAX_TOKENS = 500
CLAUDE_TEMPERATURE = 0.9
CLAUDE_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "2000"))

# API credentials
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Active configuration based on backend
if VLLM_ENABLED:
    MODEL = VLLM_MODEL
    MAX_TOKENS = QWEN_MAX_TOKENS
    TEMPERATURE = QWEN_TEMPERATURE
    BATCH_SIZE = VLLM_BATCH_SIZE
else:
    MODEL = CLAUDE_MODEL
    MAX_TOKENS = CLAUDE_MAX_TOKENS
    TEMPERATURE = CLAUDE_TEMPERATURE
    BATCH_SIZE = CLAUDE_BATCH_SIZE

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
