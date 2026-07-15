"""Modal serverless deployment of the Inclusify vLLM inference server.

Replaces the Azure T4 VM (infra/azure/vllm-vm/vllm.service). Serves the
Qwen2.5-3B-Instruct base model with the fine-tuned `inclusify` LoRA adapter over
an OpenAI-compatible API, scaling to zero when idle.

Validated environment — read directly from the Azure VM "InclusifyModel"
(rg Group07) on 2026-06-27, then the VM was deallocated:

    vLLM 0.17.1 | torch 2.10.0 | transformers 4.57.6 | peft 0.18.1
    Python 3.10.12 | Tesla T4 (driver 535.274.02)
    Base : Qwen/Qwen2.5-3B-Instruct  (FP16; served with --dtype half on T4)
    LoRA : qwen_r8_d0.2_achva_v2  (r=8, alpha=16, dropout=0.2)  served as "inclusify"

The serve flags below are copied 1:1 from the *live* systemd ExecStart on that
VM (which already uses the achva_v2 adapter — the committed vllm.service still
references the older qwen_r8_d0.2 and is stale).

Setup (one-time)
    modal secret create inclusify-vllm-key VLLM_API_KEY=<generate-a-strong-key>

Deploy
    modal deploy infra/modal/vllm_app.py

Wire up the backend (per docs/STACK-A-MIGRATION.md §2.2, §3)
    VLLM_URL=https://<workspace>--inclusify-vllm-serve.modal.run
    VLLM_API_KEY=<same value as the Modal secret>     # backend sends Bearer <key>
    VLLM_MODEL_NAME=inclusify                          # already the default

Smoke test against the deployed endpoint
    cd backend && VLLM_URL=<url> python -m pytest tests/test_vllm_integration.py -v
"""

import os
import subprocess
from pathlib import Path

import modal

# --- Versions: pinned to exactly what was validated on the Azure T4 VM --------
# (Changing these means re-validating against the T4 + the r=8 LoRA.)
VLLM_VERSION = "0.17.1"
PYTHON_VERSION = "3.10"  # VM ran 3.10.12; vLLM 0.17.1 ships wheels for 3.10

# --- Model / adapter identity ------------------------------------------------
BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
BASE_MODEL_DIR = "/models/Qwen2.5-3B-Instruct"  # baked into the image at build

# The LoRA module name MUST equal the backend's settings.VLLM_MODEL_NAME
# ("inclusify"); the backend sends it as the OpenAI `model` field on every call.
ADAPTER_NAME = "inclusify"
# Only used locally at deploy time (add_local_dir below). Modal re-imports this
# module inside the build container as /root/vllm_app.py, where parents[2] doesn't
# exist — fall back to the file's dir so import doesn't crash there (the value is
# never read in-container; the runtime uses ADAPTER_REMOTE_DIR).
_here = Path(__file__).resolve()
_repo_root = _here.parents[2] if len(_here.parents) > 2 else _here.parent
ADAPTER_LOCAL_DIR = _repo_root / "ml" / "adapters" / "qwen_r8_d0.2_achva_v2"
ADAPTER_REMOTE_DIR = "/adapters/qwen_r8_d0.2_achva_v2"

VLLM_PORT = 8001  # same internal port as the VM (Modal still serves it over HTTPS)
MINUTES = 60
HOURS = 60 * MINUTES

app = modal.App("inclusify-vllm")


def _download_base_model() -> None:
    """Bake base weights into the image at build time.

    Per docs/STACK-A-MIGRATION.md §2.4/§4.1: a cold start must be a local VRAM
    load, never a runtime HuggingFace download. Downloading here (during the
    image build) burns the weights into an image layer.
    """
    from huggingface_hub import snapshot_download

    snapshot_download(
        BASE_MODEL,
        local_dir=BASE_MODEL_DIR,
        # Qwen2.5-3B-Instruct ships safetensors; skip the redundant formats.
        ignore_patterns=["*.pt", "*.pth", "*.bin", "*.gguf"],
    )


# Modal's current idiomatic vLLM image: CUDA devel base + uv_pip_install.
vllm_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python=PYTHON_VERSION
    )
    .entrypoint([])  # the CUDA image sets an entrypoint that would shadow ours
    .uv_pip_install(
        f"vllm=={VLLM_VERSION}",
        "huggingface_hub[hf_transfer]",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .run_function(_download_base_model)  # base weights -> image layer
    # LoRA adapter (Git LFS weights, ~60 MB) copied from the repo into the image:
    .add_local_dir(ADAPTER_LOCAL_DIR.as_posix(), ADAPTER_REMOTE_DIR, copy=True)
)


@app.function(
    image=vllm_image,
    gpu="T4",  # same GPU class as the Azure Standard_NC4as_T4_v3
    scaledown_window=3 * HOURS,  # stay warm 3 h after last request, then -> 0
    timeout=10 * MINUTES,
    secrets=[modal.Secret.from_name("inclusify-vllm-key")],
    # enable_memory_snapshot=True,  # see NOTES — verify GPU-snapshot support on
    #                                 this Modal/vLLM combo before enabling.
)
@modal.concurrent(max_inputs=16)  # matches backend VLLM_MAX_CONCURRENT / --max-num-seqs
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve() -> None:
    # Flags copied 1:1 from the live systemd ExecStart on InclusifyModel.
    cmd = [
        "vllm", "serve", BASE_MODEL_DIR,
        "--served-model-name", BASE_MODEL,
        "--dtype", "half",  # T4 (Turing) has no bf16
        "--max-model-len", "4096",
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--gpu-memory-utilization", "0.88",
        "--max-num-seqs", "16",
        "--max-num-batched-tokens", "8192",
        "--enable-lora",
        "--lora-modules", f"{ADAPTER_NAME}={ADAPTER_REMOTE_DIR}",
        "--max-lora-rank", "16",
    ]

    # Auth: the backend sends `Authorization: Bearer <key>`, which is exactly the
    # scheme vLLM's --api-key enforces. The `inclusify-vllm-key` secret injects
    # VLLM_API_KEY into the env; pass it through explicitly when present. (Local
    # dev with no secret value => no auth, matching the VM's optional-auth setup.)
    api_key = os.environ.get("VLLM_API_KEY")
    if api_key:
        cmd += ["--api-key", api_key]

    subprocess.Popen(cmd)


# --- NOTES -------------------------------------------------------------------
# Cold start: a 3B FP16 model from an image layer loads in ~30-60s on a T4. The
#   backend's VLLM_TIMEOUT=120s and circuit breaker (3 fails / 60s) tolerate
#   this, but the first request after idle may trip one breaker count — consider
#   bumping VLLM_CIRCUIT_FAIL_MAX to 5 (docs/STACK-A-MIGRATION.md §2.4).
#
# Memory snapshots: Modal can snapshot/restore container state to cut cold-start
#   duration further. GPU/CUDA snapshotting has constraints that vary by Modal
#   version — confirm support for this vLLM 0.17.1 setup (Modal docs "Memory
#   Snapshots") before flipping enable_memory_snapshot=True above.
#
# Cost guardrail: never set min_containers>=1 and never let the frontend's
#   health poll keep this warm 24/7 — that converts the whole month into billed
#   idle (~$430/mo). The §2.3 health-poll cache fix is mandatory, not optional.
