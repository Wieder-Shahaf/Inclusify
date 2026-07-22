# Inclusify — Operations Runbook (Railway + Modal + R2)

Day-2 operations for the production stack. Provisioning from scratch is in
**docs/STACK-A-PROVISIONING.md**; the migration rationale is in
**docs/STACK-A-MIGRATION.md**; the non-technical guide is
**docs/operator-handbook.html**.

Concrete URLs, account emails, and secrets are deliberately NOT committed —
they live in the Railway/Modal dashboards and the operator's credential sheet
(handbook §3).

> The old Azure runbook this file replaced is in git history
> (`git log -- docs/OPERATIONS.md`). The Azure stack is retired.

---

## Quick Reference

| Piece | Where | How it deploys |
|---|---|---|
| Frontend (Next.js) | Railway service | auto on push to `main` (infra/docker/frontend.Dockerfile) |
| Backend (FastAPI) | Railway service | auto on push to `main` (infra/docker/backend.Dockerfile, `runtime` target) |
| PostgreSQL | Railway Postgres | managed |
| vLLM (Qwen2.5-3B + LoRA `inclusify`) | Modal app `inclusify-vllm` | manual: `modal deploy infra/modal/vllm_app.py` |
| Object storage | Cloudflare R2 bucket | managed |
| Health checks | `GET /health` (backend), `GET /api/v1/health/model` (vLLM reachability / circuit breaker) | — |

CLI setup (one-time): `npm i -g @railway/cli && railway login && railway link`,
`pip install modal && modal token new`.

---

## 1. Check status

```bash
railway status                          # linked project + services
curl -s https://<backend>.up.railway.app/health
curl -s https://<backend>.up.railway.app/api/v1/health/model
modal app list                          # inclusify-vllm should be "deployed"
```

With `MODEL_SCALE_TO_ZERO=true` (prod), `/api/v1/health/model` never probes
vLLM — it reports `state: "scale_to_zero"` and lets the first real request
wake the GPU. A cold start takes up to ~1 minute; that is normal, not an
outage.

---

## 2. Logs

```bash
railway logs --service backend          # or --service frontend / postgres
modal app logs inclusify-vllm           # GPU-side vLLM logs
```

Railway tags severity by stream: the backend intentionally sends INFO/DEBUG to
stdout and WARNING+ to stderr (`main.py` dictConfig), so "error" entries in the
Railway UI are real. `LOG_LEVEL` env var overrides the INFO default.

---

## 3. Deploy

- **Backend/frontend:** push to `main` → Railway builds the Dockerfiles and
  deploys. Rollback / redeploy an old build: Railway dashboard → service →
  Deployments → ⋮ → Redeploy.
- **`NEXT_PUBLIC_API_URL` is a BUILD-time variable** on the frontend service
  (inlined into the bundle). Changing it requires a rebuild, not a restart.
- **Model (Modal):**
  ```bash
  modal deploy infra/modal/vllm_app.py
  ```
  First deploy rebuilds the image and re-downloads weights (slow — expected).
  The vLLM API key comes from the Modal secret `inclusify-vllm-key` and must
  equal the backend's `VLLM_API_KEY`.
- **CI:** `gh run list --workflow CI --branch main --limit 5`,
  `gh run view <RUN_ID> --log-failed`.

---

## 4. Database

```bash
railway connect postgres                # psql shell into prod DB
```

Apply schema / seed (destructive on conflicts — schema has no migration
tooling; prod drifts from db/schema.sql, apply changes as targeted SQL):

```bash
railway run --service postgres psql < db/schema.sql   # fresh DB only
railway run --service postgres psql < db/seed.sql
```

Useful queries:

```sql
-- Users and roles
SELECT email, role FROM users;

-- Promote a user to admin (also possible in the app: admin dashboard → Users)
UPDATE users SET role = 'site_admin' WHERE email = 'user@example.com';

-- Recent analyses
SELECT d.created_at, ar.status, ar.model_version, ar.runtime_ms
FROM documents d JOIN analysis_runs ar ON ar.document_id = d.document_id
ORDER BY d.created_at DESC LIMIT 10;
```

**Backups:** Railway dashboard → Postgres service → Backups. Verify these
exist and are recent — this is the only stateful piece that can't be rebuilt
from the repo.

---

## 5. Environment variables & secrets

Set in Railway dashboard → service → Variables (backend restarts on change).
Full list with prod values: docs/STACK-A-PROVISIONING.md §3. The load-bearing
ones:

| Var | Purpose |
|---|---|
| `PG*` / `DATABASE_URL` | Postgres connection (Railway injects references) |
| `JWT_SECRET` | JWT signing key |
| `GOOGLE_CLIENT_ID/SECRET` | Google OAuth |
| `VLLM_URL` | Modal endpoint `https://<workspace>--inclusify-vllm-serve.modal.run` |
| `VLLM_API_KEY` | must equal Modal secret `inclusify-vllm-key` |
| `MODEL_SCALE_TO_ZERO` | `true` in prod — never health-probe the GPU |
| `S3_*` | Cloudflare R2 (`S3_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com`) |
| `RESEND_API_KEY`, `RESEND_FROM` | email (auth mails / contact form); `RESEND_FROM` must be a Resend-verified domain |
| `BLOCK_OCR_DOCUMENTS` | `false` on Railway Hobby (4 GB); OCR guard for smaller hosts |
| `NEXT_PUBLIC_API_URL` | frontend → backend URL (**build-time**, frontend service) |

---

## 6. Troubleshooting

| Symptom | Likely cause → fix |
|---|---|
| Backend 503 "Database not available" | Postgres service down/unlinked → Railway dashboard → Postgres → restart; check `PG*` vars |
| Analyses hang / fail after ~1 min | Modal cold start is normal once; persistent → `modal app list` (deployed?), `VLLM_URL`/`VLLM_API_KEY` mismatch, `modal app logs inclusify-vllm` |
| GPU bill climbing daily | Something keeps the container warm → confirm `scaledown_window` is 5 min in infra/modal/vllm_app.py and `MODEL_SCALE_TO_ZERO=true` on the backend (a live probe would wake it) |
| Google login fails | Redirect URI mismatch → Google Cloud console → OAuth credentials → add current frontend URL |
| Uploads crash in prod only | Backend image runs `HF_HUB_OFFLINE=1` with docling models baked in — a build warm-up must be a real `.convert()` (see infra/docker/backend.Dockerfile) |
| Emails not arriving | Resend dashboard → send log; free tier only delivers to the account owner (inclusify.support@gmail.com) |
| Service stuck | Railway dashboard → service → ⋮ → Restart |

---

## Architecture quick reference

```
Browser → Frontend (Next.js, Railway)
       → Backend (FastAPI, Railway)
           → PostgreSQL (Railway)
           → vLLM  (Modal, scale-to-zero T4; bearer auth via VLLM_API_KEY)
           → R2    (uploads, S3 API)
           → Redis (refresh tokens; optional — app degrades without it)
           → Google OAuth2 / Resend
```
