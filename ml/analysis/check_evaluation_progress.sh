#!/bin/bash
# Monitor evaluation progress on Azure VM

VM_HOST="azureuser@52.224.246.238"
LOG_FILE="~/inclusify/ml/analysis/evaluation.log"

echo "Checking evaluation progress on Azure VM..."
echo "============================================"

# Check if process is running
RUNNING=$(ssh $VM_HOST "ps aux | grep 'evaluate_metrics' | grep -v grep | wc -l")

if [ "$RUNNING" -eq "0" ]; then
    echo "❌ Evaluation process is not running!"
    echo ""
    echo "Last 50 lines of log:"
    ssh $VM_HOST "tail -50 $LOG_FILE"
    exit 1
fi

echo "✓ Evaluation process is running"
echo ""

# Get GPU status
echo "GPU Status:"
ssh $VM_HOST "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader"
echo ""

# Check log for progress
echo "Latest progress:"
ssh $VM_HOST "tail -20 $LOG_FILE | grep -E '(Progress:|Precision:|Recall:|F1|saved|Complete)' | tail -10"
echo ""

# Check log size (indication of progress)
LOG_SIZE=$(ssh $VM_HOST "wc -c < $LOG_FILE")
echo "Log file size: $((LOG_SIZE / 1024)) KB"
echo ""

# Estimate progress from log
PROGRESS=$(ssh $VM_HOST "tail -50 $LOG_FILE | grep 'Progress:' | tail -1")
if [ -n "$PROGRESS" ]; then
    echo "Current: $PROGRESS"
else
    echo "Model loading or inference in progress..."
fi

echo ""
echo "To view full log: ssh $VM_HOST 'tail -f $LOG_FILE'"
