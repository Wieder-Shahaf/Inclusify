# Stack A Migration Assessment — Azure → Modal + Railway + Cloudflare R2

**Date:** June 12, 2026
**Verdict: Compatible with moderate, well-isolated changes.** The codebase is ~90% env-var-driven and fully Dockerized (except the GPU layer, which Modal doesn't need a Dockerfile for anyway). There is exactly **one hard Azure dependency in application code** (blob storage), **one missing capability** (API-key auth on the vLLM client), and **one architectural trap** that would silently defeat scale-to-zero (the 30-second model health poll). Everything else is configuration.

---

## 0. Migration status (living — update as steps land)

Branch: `feature/stack-a-modal-vllm` · last updated **2026-06-27**.

| Step | State | Notes |
|---|---|---|
| §2.4 Modal vLLM app | 🟡 **code complete, not deployed** | `infra/modal/vllm_app.py` written, pinned to the VM-validated stack (vLLM 0.17.1, Python 3.10, Qwen2.5-3B FP16, `qwen_r8_d0.2_achva_v2` LoRA served as `inclusify`). Deploy gated on a Modal account/token + the `inclusify-vllm-key` secret. |
| §2.2 vLLM bearer auth | ✅ **done (already existed)** | `_auth_headers()` in `llm_client.py` and the probe in `health.py` already send `Authorization: Bearer`. The "no auth header" claim in §2.2 below was stale at the time of writing. |
| §2.3 health-poll cache | ✅ **done** | `MODEL_SCALE_TO_ZERO` (serverless: never probes vLLM, infers from the circuit breaker, reports `state=scale_to_zero`) + `MODEL_HEALTH_CACHE_TTL` (always-on path: 5-min cached probe behind a lock). |
| §2.1 R2 / S3 swap | ✅ **code done; data copy pending** | `blob_storage.py` rewritten to boto3 (S3); `config.py` S3_* settings replace `AZURE_STORAGE_*`; `requirements.txt` boto3; dev `docker-compose` now runs MinIO + a bucket-init job. Remaining: the one-time `rclone` copy of existing objects from `inclusifystorage` → R2. |
| Railway provisioning | ⬜ not started | Postgres/Redis/backend/frontend + env wiring (§3) + Google OAuth redirects. |
| Cutover + teardown | ⬜ not started | Flip DNS/links, soak, then `azure-teardown.sh`. Coordinate with the Achva handover. |

**Validated GPU stack** (read off the live Azure VM `InclusifyModel` on 2026-06-27, then deallocated): vLLM 0.17.1 · torch 2.10.0 · transformers 4.57.6 · peft 0.18.1 · Python 3.10.12 · Tesla T4. The committed `infra/azure/vllm-vm/vllm.service` and `ml/adapters/active.json` are **stale** — they reference `qwen_r8_d0.2` (no weights in repo), but the live VM serves `qwen_r8_d0.2_achva_v2`.

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

### 2.1 `backend/app/core/blob_storage.py` — the only hard Azure SDK dependency  ✅ **CODE DONE (2026-06-27)**
> **Done:** `blob_storage.py` rewritten to **boto3** (sync, run in executor — same pattern as before); `config.py` now has `S3_ENDPOINT_URL/S3_ACCESS_KEY_ID/S3_SECRET_ACCESS_KEY/S3_BUCKET/S3_REGION` (replacing `AZURE_STORAGE_*`); `requirements.txt` swaps `azure-storage-blob`→`boto3`; dev `docker-compose` runs **MinIO** + a `minio-init` bucket job (Azurite removed). Public API (`ensure_container`/`upload_text`/`upload_file_bytes`) and the `blob://<bucket>/<key>` ref format are unchanged, so no DB refs need rewriting. **Remaining: the one-time `rclone` data copy** below.

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

### 2.2 `backend/app/modules/analysis/llm_client.py` — add bearer auth for Modal  ✅ **ALREADY DONE**
> **Correction:** this was already implemented in the codebase before the migration started. `llm_client.py` has `_auth_headers()` (returns `Authorization: Bearer <VLLM_API_KEY>` when set, else `{}`) and both POSTs pass it; the `/v1/models` probe in `health.py` does the same; `VLLM_API_KEY` is in `config.py`. The description below is the original (now-stale) plan, kept for context. No further code change needed — only set `VLLM_API_KEY` to the Modal secret value at cutover.

All three `httpx.AsyncClient` POSTs to `{VLLM_URL}/v1/chat/completions` send **no Authorization header**. That was fine inside a private VNet; a Modal web endpoint is on the public internet and must be protected (Modal proxy auth or a vLLM `--api-key`). Add:

```python
# config.py
VLLM_API_KEY: str = ""   # empty = no auth header (local dev unchanged)

# llm_client.py — in each request
headers = {"Authorization": f"Bearer {settings.VLLM_API_KEY}"} if settings.VLLM_API_KEY else {}
```

Same change applies to the model health check in `app/routers/health.py` and, if you keep using it, `ml/data_synthesis/utils/vllm_processor.py`.

### 2.3 The scale-to-zero trap: the 30-second model health poll  ✅ **DONE (2026-06-27)**
> **Done:** added `MODEL_SCALE_TO_ZERO` — when true (Modal), `/api/v1/health/model` **never probes vLLM**; it infers availability from the circuit breaker and returns `status:"available", state:"scale_to_zero"` so Modal cold-starts only on the first real request. The always-on path (Azure VM) now caches the live `/v1/models` probe for `MODEL_HEALTH_CACHE_TTL` (default 300s) behind a lock. Response contract unchanged; the frontend poll/banner are untouched. **Set `MODEL_SCALE_TO_ZERO=true` on the Railway backend at cutover.**

`frontend/app/[locale]/analyze/page.tsx` calls `modelHealthCheck()` **every 30 seconds** while anyone has the analyze page open, and that endpoint reaches through to vLLM. On Azure (always-on VM) this is harmless. On Modal it means **any open browser tab keeps the GPU container warm — or worse, repeatedly cold-starts it** — and your $0–10/mo projection becomes $100+/mo.

Fix (small, do it as part of the migration):
- Make `/api/v1/health/model` answer from a cached probe (e.g., probe vLLM at most once every 5 minutes, serve the cached state) **and never trigger a cold start** — if the container is scaled to zero, report `"available": true, "state": "scale_to_zero"` since Modal will spin it up on the first real request.
- The frontend's "model unavailable" banner logic stays unchanged.

### 2.4 Modal app for the GPU layer (new file, `infra/modal/vllm_app.py`)  🟡 **WRITTEN, NOT DEPLOYED (2026-06-27)**
> **Done:** `infra/modal/vllm_app.py` exists, pinned to the VM-validated stack (vLLM 0.17.1, Python 3.10) and copying the live serve flags 1:1; it bakes the Qwen2.5-3B FP16 base weights into the image and serves the `qwen_r8_d0.2_achva_v2` LoRA as `inclusify` (matching the backend's `VLLM_MODEL_NAME`), with vLLM `--api-key` auth to match the backend's Bearer client. The sketch below is the original draft — the committed file supersedes it (e.g. it uses `@modal.web_server` + `@modal.concurrent`, `scaledown_window`, and an image-baked download function). **Remaining: a Modal account/token + `modal secret create inclusify-vllm-key VLLM_API_KEY=…`, then `modal deploy`.**

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

**Pre-stage the weights for fast warm-up — and treat warm-up as billable, not just inference.** Bake the model weights into the **container image** (or keep them on the Modal Volume) so a cold start is a *local VRAM load* — **never** a runtime HuggingFace download. For the fastest warm-up, image-baked weights + Modal **memory-snapshots** (restore VRAM state instead of re-loading) push cold starts toward sub-second. This is a **cost** lever, not just UX: per Modal's cold-start docs the keep-warm/idle time is billed, and the boot/weight-load phase almost certainly bills too (GPU reserved during boot — verify; see §4.1). So minimise cold-start **duration** here (weights-in-image + snapshots) and **frequency** in §4.1 (`scaledown_window` + clustering).

**GPU tier — now & future** (each model is its own Modal function; size per function, change `gpu=` in one line anytime — no migration cost, so don't over-provision ahead):
- **Now — Qwen2.5-3B analysis (this app):** `gpu="T4"` (matches the Azure VM; ~6 GB weights fit; ~$0 inside the $30 credit at 50/day). Want snappier results while staying free? `gpu="L4"` ($0.80/h, 24 GB, BF16/FP8) is a ~2× speed-up still inside the credit; `A10` ($1.10/h) likewise. **A100/H100 are an overpay for a 3B at low volume** — idle keep-warm dominates the bill (§4.1), so a faster chip just pays ~3.6× to *wait*. Reserve them for sustained high throughput or much larger models.
- **Future — the audit agent's reasoning model (P3, text-only; no vision/audio):** a **small reasoning Gemma**, run **co-located with Qwen-3B in one Modal function** — the agent fires on *every* analysis, so two separate scale-to-zero functions would double the cold-start + warm-idle overhead that dominates the bill (§4.1). (Scanned-PDF/image → text already happens upstream at the Docling/OCR layer, so the model only ever needs text.) Size by the Gemma you pick: **Gemma 3 1B** (~2 GB) co-resides with Qwen-3B on a single **`T4`** (stays ~$0 in credit, but 1B reasoning is weak); **Gemma 3 4B text-only** (~8 GB — the practical floor for real reasoning) + Qwen-3B overflows the T4's 16 GB → **`gpu="L4"`** (Ada, BF16; preferred for Gemma) or **`"A10"`** (24 GB). A100 only at Gemma 12B/27B. **Cost:** §4's ~$15/mo is the *current single-pass Qwen* path; the agent's ReAct + reflection loop is several LLM calls per document, so per-analysis GPU-seconds rise sharply — expect the agentic path to **exceed the $30 credit** (~$20–50/mo on L4, driven by reasoning-loop depth more than by GPU tier; **bound the loop**). If `classify_span` keeps using the fine-tuned Qwen LoRA (the validated baseline) while Gemma drives reasoning, both models stay resident — hence the co-location.

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

## 4. Cost reality check — grounded for 50 analyses/day (~1,500/month)

*Rates as published Jun 2026 (Railway Hobby · Modal Starter · Cloudflare R2). Assumptions stated inline — change them and the totals move. Per analysis: Docling parse (CPU, on Railway) + LLM on the Qwen2.5-3B LoRA (Modal T4); active GPU inference ≈ 20–60 s/doc, cold start ≈ 30–60 s, `scaledown_window = 300 s`.*

### 4.1 Modal (GPU) — driven by warm-idle, not inference
T4 = **$0.59/GPU-h**; the vLLM container also bills CPU ($0.0473/core-h) + memory ($0.0080/GiB-h) ⇒ ≈ **$0.75–0.90/h all-in**. Weights + LoRA (~6 GB) on a Volume sit inside the **1 TiB free** ⇒ $0. Cost is dominated by the 5-min keep-warm tail after each activity burst, so it swings with how clustered the 50 requests are:
- **Clustered** (staff work in a few sessions/day): ~3–5 cold starts + 50× inference + a few 5-min tails ≈ **~25–30 GPU-h/mo**.
- **Fully spread** (each request >5 min apart, so isolated): ≈ **~160 GPU-h/mo**.

The **$30/mo Starter credit covers ~35–50 effective T4-h**, so clustered ⇒ **$0**; fully spread ⇒ ~$130 − $30 ≈ **~$100/mo**.

**Warm-up is on the meter — not just inference.** Per Modal's [cold-start docs](https://modal.com/docs/guide/cold-start): you are *"billed for any resources used while the container is idle (e.g., GPU reservation or residual memory occupancy)"* — so the keep-warm tail above is billed. The **boot / weight-load** phase isn't stated explicitly by Modal but almost certainly bills too (the GPU is reserved during boot — the same condition they bill when idle); confirm via `billing@modal.com` or by measuring billed GPU-seconds on one cold invocation. Mitigate on both axes: cold-start **frequency** (clustering + `scaledown_window`) and **duration** (weights baked into the image + memory-snapshots — see §2.4). Corollary: **never** pin the GPU warm 24/7 (`min_containers≥1`, or a health-poll that does it by accident) — that converts the entire month into billed idle.

⚠️ **The §2.3 health-poll trap overrides everything.** If the frontend's 30-s `modelHealthCheck()` keeps the container warm 24/7: 730 h × $0.59 = **~$430/mo on GPU alone** (~$600 all-in). This is the single biggest financial risk — **the §2.3 fix is mandatory**, not an optimization. Mismanaged, Modal alone costs more than the entire Azure stack you're leaving.

### 4.2 Railway (backend + frontend + Postgres + Redis) — the real recurring cost
Hobby = **$5/mo floor (incl. $5 usage)**, then billed on actual vCPU- + RAM-time (assume ≈ $10/GB-month memory, $20/vCPU-month — confirm current rates). At 50/day the load is light, so the bill ≈ the continuous RAM of four always-on services, and the **backend dominates** because `main.py` warm-loads Docling at startup (~1–1.5 GB resident): backend ~1.2 GB + frontend ~0.3 + Postgres ~0.2 + Redis ~0.05 ⇒ **~$12–20/mo** (≈ $15 typical); CPU mostly idle (bursts during parse). **Trim toward ~$5–10:** app-sleep the frontend; drop Redis (Postgres-backed refresh tokens already degrade gracefully → one fewer always-on service).

### 4.3 Cloudflare R2 (object storage) — free at this scale
Free tier: 10 GB-month, 1M Class A ops, 10M Class B ops, **egress free**. 1,500 analyses/mo ⇒ a few thousand Class A writes (vs 1M free), reads modest (vs 10M free), originals stored only when not in private mode (~1–2 MB each → a few GB before cleanup) ⇒ **$0/mo**. Even at 50 GB stored = $0.015 × 50 = **$0.75/mo**.

### 4.4 Total (50 analyses/day)

| Component | Realistic (clustered, health-poll fixed) | If mismanaged |
|---|---|---|
| **Modal T4** | **$0** (~25–30 GPU-h, inside the $30 credit) | ~$100/mo (traffic fully spread) · **~$430/mo (health-poll warm 24/7)** |
| **Railway** (4 svcs) | **~$15/mo** (backend Docling RAM dominates) | trim to ~$5–10 (sleep frontend, drop Redis) |
| **Cloudflare R2** | **$0** (inside free tier) | ~$0.75/mo at 50 GB stored |
| **Total** | **≈ $15/month** | swings to **$100–430** only if Modal is mismanaged |

**vs Azure** (B1ms Postgres + Container Apps + always-on T4 VM ≈ **$150+/mo** when the VM runs) ⇒ Stack A is **~90% cheaper at 50/day** — but essentially all the saving is the GPU going serverless, so it evaporates if the health poll keeps the container warm. **Recurring floor = Railway (~$15); Modal and R2 ride free tiers.**

---

## 5. Suggested migration order (each step independently verifiable)

1. **Modal vLLM** first — 🟡 app written (`infra/modal/vllm_app.py`); still to do: deploy it, then run `backend/tests/test_vllm_integration.py` against it (`VLLM_URL` env override already supported by the workflow). The Azure stack keeps running.
2. **Backend auth header + health-poll cache** (§2.2, §2.3) — ✅ done; §2.2 was already present, §2.3 shipped. Works against both old VM and Modal.
3. **R2 swap** (§2.1) + MinIO in dev — ✅ code done; remaining: the `rclone` data copy.
4. **Railway provisioning** — Postgres (apply schema/seed), Redis, backend, frontend; wire variables per §3; update Google OAuth redirects.
5. **Cutover + teardown** — flip DNS/links, run `infra/scripts/azure-teardown.sh` after a soak week. (Coordinate with the Achva handover plan — if the EA-subscription transfer is happening, agree which stack is being handed over before tearing anything down.)

Total estimated effort: **2–4 focused days**, dominated by the Modal app + R2 swap testing, not by refactoring.
