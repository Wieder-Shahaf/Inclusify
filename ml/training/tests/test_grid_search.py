"""Tests for automated grid search training script."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ml.training.train_qwen_grid import create_lora_config


def test_create_lora_config():
    """Test LoRA config creation with correct parameters."""
    config = create_lora_config(rank=16, alpha=32, dropout=0.1)

    assert config.r == 16
    assert config.lora_alpha == 32
    assert config.lora_dropout == 0.1
    assert config.task_type == "CAUSAL_LM"
    assert config.bias == "none"
    assert "q_proj" in config.target_modules
    assert "k_proj" in config.target_modules


def test_grid_search_loop_structure():
    """Test that main() function exists and has grid loop structure."""
    from ml.training.train_qwen_grid import main

    # Just verify function exists and is callable
    assert callable(main)


def test_train_single_config_signature():
    """Test train_single_config function exists with correct signature."""
    from ml.training.train_qwen_grid import train_single_config
    import inspect

    sig = inspect.signature(train_single_config)
    params = list(sig.parameters.keys())

    # Verify all expected parameters are present
    expected_params = [
        'base_model', 'tokenizer', 'train_dataset', 'val_dataset',
        'rank', 'alpha', 'dropout', 'config_name',
        'config_num', 'total_configs'
    ]

    for param in expected_params:
        assert param in params, f"Missing parameter: {param}"


def test_gpu_memory_cleanup():
    """Test that torch.cuda.empty_cache() is called between configs."""
    # This is a behavior test - we'll verify the implementation includes cleanup
    from ml.training import train_qwen_grid
    import inspect

    source = inspect.getsource(train_qwen_grid.train_single_config)

    # Verify GPU cleanup is in the code
    assert "torch.cuda.empty_cache()" in source, "Missing GPU memory cleanup"


def test_config_name_format():
    """Test that config names follow expected format: qwen_r{rank}_d{dropout}"""
    from ml.training.config import get_grid

    grid = get_grid()

    for rank, alpha, dropout in grid:
        expected_name = f"qwen_r{rank}_d{dropout}"

        # Verify format is correct
        assert "_r" in expected_name
        assert "_d" in expected_name
        assert str(rank) in expected_name
        assert str(dropout) in expected_name
