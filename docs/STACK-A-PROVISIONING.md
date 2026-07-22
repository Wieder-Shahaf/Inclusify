# Stack A Provisioning Runbook — Modal + Railway + Cloudflare R2

Turnkey steps to stand up the new stack once you have the accounts. All **code**
changes are already done on `feature/stack-a-modal-vllm` (see
`docs/STACK-A-MIGRATION.md` §0 for status); this doc is the **deploy** procedure.

Do the steps in order — each is independently verifiable and the Azure stack
keeps running until cutover (Step 5), so you can roll back at any point.

---

## 0. Prerequisites

| Need | How |
|---|---|
| Modal account + CLI | `pip install modal` → `modal token new` |
| Railway account + CLI | `npm i -g @railway/cli` → `railway login` |
| Cloudflare account (R2 enabled) | dashboard → R2 → create bucket |
| `rclone` (one-time data copy) | `brew install rclone` |
| Azure storage key (source of the copy) | `az storage account keys list -n inclusifystorage -g Group07` |

Generate one strong shared secret up front (used as the vLLM API key):
```bash
openssl rand -hex 32   # -> VLLM_API_KEY value, used by both Modal and the backend
```

---

## 0.5 Pre-flight — validate locally before you have accounts

Every account-gated step can be rehearsed with a local stand-in, so failures are
caught now rather than mid-cutover. All of these passed on 2026-06-27.

**DB init** (rehearses the Railway `psql < schema.sql` step against a fresh DB):
```bash
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE rb_preflight;"
docker compose exec -T postgres psql -U postgres -d rb_preflight -v ON_ERROR_STOP=1 < db/schema.sql
docker compose exec -T postgres psql -U postgres -d rb_preflight -v ON_ERROR_STOP=1 < db/seed.sql
docker compose exec -T postgres psql -U postgres -c "DROP DATABASE rb_preflight;"
# -> 14 tables created + seeds inserted; ON_ERROR_STOP makes any SQL error fail loudly.
```

**Modal app** (validates the decorators/args — no Modal account or deploy needed):
```bash
pip install modal
python -c "import importlib.util,pathlib; \
 s=importlib.util.spec_from_file_location('m', pathlib.Path('infra/modal/vllm_app.py').resolve()); \
 m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print('OK', m.app.name)"
# -> 'OK inclusify-vllm'. A wrong decorator arg (e.g. scaledown_window) throws HERE,
#    long before `modal deploy`.
```

**Production Docker builds** (rehearses Railway's build — Railway builds these Dockerfiles directly):
```bash
docker build -f infra/docker/backend.Dockerfile --target runtime -t inclusify-backend:preflight .
docker build -f infra/docker/frontend.Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=https://<your-backend>.up.railway.app \
  -t inclusify-frontend:preflight .
# Confirm the Azure->S3 swap landed in the prod image (boto3 present, azure SDK gone):
docker run --rm inclusify-backend:preflight python -c "import boto3; print(boto3.__version__)"
# Confirm NEXT_PUBLIC_API_URL is inlined at BUILD time (this is why it must be a
# Railway BUILD variable, not runtime) — the URL appears inside the compiled bundle:
docker run --rm inclusify-frontend:preflight sh -c "grep -rl '<your-backend>.up.railway.app' .next/"
```

---

## 1. Modal — GPU layer (vLLM)

The app is `infra/modal/vllm_app.py` (pinned to the VM-validated stack; serves the
`qwen_r8_d0.2_achva_v2` LoRA as `inclusify`). Weights are baked into the image at
build, so the first deploy build is slow (downloads Qwen2.5-3B once) — expected.

```bash
# 1. Auth header secret (must equal the backend's VLLM_API_KEY)
modal secret create inclusify-vllm-key VLLM_API_KEY=<the openssl value>

# 2. Deploy (builds the image, bakes weights, publishes the web endpoint)
modal deploy infra/modal/vllm_app.py
# -> note the URL: https://<workspace>--inclusify-vllm-serve.modal.run

# 3. Verify against the deployed endpoint (Azure still running — safe)
cd backend && VLLM_URL=<modal-url> VLLM_API_KEY=<the openssl value> \
  python -m pytest tests/test_vllm_integration.py -v
```

Cold start ≈ 30–60s (3B FP16 from an image layer). The backend's
`VLLM_TIMEOUT=120s` + circuit breaker tolerate it. **Never** set `min_containers>=1`
and make sure `MODEL_SCALE_TO_ZERO=true` is set on the backend (Step 3) so the
health poll can't keep the GPU warm — that is the single biggest cost risk.

---

## 2. Cloudflare R2 — object storage

```bash
# 1. Create the bucket (dashboard → R2 → Create bucket): name it `texts`
# 2. Create an R2 API token (S3 credentials): R2 → Manage API Tokens → Create
#    -> gives Access Key ID + Secret + the account endpoint
#       https://<ACCOUNT_ID>.r2.cloudflarestorage.com
```

One-time data copy from Azure Blob → R2 (R2 ingress + egress are free):
```bash
# ~/.config/rclone/rclone.conf
[azureblob]
type = azureblob
account = inclusifystorage
key = <azure-storage-account-key>

[r2]
type = s3
provider = Cloudflare
access_key_id = <r2-access-key-id>
secret_access_key = <r2-secret>
endpoint = https://<ACCOUNT_ID>.r2.cloudflarestorage.com
region = auto

# Copy. Keys are content-addressed (<sha256>.txt, files/<sha256>.<ext>) and the
# backend's blob:// refs are unchanged, so this is a flat mirror — no rewrite.
rclone sync azureblob:texts r2:texts --progress
rclone check azureblob:texts r2:texts   # verify parity
```

---

## 3. Railway — backend, frontend, Postgres, Redis

Create a Railway project, then add four services. Railway auto-deploys from the
GitHub repo on push and builds the Dockerfiles directly.

```bash
railway init                       # new project
railway add --database postgres    # managed Postgres 16
railway add --database redis       # managed Redis
# Backend + frontend: add as GitHub-repo services pointing at the two Dockerfiles
#   backend  -> infra/docker/backend.Dockerfile   (target: runtime)
#   frontend -> infra/docker/frontend.Dockerfile  (final stage is `runtime`; build
#               with NO target. Do NOT set target `runner` — that stage does not
#               exist; the legacy deploy.yml's `target: runner` is broken and dies
#               at cutover.)
```

Apply the DB schema once Postgres exists:
```bash
railway run --service postgres psql < db/schema.sql
railway run --service postgres psql < db/seed.sql
```

### Backend service variables
Use Railway's variable references for Postgres (`${{Postgres.PGHOST}}` etc.).

| Variable | Value |
|---|---|
| `PGHOST` `PGPORT` `PGDATABASE` `PGUSER` `PGPASSWORD` | Railway Postgres references |
| `PGSSL` | `require` |
| `REDIS_URL` | Railway Redis reference (`${{Redis.REDIS_URL}}`) |
| `VLLM_URL` | the Modal endpoint from Step 1 |
| `VLLM_API_KEY` | the `openssl` secret (same as Modal's) |
| `MODEL_SCALE_TO_ZERO` | `true`  ← **mandatory on Modal** |
| `S3_ENDPOINT_URL` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY_ID` `S3_SECRET_ACCESS_KEY` | R2 token from Step 2 |
| `S3_BUCKET` | `texts` |
| `S3_REGION` | `auto` |
| `JWT_SECRET` | existing prod value |
| `GOOGLE_CLIENT_ID` `GOOGLE_CLIENT_SECRET` | existing values |
| `FRONTEND_URL` | the Railway frontend URL |
| `ALLOWED_ORIGINS` | the Railway frontend URL |
| `RESEND_API_KEY` `RESEND_FROM` | existing values |
| `SMTP_USER` `SMTP_PASSWORD` `SMTP_HOST` `SMTP_PORT` | existing values |

### Frontend service variables
| Variable | Value | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | the Railway **backend** public URL | **BUILD-TIME** — set as a build variable; Next.js inlines it at build, so a runtime-only value won't take effect |

---

## 4. Google OAuth redirect URIs

In Google Cloud Console → Credentials → the OAuth client, add the Railway
frontend domain to **Authorized redirect URIs** (and origins). Without this,
Google login 400s after cutover. Keep the Azure URIs until teardown.

---

## 5. Cutover + teardown

1. **Smoke test** the Railway URLs end-to-end: register/login, upload a PDF →
   Docling parse → analysis → results → report download. Confirm an object lands
   in R2 and the analyze page shows the model available (no banner).
2. **Flip** any DNS / shared links to the Railway frontend. Soak ~1 week.
3. **Tear down Azure** only after the soak: `infra/scripts/azure-teardown.sh`.
   Coordinate with the Achva handover — if the EA-subscription transfer is in
   play, agree which stack is being handed over first.

### Files that become dead after cutover (archive, don't delete until verified)
`infra/scripts/azure-*.sh`, `infra/azure/vllm-vm/*`, `.github/workflows/deploy.yml`
(ACR push). `.github/workflows/vllm-integration.yml` survives — just point its
`VLLM_URL` secret at Modal and add `VLLM_API_KEY`.

---

## Rollback

Nothing is destructive until Step 5. To roll back, point the backend's `VLLM_URL`
back at the Azure VM (start it: `az vm start -n InclusifyModel -g Group07`),
restore `AZURE_STORAGE_*` config on the old backend, and serve from the Azure
Container Apps that are still running on `main`.
