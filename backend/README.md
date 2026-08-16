# Inclusify Backend

FastAPI service behind the Inclusify analyzer. It ingests academic documents,
sends their text to a fine-tuned LLM for inclusive-language analysis, persists
the results, and serves the admin and account APIs.

## Stack

- **FastAPI** (Python 3.11+), fully async, **Pydantic v2** for schemas and settings
- **PostgreSQL** via **asyncpg** — a connection pool created in the `main.py` lifespan
- **Redis** — refresh-token store
- **fastapi-users** — JWT auth plus Google OAuth
- **Docling** — document parsing (PDF / DOCX / PPTX / TXT), including Hebrew and English OCR
- **vLLM on Modal** — the model runs remotely over HTTP; this service never loads it

## Layout

```
app/
├── main.py            app construction, CORS, lifespan (DB pool, Redis), logging
├── core/
│   ├── config.py      Pydantic settings — every env var lives here
│   ├── blob_storage.py  S3-compatible storage (Cloudflare R2 in prod, MinIO locally)
│   └── redis.py       refresh-token store
├── db/
│   ├── connection.py  asyncpg pool
│   ├── models.py      SQLAlchemy models used by fastapi-users
│   └── repository.py  all SQL for analysis runs, findings, documents
├── auth/              JWT + Google OAuth wiring, password reset
├── routers/health.py  GET / and the model-health endpoint
└── modules/
    ├── ingestion/     upload → Docling parse → text + bounding boxes
    ├── analysis/      the LLM pipeline (see below)
    ├── admin/         analytics, user roles, model metrics, feedback (site_admin only)
    ├── feedback/      per-finding thumbs up/down
    ├── contact/       contact form (Resend)
    └── profile/       user profile
```

## How analysis works

`POST /api/v1/analysis/analyze` is the core endpoint.

- Detection is **LLM-only**. `HybridDetector` is a historical name — there is no
  rule-based pass, and the `glossary_terms` / `rules` tables are seeded but unread.
- `VLLMClient` (`modules/analysis/llm_client.py`) talks to the Modal endpoint with
  bearer auth, a circuit breaker, and cold-start handling. Modal is
  **scale-to-zero**, so the first request after an idle period waits ~2–3 minutes
  for the model to load; `MODEL_SCALE_TO_ZERO` controls that behaviour.
- Guests may analyse without an account. The route is rate-limited to 20 calls
  per hour per caller, and `text` is capped at 200,000 characters — both exist
  because every call occupies a paid GPU.
- **Private mode** stores no text. This is enforced by a DB `CHECK` constraint,
  not only by application code.

## Ingestion, and why it uses a subprocess

Docling runs in a **recycled spawn subprocess** (`ProcessPoolExecutor`,
`max_tasks_per_child=4`) in `modules/ingestion/service.py`. In-process it OOM'd the
container: its memory ratchets upward and is never returned to the OS. Running it
in a child process that is periodically recycled keeps the API parent at ~40 MB and
reclaims each conversion's peak. Parses are serialised to one at a time.

Do not "simplify" this back to a direct in-process call.

## Running it

Easiest path is Docker Compose from the repository root, which also starts
Postgres, Redis and MinIO:

```bash
docker compose --profile dev up
```

Standalone, against services you already have running:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Then: <http://localhost:8000> for the health check, <http://localhost:8000/docs>
for the interactive API docs.

> In production, uvicorn runs with `--proxy-headers --forwarded-allow-ips=*` so
> `request.client.host` is the real caller rather than the platform's edge proxy.
> Without it, every client collapses into a handful of proxy addresses and per-IP
> rate limits end up shared between unrelated users.

## Configuration

All settings are declared in `app/core/config.py` — read that file rather than
guessing at env var names. `.env.example` at the repository root is the template.
The ones you are most likely to need locally:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` / `PG*` | Postgres connection |
| `REDIS_URL` | refresh-token store |
| `VLLM_URL`, `VLLM_API_KEY` | the model endpoint |
| `MODEL_SCALE_TO_ZERO` | `true` when the GPU is serverless, so cold starts are handled |
| `JWT_SECRET` | **must** be set to a real value outside development |
| `GOOGLE_CLIENT_ID` / `_SECRET` | Google sign-in |
| `ALLOWED_ORIGINS` | CORS; defaults to localhost |

## Tests

```bash
cd backend
python -m pytest          # 239 passed, 16 skipped at the time of writing
ruff check .
```

`tests/conftest.py` forces `DATABASE_URL` onto an ephemeral SQLite database
**before any app module is imported**. This is deliberate and load-bearing:
`app.auth.users` builds its SQLAlchemy engine from the cached settings at import
time, so a later override arrives too late, and a full-suite run would otherwise
bind to the real Postgres and let a fixture's `drop_all()` run against the live
schema. Leave that block at the top of the file.

Lint rules are pinned in `pyproject.toml` to ruff's documented default set. CI
installs ruff unpinned, and a release that widened the implicit defaults once
broke lint on untouched files with no commit to blame. Widening the set is a
deliberate change, not something to inherit from an upgrade.

## Database

`db/schema.sql` at the repository root is the canonical schema. There is **no
migration runner** — see `db/migrations/README.md` for how changes are applied.

## Logging

Logging is level-split in `main.py` (`dictConfig`): INFO and DEBUG go to stdout,
WARNING and above to stderr, because the hosting platform infers severity from
the stream. `LOG_LEVEL` overrides the INFO default.
