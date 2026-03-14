#!/bin/bash
# Deploy vLLM with LoRA adapter as OpenAI-compatible server

MODEL="Qwen/Qwen2.5-3B-Instruct"
ADAPTER_PATH="/home/azureuser/inclusify/ml/adapters/qwen_r8_d0.2"
PORT=8000

echo "=========================================="
echo "Starting vLLM Server with LoRA Adapter"
echo "=========================================="
echo "Model: $MODEL"
echo "Adapter: $ADAPTER_PATH"
echo "Port: $PORT"
echo ""

# Activate venv
source /home/azureuser/vllm-venv/bin/activate

# Start vLLM server
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --enable-lora \
    --lora-modules inclusify=$ADAPTER_PATH \
    --max-lora-rank 64 \
    --port $PORT \
    --host 0.0.0.0 \
    --dtype float16 \
    --gpu-memory-utilization 0.9 \
    --max-model-len 2048 \
    --trust-remote-code \
    2>&1 | tee /home/azureuser/inclusify/ml/analysis/vllm_server.log
