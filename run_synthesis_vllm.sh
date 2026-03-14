#!/bin/bash
# Run dataset synthesis using vLLM (requires GPU)

echo "=== Dataset Synthesis with vLLM ==="
echo ""
echo "This requires a running vLLM server with GPU."
echo "Expected time: ~10 minutes for 10K samples"
echo "Expected cost: $0"
echo ""

# Check for vLLM server
echo "Checking vLLM server health..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: vLLM server not responding at http://localhost:8000"
    echo ""
    echo "Please start vLLM server first:"
    echo "  vllm serve Qwen/Qwen2.5-3B-Instruct \\"
    echo "    --port 8000 \\"
    echo "    --gpu-memory-utilization 0.9 \\"
    echo "    --max-model-len 3072 \\"
    echo "    --trust-remote-code"
    echo ""
    exit 1
fi

echo "✓ vLLM server is running"
echo ""

# Run quick test
echo "Running quick test..."
if ! python scripts/quick_qwen_test.py > /tmp/vllm_test.log 2>&1; then
    echo "✗ Quick test failed. Check /tmp/vllm_test.log for details"
    cat /tmp/vllm_test.log
    exit 1
fi

echo "✓ Quick test passed"
echo ""

# Set vLLM mode
export VLLM_ENABLED=true
export VLLM_ENDPOINT="http://localhost:8000/v1"
export VLLM_BATCH_SIZE=64
export VLLM_MAX_THROUGHPUT=30

echo "Configuration:"
echo "  Backend: vLLM"
echo "  Model: Qwen/Qwen2.5-3B-Instruct"
echo "  Batch size: 64 requests"
echo "  Max throughput: 30 req/sec"
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
