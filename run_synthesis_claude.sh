#!/bin/bash
# Run dataset synthesis using Claude API (no GPU required)

echo "=== Dataset Synthesis with Claude API ==="
echo ""
echo "This will use the Claude Batch API instead of vLLM."
echo "Expected time: 12-24 hours for 10K samples"
echo "Expected cost: ~$15"
echo ""

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set"
    echo ""
    echo "Please set your API key:"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo ""
    exit 1
fi

# Set Claude mode
export VLLM_ENABLED=false

echo "Configuration:"
echo "  Backend: Claude Batch API"
echo "  Model: claude-opus-4-20250514"
echo "  Batch size: 2000 requests"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Run synthesis
cd ml/data_synthesis
python synthesize_english.py
