# External Integrations

**Analysis Date:** 2026-03-08

## APIs & External Services

**LLM Inference (Planned):**
- **lightblue/suzume-llama-3-8B-multilingual** - Fine-tuned LLM model
  - Status: Validated locally via `ml/inference_demo.py`
  - Deployment: Azure ML Online Endpoint (not yet integrated)
  - Integration: `backend/app/modules/analysis/router.py` (TODO in comments)
  - LoRA Adapters: `ml/LoRA_Adapters/` (ready, fine-tuning complete)

**PDF Processing (In Flight):**
- **Docling** - Document parsing library (R&D validated, replacing PyMuPDF)
  - Current: PyMuPDF (fitz 1.23.8) in `backend/app/modules/ingestion/router.py`
  - Status: Transition pending

**Text Embeddings:**
- **Sentence Transformers** - Embedding model for text analysis
  - SDK: `sentence-transformers 2.2.0`
  - Location: `ml/embeddings/encoder.py`

## Data Storage

**Databases:**

**PostgreSQL 13+:**
- Connection: Environment variables (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD)
- Client: `asyncpg 0.30.0` (async driver)
- Schema: `db/schema.sql` (canonical source, 303 lines)
- ORM/Abstraction: Direct asyncpg queries via repository layer (`backend/app/db/repository.py`)
- Connection pooling: Planned via `request.app.state.db_pool` (deps in `backend/app/db/deps.py`)

**Schema Highlights:**
- **Organizations** (`organizations`) - Multi-tenant support
- **Users** (`users`) - Auth, roles (user/org_admin/site_admin), locale preference
- **Documents** (`documents`) - Input tracking (paste/upload), language detection, private mode enforcement
- **Analysis Runs** (`analysis_runs`) - Job tracking, model version, runtime metrics
- **Issues** (`issues`) - Detection results with severity, affected spans
- **Guideline Sources** (`guideline_sources`) - Rule database for hybrid detection
- **Settings** - JSONB columns for extensibility

**File Storage:**
- Local filesystem only (no cloud storage detected)
- PDF/document uploads: In-memory processing via `python-multipart` in FastAPI

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- Custom (built-in planning)
- Schema prepared in `db/schema.sql`:
  - Password hashing: `users.password_hash` field
  - SSO support: `users.sso_provider` field (NULL for local auth)
  - Roles: user, org_admin, site_admin (CHECK constraint)

**Current Status:**
- No auth middleware implemented in backend
- Auth routes not present in `backend/app/main.py`

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Standard Python logging (not configured)
- Backend startup logs: `app.main:app` via uvicorn

**Metrics & Tracing:**
- Analysis runtime tracked: `analysis_runs.runtime_ms`
- No external APM detected

## CI/CD & Deployment

**Hosting:**
- **Microsoft Azure** (course requirement)
- **Infra config location:** `/infra` (currently empty - Docker/ARM templates pending)

**CI Pipeline:**
- **GitHub Actions** - `.github/workflows/ci.yml`
  - Basic sanity checks:
    - Repo structure validation (frontend, backend, ml, shared, infra, docs directories)
    - `.env` file not committed check
  - Triggers: Pull requests and pushes to main

**Local Dev Servers:**
- Frontend: `http://localhost:3000` (Next.js dev server)
- Backend: `http://localhost:8000` (FastAPI + uvicorn)

**CORS Configuration:**
- Backend allows:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- Configured in `backend/app/main.py` via CORSMiddleware

## Environment Configuration

**Required Environment Variables:**

**Frontend:**
- `NEXT_PUBLIC_API_URL` - Backend API endpoint (default: `http://localhost:8000`)

**Backend:**
- `PGHOST` - PostgreSQL hostname
- `PGPORT` - PostgreSQL port
- `PGDATABASE` - Database name
- `PGUSER` - PostgreSQL username
- `PGPASSWORD` - PostgreSQL password
- `SSL_MODE` - Implied as "require" in `backend/app/db/connection.py`

**Secrets Location:**
- `.env` file (not tracked in git per `.gitignore`)
- Python-dotenv loading in `backend/app/db/connection.py`
- Frontend env vars: Next.js plugin in `frontend/next.config.ts`

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

**Note:** Analysis system is request-response only, no async job notifications yet.

## Multi-Language / Localization

**Implementation:**
- **next-intl 4.6.0** for frontend i18n
- Supported languages: Hebrew (he), English (en)
- Auto-detection fallback: locale detection via request
- Message files: `frontend/messages/{locale}.json`
- Configuration: `frontend/i18n/`

**Backend:**
- Language field in `documents` table: `language TEXT ('he'|'en'|'auto')`
- User preference stored: `users.locale` (defaults to 'he')

## Database Constraints & Features

**Privacy Mode:**
- Enforced by CHECK constraint: `documents.private_mode` BOOLEAN
- When enabled: No text storage (planned architecture)
- Default: TRUE

**Data Retention:**
- Soft deletes: `documents.deleted_at` TIMESTAMP
- Expiration: `documents.expires_at` TIMESTAMP

**Text Storage:**
- Reference-based: `documents.text_storage_ref`, `documents.text_sha256`
- Supports external text storage (not yet integrated)

---

*Integration audit: 2026-03-08*
