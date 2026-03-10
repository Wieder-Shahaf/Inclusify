#!/bin/bash
set -euo pipefail

# Inclusify vLLM VM Verification Script
# Usage: ./scripts/test-vllm-vm.sh [VM_IP]

# Get VM IP from argument or Azure CLI
VM_IP="${1:-}"
if [ -z "$VM_IP" ]; then
    echo "Discovering VM IP from Azure..."
    VM_IP=$(az network public-ip show --resource-group Group07 --name InclusifyModel-ip --query ipAddress -o tsv)
fi

if [ -z "$VM_IP" ]; then
    echo "ERROR: Could not determine VM IP. Pass as argument or ensure Azure CLI is configured."
    exit 1
fi

echo "=== Inclusify vLLM VM Verification ==="
echo "VM IP: $VM_IP"
echo ""

PASS=0
FAIL=0

# Test 1: Service status
echo "[1/4] Checking vLLM service status..."
if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no azureuser@$VM_IP "sudo systemctl is-active vllm" &>/dev/null; then
    echo "  PASS: vLLM service is active"
    ((PASS++))
else
    echo "  FAIL: vLLM service is not active"
    ((FAIL++))
fi

# Test 2: Health endpoint
echo "[2/4] Checking /v1/models endpoint..."
MODELS=$(ssh -o StrictHostKeyChecking=no azureuser@$VM_IP "curl -s http://localhost:8001/v1/models" 2>/dev/null)
if echo "$MODELS" | grep -q '"data"'; then
    echo "  PASS: /v1/models returns model list"
    ((PASS++))
else
    echo "  FAIL: /v1/models did not return expected response"
    ((FAIL++))
fi

# Test 3: English inference
echo "[3/4] Testing English inference..."
ENGLISH_RESPONSE=$(ssh -o StrictHostKeyChecking=no azureuser@$VM_IP 'curl -s http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '"'"'{
    "model": "/home/azureuser/models/Qwen2.5-3B-Instruct-GPTQ-Int4",
    "messages": [{"role": "user", "content": "Hello, how are you?"}],
    "max_tokens": 50
  }'"'"'' 2>/dev/null)
if echo "$ENGLISH_RESPONSE" | grep -q '"choices"'; then
    echo "  PASS: English inference successful"
    ((PASS++))
else
    echo "  FAIL: English inference failed"
    echo "  Response: $ENGLISH_RESPONSE"
    ((FAIL++))
fi

# Test 4: Hebrew inference
echo "[4/4] Testing Hebrew inference..."
HEBREW_RESPONSE=$(ssh -o StrictHostKeyChecking=no azureuser@$VM_IP 'curl -s http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '"'"'{
    "model": "/home/azureuser/models/Qwen2.5-3B-Instruct-GPTQ-Int4",
    "messages": [{"role": "user", "content": "'\u05e9\u05dc\u05d5\u05dd, \u05de\u05d4 \u05e9\u05dc\u05d5\u05de\u05da?'"}],
    "max_tokens": 50
  }'"'"'' 2>/dev/null)
if echo "$HEBREW_RESPONSE" | grep -q '"choices"'; then
    echo "  PASS: Hebrew inference successful"
    ((PASS++))
else
    echo "  FAIL: Hebrew inference failed"
    echo "  Response: $HEBREW_RESPONSE"
    ((FAIL++))
fi

# Summary
echo ""
echo "=== Results ==="
echo "PASS: $PASS / $((PASS + FAIL))"
echo "FAIL: $FAIL / $((PASS + FAIL))"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo "All tests passed! vLLM is ready for inference."
    exit 0
else
    echo ""
    echo "Some tests failed. Check vLLM logs: ssh azureuser@$VM_IP 'sudo journalctl -u vllm -n 100'"
    exit 1
fi
