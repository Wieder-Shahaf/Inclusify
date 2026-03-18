"""Tests for automated grid search training script.

Note: These tests verify code structure without running training.
Full integration tests will run on VM with GPU.
"""

import pytest
import inspect
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


def test_script_exists():
    """Test that train_qwen_grid.py exists and is readable."""
    script_path = Path(__file__).parent.parent / "train_qwen_grid.py"
    assert script_path.exists(), "train_qwen_grid.py not found"
    assert script_path.is_file(), "train_qwen_grid.py is not a file"


def test_script_structure():
    """Test script has required functions and patterns."""
    script_path = Path(__file__).parent.parent / "train_qwen_grid.py"
    source = script_path.read_text()

    # Check for key functions
    assert "def create_lora_config(" in source, "Missing create_lora_config function"
    assert "def train_single_config(" in source, "Missing train_single_config function"
    assert "def main():" in source, "Missing main function"

    # Check for key imports
    assert "from peft import LoraConfig" in source, "Missing LoraConfig import"
    assert "from trl import SFTTrainer" in source, "Missing SFTTrainer import"
    assert "import torch" in source, "Missing torch import"

    # Check for GPU cleanup
    assert "torch.cuda.empty_cache()" in source, "Missing GPU memory cleanup"

    # Check for grid iteration
    assert "get_grid()" in source, "Missing grid search loop"
    assert "for i, (rank, alpha, dropout)" in source, "Missing grid iteration"


def test_create_lora_config_signature():
    """Test create_lora_config has correct signature."""
    script_path = Path(__file__).parent.parent / "train_qwen_grid.py"
    source = script_path.read_text()

    # Verify function signature
    assert "def create_lora_config(rank: int, alpha: int, dropout: float)" in source


def test_train_single_config_signature():
    """Test train_single_config has all required parameters."""
    script_path = Path(__file__).parent.parent / "train_qwen_grid.py"
    source = script_path.read_text()

    # Check for all expected parameters
    expected_params = [
        "base_model", "tokenizer", "train_dataset", "val_dataset",
        "rank", "alpha", "dropout", "config_name",
        "config_num", "total_configs"
    ]

    for param in expected_params:
        assert f"{param}:" in source or f"{param}," in source, f"Missing parameter: {param}"


def test_config_name_format():
    """Test that config names follow expected format."""
    script_path = Path(__file__).parent.parent / "train_qwen_grid.py"
    source = script_path.read_text()

    # Verify config name format
    assert 'config_name = f"qwen_r{rank}_d{dropout}"' in source


def test_error_handling():
    """Test that grid search has error handling."""
    script_path = Path(__file__).parent.parent / "train_qwen_grid.py"
    source = script_path.read_text()

    # Check for try-except around training
    assert "try:" in source and "except Exception as e:" in source, "Missing error handling"
    assert '"error": str(e)' in source, "Missing error recording"


def test_results_saving():
    """Test that results are saved to JSON."""
    script_path = Path(__file__).parent.parent / "train_qwen_grid.py"
    source = script_path.read_text()

    # Check for results saving
    assert 'grid_search_results.json' in source, "Missing results file"
    assert "json.dump(results" in source, "Missing JSON dump"


def test_lora_config_parameters():
    """Test that LoRA config has required parameters."""
    script_path = Path(__file__).parent.parent / "train_qwen_grid.py"
    source = script_path.read_text()

    # Check LoraConfig parameters
    assert "r=rank" in source, "Missing rank parameter"
    assert "lora_alpha=alpha" in source, "Missing alpha parameter"
    assert "lora_dropout=dropout" in source, "Missing dropout parameter"
    assert "target_modules=CONFIG.target_modules" in source, "Missing target_modules"
    assert 'task_type="CAUSAL_LM"' in source, "Missing task_type"


def test_grid_config_import():
    """Test that grid configuration is imported correctly."""
    from ml.training.config import get_grid

    grid = get_grid()
    assert len(grid) == 9, f"Expected 9 configs, got {len(grid)}"

    # Verify all configs have correct structure
    for rank, alpha, dropout in grid:
        assert isinstance(rank, int), "Rank should be int"
        assert isinstance(alpha, int), "Alpha should be int"
        assert isinstance(dropout, float), "Dropout should be float"
        assert alpha == 2 * rank, f"Alpha scaling incorrect: {alpha} != 2*{rank}"
