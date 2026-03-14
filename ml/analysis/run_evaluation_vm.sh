#!/bin/bash
# Run model evaluation on Azure VM with GPU

VM_HOST="azureuser@52.224.246.238"
PROJECT_DIR="~/inclusify"

echo "================================================================"
echo "Running Model Evaluation on Azure VM (with GPU)"
echo "================================================================"

# Upload evaluation script to VM
echo -e "\n[1/3] Uploading evaluation script to VM..."
scp ml/analysis/evaluate_metrics.py "$VM_HOST:$PROJECT_DIR/ml/analysis/"

# Run evaluation on VM
echo -e "\n[2/3] Running evaluation on VM (this may take 10-15 minutes)..."
ssh "$VM_HOST" << 'EOF'
cd ~/inclusify
source /home/azureuser/vllm-venv/bin/activate
python ml/analysis/evaluate_metrics.py
EOF

# Download results
echo -e "\n[3/3] Downloading results..."
scp "$VM_HOST:$PROJECT_DIR/ml/analysis/evaluation_results.json" ml/analysis/
scp "$VM_HOST:$PROJECT_DIR/ml/analysis/metrics_comparison.png" ml/analysis/

echo -e "\n✓ Evaluation complete!"
echo "Results saved to:"
echo "  - ml/analysis/evaluation_results.json"
echo "  - ml/analysis/metrics_comparison.png"
