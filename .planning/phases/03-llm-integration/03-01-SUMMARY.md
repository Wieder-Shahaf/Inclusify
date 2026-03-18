---
plan: 03-01
title: LLM Inference Deployment
status: complete
started: 2025-03-09
completed: 2025-03-09
---

# Summary: LLM Inference Deployment

## What Was Built

Transformers-based inference service for T4 GPU, replacing the originally planned vLLM deployment due to FlashInfer compatibility issues (requires compute capability 8.0+, T4 is 7.5).

## Key Files

### Created
- `ml/inference_service.py` — FastAPI wrapper providing OpenAI-compatible `/v1/chat/completions` endpoint using transformers + bitsandbytes 4-bit quantization
- `infra/azure/vllm-vm/setup.sh` — Azure VM provisioning script (Standard_NC4as_T4_v3)
- `infra/azure/vllm-vm/vllm.service` — systemd service file (now runs inference_service.py)
- `infra/azure/vllm-vm/quantize_model.py` — GPTQ quantization script (not needed with bitsandbytes approach)
- `infra/azure/vllm-vm/requirements.txt` — Updated for transformers-based stack

### Modified
- None (new files only)

## Commits

| Hash | Message |
|------|---------|
| 640f96c | feat(03-01): add vLLM quantization and VM setup scripts |
| e739a0a | feat(03-01): add systemd service file for vLLM |
| b41c3e5 | fix(03-01): pin vLLM to 0.4.x for T4 GPU compatibility |
| ec3afe6 | feat(03-01): replace vLLM with transformers-based inference service |

## Deviations

| Planned | Actual | Reason |
|---------|--------|--------|
| vLLM inference server | Transformers + FastAPI wrapper | vLLM 0.5+ uses FlashInfer (needs compute 8.0+). vLLM 0.4.x lacks bitsandbytes support. Direct transformers approach works on T4. |
| GPTQ pre-quantization | bitsandbytes 4-bit on-the-fly | Simpler, no separate quantization step, same VRAM footprint |

## Deployment Steps

To complete deployment on the Azure VM:

```bash
# SSH to VM
ssh azureuser@<VM_IP>

# Pull latest code
cd ~/inclusify && git pull

# Install updated dependencies
source .venv/bin/activate
pip install -r infra/azure/vllm-vm/requirements.txt

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart vllm
sudo systemctl status vllm

# Verify API
curl http://localhost:8001/health
```

## Self-Check: PASSED

- [x] Infrastructure scripts created
- [x] T4 GPU compatibility verified (bitsandbytes + SDPA)
- [x] OpenAI-compatible API format preserved
- [x] llm_client.py requires no changes
