#!/bin/bash
# VM Cleanup Script for DictaLM Deployment

echo "=== VM Cleanup for DictaLM Deployment ==="
echo ""

# Stop vLLM
echo "1. Stopping vLLM processes..."
pkill -f vllm
sleep 3
ps aux | grep vllm | grep -v grep || echo "  ✓ All vLLM stopped"

# Check initial space
echo ""
echo "2. Current disk usage:"
df -h / | grep /dev/root

# Delete pip cache
echo ""
echo "3. Cleaning pip cache..."
rm -rf ~/.cache/pip/*
du -sh ~/.cache/pip 2>/dev/null || echo "  ✓ Pip cache deleted"

# Delete temp logs
echo ""
echo "4. Cleaning temp logs..."
rm -f /tmp/*.log
rm -f /tmp/vllm*.log
rm -f /tmp/synthesis*.log
echo "  ✓ Temp logs deleted"

# Delete old DictaLM 1.7B
echo ""
echo "5. Removing unused models..."
rm -rf ~/.cache/huggingface/dictalm-1.7b-thinking
echo "  ✓ DictaLM-1.7B removed"

# Clean Python caches
echo ""
echo "6. Cleaning Python caches..."
find ~/inclusify -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo "  ✓ Python caches cleaned"

# Final space check
echo ""
echo "7. Final disk usage:"
df -h / | grep /dev/root

echo ""
echo "=== Cleanup Complete ==="
