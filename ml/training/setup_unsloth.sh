#!/bin/bash
# Setup script for Unsloth framework on Azure VM
# Based on: https://unsloth.ai/docs/models/qwen3.5/fine-tune

set -e  # Exit on error

echo "================================================================"
echo "Installing Unsloth for Qwen3.5 Fine-tuning"
echo "================================================================"

# Activate virtual environment
source /home/azureuser/vllm-venv/bin/activate

# Check CUDA version
echo ""
echo "Checking CUDA version..."
nvcc --version || echo "NVCC not found in PATH"
nvidia-smi | head -20

# Install Unsloth
echo ""
echo "Installing Unsloth..."
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

# Verify installation
echo ""
echo "Verifying Unsloth installation..."
python3 << 'EOF'
try:
    from unsloth import FastLanguageModel
    print("✓ Unsloth installed successfully")
    print(f"  FastLanguageModel: {FastLanguageModel}")
except ImportError as e:
    print(f"✗ Unsloth import failed: {e}")
    exit(1)
EOF

echo ""
echo "================================================================"
echo "✓ Unsloth setup complete!"
echo "================================================================"
echo ""
echo "Next steps:"
echo "  1. Copy training script to VM:"
echo "     scp ~/inclusify/ml/training/train_qwen3_unsloth.py azureuser@52.224.246.238:~/inclusify/ml/training/"
echo ""
echo "  2. Run training:"
echo "     cd ~/inclusify && python ml/training/train_qwen3_unsloth.py"
echo ""
