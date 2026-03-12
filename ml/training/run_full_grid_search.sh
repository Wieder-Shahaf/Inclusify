#!/bin/bash
set -e  # Exit on error

# Master orchestration script for complete LoRA adapter grid search
# Runs Qwen2.5-3B and Qwen3.5-0.8B sequentially, then shuts down VM

LOG_DIR="/home/azureuser/inclusify/ml/logs"
mkdir -p "$LOG_DIR"

MASTER_LOG="$LOG_DIR/master_grid_search.log"

echo "================================================================" | tee -a "$MASTER_LOG"
echo "Starting Full Grid Search Pipeline" | tee -a "$MASTER_LOG"
echo "Started: $(date)" | tee -a "$MASTER_LOG"
echo "================================================================" | tee -a "$MASTER_LOG"

# Activate virtual environment
source /home/azureuser/vllm-venv/bin/activate

cd /home/azureuser/inclusify

# ================================================================
# PHASE 1: Qwen2.5-3B Grid Search
# ================================================================

echo "" | tee -a "$MASTER_LOG"
echo "================================================================" | tee -a "$MASTER_LOG"
echo "PHASE 1: Qwen2.5-3B Grid Search (9 configs)" | tee -a "$MASTER_LOG"
echo "================================================================" | tee -a "$MASTER_LOG"

python ml/training/train_qwen_grid.py 2>&1 | tee "$LOG_DIR/qwen2.5_grid.log"

QWEN25_EXIT=$?

if [ $QWEN25_EXIT -eq 0 ]; then
    echo "✓ Qwen2.5-3B grid search completed successfully" | tee -a "$MASTER_LOG"

    # Count successful configs
    QWEN25_SUCCESS=$(cat /home/azureuser/inclusify/ml/adapters/grid_search_results.json | python3 -c "import json, sys; data=json.load(sys.stdin); print(len([r for r in data if 'error' not in r]))" 2>/dev/null || echo "0")
    echo "  → $QWEN25_SUCCESS/9 configs completed" | tee -a "$MASTER_LOG"
else
    echo "✗ Qwen2.5-3B grid search failed with exit code $QWEN25_EXIT" | tee -a "$MASTER_LOG"
    echo "  → Continuing to Qwen3.5 anyway..." | tee -a "$MASTER_LOG"
fi

# ================================================================
# PHASE 2: Qwen3.5-0.8B Grid Search
# ================================================================

echo "" | tee -a "$MASTER_LOG"
echo "================================================================" | tee -a "$MASTER_LOG"
echo "PHASE 2: Qwen3.5-0.8B Grid Search (9 configs)" | tee -a "$MASTER_LOG"
echo "================================================================" | tee -a "$MASTER_LOG"

python ml/training/train_qwen3_grid.py 2>&1 | tee "$LOG_DIR/qwen3.5_grid.log"

QWEN3_EXIT=$?

if [ $QWEN3_EXIT -eq 0 ]; then
    echo "✓ Qwen3.5-0.8B grid search completed successfully" | tee -a "$MASTER_LOG"

    # Count successful configs
    QWEN3_SUCCESS=$(cat /home/azureuser/inclusify/ml/adapters/qwen3/grid_search_results.json | python3 -c "import json, sys; data=json.load(sys.stdin); print(len([r for r in data if 'error' not in r]))" 2>/dev/null || echo "0")
    echo "  → $QWEN3_SUCCESS/9 configs completed" | tee -a "$MASTER_LOG"
else
    echo "✗ Qwen3.5-0.8B grid search failed with exit code $QWEN3_EXIT" | tee -a "$MASTER_LOG"
fi

# ================================================================
# SUMMARY
# ================================================================

echo "" | tee -a "$MASTER_LOG"
echo "================================================================" | tee -a "$MASTER_LOG"
echo "Grid Search Pipeline Complete" | tee -a "$MASTER_LOG"
echo "Completed: $(date)" | tee -a "$MASTER_LOG"
echo "================================================================" | tee -a "$MASTER_LOG"

# Duration
START_TIME=$(head -1 "$MASTER_LOG" | grep -oP '\d{2}:\d{2}:\d{2}' || echo "unknown")
END_TIME=$(date +%H:%M:%S)
echo "Started: $START_TIME" | tee -a "$MASTER_LOG"
echo "Ended: $END_TIME" | tee -a "$MASTER_LOG"

# Results summary
echo "" | tee -a "$MASTER_LOG"
echo "Results:" | tee -a "$MASTER_LOG"
echo "  Qwen2.5-3B: ${QWEN25_SUCCESS:-?}/9 configs" | tee -a "$MASTER_LOG"
echo "  Qwen3.5-0.8B: ${QWEN3_SUCCESS:-?}/9 configs" | tee -a "$MASTER_LOG"
echo "" | tee -a "$MASTER_LOG"
echo "Logs:" | tee -a "$MASTER_LOG"
echo "  Master: $MASTER_LOG" | tee -a "$MASTER_LOG"
echo "  Qwen2.5: $LOG_DIR/qwen2.5_grid.log" | tee -a "$MASTER_LOG"
echo "  Qwen3.5: $LOG_DIR/qwen3.5_grid.log" | tee -a "$MASTER_LOG"
echo "" | tee -a "$MASTER_LOG"
echo "Adapters:" | tee -a "$MASTER_LOG"
echo "  Qwen2.5: /home/azureuser/inclusify/ml/adapters/" | tee -a "$MASTER_LOG"
echo "  Qwen3.5: /home/azureuser/inclusify/ml/adapters/qwen3/" | tee -a "$MASTER_LOG"

# ================================================================
# AUTO-SHUTDOWN
# ================================================================

echo "" | tee -a "$MASTER_LOG"
echo "================================================================" | tee -a "$MASTER_LOG"
echo "Auto-shutdown in 60 seconds..." | tee -a "$MASTER_LOG"
echo "Cancel with: sudo shutdown -c" | tee -a "$MASTER_LOG"
echo "================================================================" | tee -a "$MASTER_LOG"

# Give 60 seconds to cancel if needed
sleep 60

echo "Shutting down VM..." | tee -a "$MASTER_LOG"
sudo shutdown -h now
