# Stack A Migration Assessment — Azure → Modal + Railway + Cloudflare R2

**Date:** June 12, 2026
**Verdict: Compatible with moderate, well-isolated changes.** The codebase is ~90% env-var-driven and fully Dockerized (except the GPU layer, which Modal doesn't need a Dockerfile for anyway). There is exactly **one hard Azure dependency in application code** (blob storage), **one missing capability** (API-key auth on the vLLM client), and **one architectural trap** that would silently defeat scale-to-zero (the 30-second model health poll). Everything else is configuration.

---

## 1. Compatibility matrix

| Layer | Current (Azure) | Stack A target | Compatible? | Work needed |
|---|---|---|---|---|
| Backend container | Container Apps, `infra/docker/backend.Dockerfile` (python:3.12-slim, non-root, port 8000) | Railway service | ✅ as-is | Point Railway at the Dockerfile (`runtime` target) |
| Frontend container | Container Apps, `infra/docker/frontend.Dockerfile` (node:22-slim, Next standalone, port 3000) | Railway service | ✅ as-is | `NEXT_PUBLIC_API_URL` must be set as a **build-time** variable on Railway (it's inlined at build) |
| PostgreSQL | Azure Flexible Server (B1ms) | Railway Postgres | ✅ | Re-point `PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE/PGSSL`; apply `db/schema.sql` + `db/seed.sql` once |
| Redis | docker-compose dev only (refresh tokens; optional) | Railway Redis | ✅ | Set `REDIS_URL`. App already degrades gracefully without it |
| Object storage | Azure Blob (`azure-storage-blob` SDK) | Cloudflare R2 | ❌ **code change** | Rewrite `backend/app/core/blob_storage.py` (~1 module, 2 functions) to S3-compatible client |
| GPU / vLLM | T4 VM, systemd service, private VNet IP `10.0.0.4:8001` | Modal serverless | ⚠️ **code change** | Add `Authorization` header support to `llm_client.py`; write a Modal app (~100 lines); fix health-poll trap |
| CI/CD | `.github/workflows/deploy.yml` → ACR push, manual `az containerapp update` | Railway GitHub integration | ⚠️ config | Railway auto-deploys on push; delete/replace ACR workflow |
| Dev environment | docker-compose with Azurite emulator | — | ⚠️ config | Replace Azurite with MinIO (S3-compatible, matches R2) |

---

## 2. Required code changes (in priority order)

### 2.1 `backend/app/core/blob_storage.py` — the only hard Azure SDK dependency
The whole Azure surface is two functions: `upload_text(sha256, text)` and `upload_file_bytes(sha256, filename, data)`. R2 is S3-compatible, so swap `azure-storage-blob` for `boto3` (or `aioboto3` to keep it async):

```python
# settings additions (config.py) — replaces AZURE_STORAGE_CONNECTION_STRING
S3_ENDPOINT_URL: str = ""      # https://<ACCOUNT_ID>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID: str = ""
S3_SECRET_ACCESS_KEY: str = ""
S3_BUCKET: str = "texts"       # replaces AZURE_STORAGE_CONTAINER
```

Notes:
- The storage refs persisted in the DB are opaque strings (`blob://texts/<sha256>.txt`). Keep emitting the same format (or `r2://…`) — nothing else parses them, so no data migration of refs is needed.
- One-time data migration: `rclone sync` from the `inclusifystorage` account to the R2 bucket (R2 has free ingress and free egress).
- `requirements.txt`: remove `azure-storage-blob>=12.19.0`, add `boto3` (or `aioboto3`).
- Dev: replace the `azurite` service in `docker-compose.yml` with `minio/minio` so dev and prod speak the same S3 protocol.

### 2.2 `backend/app/modules/analysis/llm_client.py` — add bearer auth for Modal
All three `httpx.AsyncClient` POSTs to `{VLLM_URL}/v1/chat/completions` send **no Authorization header**. That was fine inside a private VNet; a Modal web endpoint is on the public internet and must be protected (Modal proxy auth or a vLLM `--api-key`). Add:

```python
# config.py
VLLM_API_KEY: str = ""   # empty = no auth header (local dev unchanged)

# llm_client.py — in each request
headers = {"Authorization": f"Bearer {settings.VLLM_API_KEY}"} if settings.VLLM_API_KEY else {}
```

Same change applies to the model health check in `app/routers/health.py` and, if you keep using it, `ml/data_synthesis/utils/vllm_processor.py`.

### 2.3 The scale-to-zero trap: the 30-second model health poll
`frontend/app/[locale]/analyze/page.tsx` calls `modelHealthCheck()` **every 30 seconds** while anyone has the analyze page open, and that endpoint reaches through to vLLM. On Azure (always-on VM) this is harmless. On Modal it means **any open browser tab keeps the GPU container warm — or worse, repeatedly cold-starts it** — and your $0–10/mo projection becomes $100+/mo.

Fix (small, do it as part of the migration):
- Make `/api/v1/health/model` answer from a cached probe (e.g., probe vLLM at most once every 5 minutes, serve the cached state) **and never trigger a cold start** — if the container is scaled to zero, report `"available": true, "state": "scale_to_zero"` since Modal will spin it up on the first real request.
- The frontend's "model unavailable" banner logic stays unchanged.

### 2.4 Modal app for the GPU layer (new file, `infra/modal/vllm_app.py`)
Nothing to port from a Dockerfile — Modal images are defined in Python. The current systemd unit translates directly:

```python
import modal

MODEL_DIR = "/models/Qwen2.5-3B-Instruct"
app = modal.App("inclusify-vllm")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("vllm==<pin to the version validated on the T4>")
)
volume = modal.Volume.from_name("inclusify-models", create_if_missing=True)

@app.function(
    image=image,
    gpu="T4",                      # same class as the Azure VM; A10G if you want headroom
    volumes={"/models": volume},   # weights + LoRA adapter cached on a Volume → fast cold starts
    scaledown_window=300,          # stay warm 5 min after last request, then scale to zero
    secrets=[modal.Secret.from_name("inclusify-vllm-key")],
)
@modal.web_server(port=8001)
def serve():
    import subprocess
    subprocess.Popen([
        "vllm", "serve", MODEL_DIR,
        "--port", "8001", "--dtype", "half",
        "--max-model-len", "4096", "--gpu-memory-utilization", "0.88",
        "--max-num-seqs", "16", "--max-num-batched-tokens", "8192",
        "--enable-lora", "--lora-modules", "inclusify=/models/adapters/qwen_r8_d0.2",
        "--api-key", "$VLLM_API_KEY",
    ])
```

Operational parameters carry over 1:1 from `infra/azure/vllm-vm/vllm.service` (`--max-num-seqs 16` already matches `VLLM_MAX_CONCURRENT=16` in the backend). One-time setup: upload model weights + the `qwen_r8_d0.2` LoRA adapter to the Modal Volume. Expect **cold starts of roughly 30–60s** for a 3B FP16 model loaded from a Volume; the backend's `VLLM_TIMEOUT=120s` and circuit breaker (3 failures / 60s reset) tolerate this, but the **first request after idle may trip one breaker count** — consider bumping `VLLM_CIRCUIT_FAIL_MAX` to 5, or have the backend send a warm-up ping when an upload starts (the user then "pays" the cold start during the Docling parse, which already takes tens of seconds).

> Note: a Modal deep-dive video was referenced in the task description but no link came through — the above is based on Modal's standard vLLM serving pattern (Volume-cached weights + `scaledown_window` + web_server).

### 2.5 Things that need **no** changes
- `backend/app/core/config.py` — fully env-driven; only *additions* (S3_*, VLLM_API_KEY).
- Both Dockerfiles — multi-stage, non-root, standalone output; Railway consumes them directly.
- asyncpg/SQLAlchemy layer — Railway Postgres is vanilla Postgres 16.
- Redis token store — already optional + `REDIS_URL`-driven.
- Frontend code — zero Azure references; only the build-time `NEXT_PUBLIC_API_URL`.

---

## 3. Configuration / environment variable mapping

| Variable | Azure value | Stack A value |
|---|---|---|
| `PGHOST` | `<server>.postgres.database.azure.com` | Railway Postgres host (use Railway's variable references) |
| `PGSSL` | `require` | `require` |
| `VLLM_URL` | `http://10.0.0.4:8001` (also a stale public IP `52.224.246.238` default in `docker-compose.yml` — remove it) | `https://<workspace>--inclusify-vllm-serve.modal.run` |
| `VLLM_API_KEY` | — (new) | Modal secret value |
| `AZURE_STORAGE_CONNECTION_STRING` / `AZURE_STORAGE_CONTAINER` | Azure | **removed** → `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET` |
| `REDIS_URL` | (dev only) | Railway Redis URL |
| `FRONTEND_URL` / `ALLOWED_ORIGINS` | `*.azurecontainerapps.io` FQDN | Railway domain(s) — also update the **Google OAuth authorized redirect URIs** in the Google Cloud console |
| `NEXT_PUBLIC_API_URL` | backend FQDN (build arg) | Railway backend public URL (Railway build-time var) |
| `JWT_SECRET`, `GOOGLE_CLIENT_*`, `RESEND_API_KEY`, SMTP vars | Container Apps secrets | Railway service variables (unchanged values) |

**Files that become dead after migration** (archive, don't delete until cutover is verified): `infra/scripts/azure-*.sh`, `infra/azure/vllm-vm/*`, the `azurite` compose service, `.github/workflows/deploy.yml` (ACR push), and the hardcoded `BACKEND_URL`/ACR names inside it. `.github/workflows/vllm-integration.yml` survives — just point its `VLLM_URL` secret at Modal and add the API key.

---

## 4. Cost reality check on the $5–15/mo projection

- **Modal**: $30/mo free credit covers ~50 T4-hours. With scale-to-zero and the health-poll fix, academic-project traffic plausibly stays inside free credit → **$0**, matching the projection. Without the health-poll fix, this blows up — that's the single biggest financial risk in the plan.
- **Railway**: the $5 Hobby plan includes $5 of usage. Four always-on services (frontend + backend + Postgres + Redis) typically land at **$10–20/mo** of usage, not $5 — the backend image is heavy (Docling + torch) and idles around 0.5–1 GB RAM. Expect the top of your range, not the bottom. Mitigation: Railway's serverless/app-sleep for the frontend, and consider whether Redis is worth a service at all (refresh tokens already degrade gracefully; a Postgres-backed token store would drop one service).
- **R2**: free tier (10 GB storage, free egress) is far above current usage → **$0**. ✅
- **Realistic total: $10–20/mo**, $0–10 of which is avoidable with the sleep/Redis optimizations. Still roughly 85–90% below the current Azure footprint (B1ms Postgres + Container Apps + T4 VM ≈ $150+/mo when the VM runs).

---

## 5. Suggested migration order (each step independently verifiable)

1. **Modal vLLM** first — deploy `infra/modal/vllm_app.py`, run `tests/test_vllm_integration.py` against it (`VLLM_URL` env override already supported by the workflow). The Azure stack keeps running.
2. **Backend auth header + health-poll cache** (§2.2, §2.3) — works against both old VM and Modal; ship it before cutover.
3. **R2 swap** (§2.1) + MinIO in dev + `rclone` data copy.
4. **Railway provisioning** — Postgres (apply schema/seed), Redis, backend, frontend; wire variables per §3; update Google OAuth redirects.
5. **Cutover + teardown** — flip DNS/links, run `infra/scripts/azure-teardown.sh` after a soak week. (Coordinate with the Achva handover plan — if the EA-subscription transfer is happening, agree which stack is being handed over before tearing anything down.)

Total estimated effort: **2–4 focused days**, dominated by the Modal app + R2 swap testing, not by refactoring.
