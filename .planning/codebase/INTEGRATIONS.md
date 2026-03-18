# External Integrations

**Analysis Date:** 2026-03-09

## APIs & External Services

**LLM Inference (Planned - Azure ML):**
- **Model:** lightblue/suzume-llama-3-8B-multilingual with QLoRA fine-tuning
  - Status: Validated locally via `ml/inference_demo.py`
  - Deployment Target: Azure ML Online Endpoint (not yet integrated)
  - Backend Integration Point: `backend/app/modules/analysis/router.py` (TODO in comments, lines 19-23)
  - LoRA Adapters: `ml/LoRA_Adapters/` (ready, fine-tuning complete)
  - Default adapter path: `/home/azureuser/inclusify/ml/LoRA_Adapters` (Azure VM)

**Gemini API (Data Augmentation):**
- **Package:** `google-generativeai>=0.3.0` in `ml/requirements.txt`
  - Purpose: Used for training data augmentation (commented out in notebook)
  - Not used in production inference
  - Reference: `ml/finetune_llm_with_lora.ipynb` (lines 1100-1126)

**PDF Processing:**
- **Current:** PyMuPDF (fitz 1.23.8)
  - Location: `backend/app/modules/ingestion/router.py`
  - Usage: `fitz.open(stream=file_content, filetype="pdf")`
- **Planned:** Docling (R&D validated, replacing PyMuPDF)
  - Status: Transition pending

**Text Embeddings:**
- **Package:** sentence-transformers 2.2.0
  - Purpose: Text embedding for clustering analysis
  - Location: `ml/embeddings/` directory

**Hugging Face Hub:**
- **Package:** huggingface-hub>=0.16.0
  - Purpose: Model downloads (base LLM, tokenizers)
  - Auth: Uses default HF cache, no API key in app code

## Data Storage

**PostgreSQL (Primary Database):**
- **Version:** 13+ (required for pgcrypto extension)
- **Driver:** asyncpg 0.30.0 (async)
- **Connection:** `backend/app/db/connection.py`
  - SSL Mode: `ssl="require"` (hardcoded)
  - Env loading: python-dotenv

**Connection Configuration:**
```python
# Required environment variables
PGHOST     # PostgreSQL hostname
PGPORT     # PostgreSQL port (cast to int)
PGDATABASE # Database name
PGUSER     # Database username
PGPASSWORD # Database password
```

**Schema Location:** `db/schema.sql` (303 lines, canonical source)

**Key Tables:**
| Table | Purpose |
|-------|---------|
| `organizations` | Multi-tenant support, org settings |
| `users` | Auth, roles (user/org_admin/site_admin), locale |
| `documents` | Input tracking, private mode enforcement |
| `analysis_runs` | Job status, model version, runtime metrics |
| `findings` | Detection results with severity, text spans |
| `suggestions` | Replacement text per finding |
| `rules` | Rule database for hybrid detection |
| `glossary_terms` | Bilingual terminology definitions |
| `guideline_sources` | Reference sources for rules |
| `feedback` | User feedback on findings |
| `usage_events` | Analytics events |
| `audit_log` | Security audit trail |
| `report_exports` | Generated report storage |
| `configs` | Per-org configuration snapshots |

**Connection Pool Pattern:**
- Planned: `request.app.state.db_pool` via FastAPI lifespan
- Dependency: `backend/app/db/deps.py` (get_db function)
- Status: Written but not connected in main.py

**Repository Layer:**
- Location: `backend/app/db/repository.py`
- Pattern: Direct asyncpg queries (no ORM)
- Functions: `create_document`, `create_run`, `insert_finding`, `insert_suggestion`, etc.

**File Storage:**
- Local filesystem only (no cloud storage)
- PDF uploads: In-memory processing via `python-multipart`

**Caching:**
- None implemented

## Authentication & Identity

**Auth Provider:** Custom (planned, not implemented)

**Schema Support:**
- Password auth: `users.password_hash` field
- SSO ready: `users.sso_provider` field (NULL = local auth)
- Roles: `user`, `org_admin`, `site_admin` (CHECK constraint)
- Consent tracking: `users.consent_store_text` BOOLEAN

**Current Status:**
- No auth middleware in backend
- No auth routes in `backend/app/main.py`
- Org/user resolution in analysis router is commented out (DB integration pending)

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, DataDog, etc.)

**Logging:**
- Standard Python logging (not configured)
- Backend: uvicorn default logging
- No structured logging format

**Metrics:**
- Analysis runtime: `analysis_runs.runtime_ms` (stored in DB)
- No external APM or metrics service

**Health Check:**
- Backend: `GET /` returns `{"message": "Inclusify API is running", "status": "OK"}`
- Frontend: `healthCheck()` function in `frontend/lib/api/client.ts`

## CI/CD & Deployment

**Hosting Target:** Microsoft Azure (course requirement)

**Infrastructure Config:**
- Location: `/infra/` (currently empty - .gitkeep only)
- No Dockerfile detected
- No docker-compose detected
- No ARM/Bicep templates

**CI Pipeline:** GitHub Actions
- Config: `.github/workflows/ci.yml`
- Triggers: Pull requests, pushes to main branch
- Jobs:
  1. Repo structure validation (frontend, backend, ml, shared, infra, docs directories exist)
  2. `.env` file not committed check

**Local Development:**
| Service | URL | Command |
|---------|-----|---------|
| Frontend | http://localhost:3000 | `cd frontend && npm run dev` |
| Backend | http://localhost:8000 | `cd backend && uvicorn app.main:app --reload --port 8000` |

**CORS Configuration:**
- Location: `backend/app/main.py`
- Allowed origins:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- Methods: `*` (all)
- Credentials: Enabled

## Environment Configuration

**Frontend Environment Variables:**
| Variable | Purpose | Default |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API endpoint | `http://localhost:8000` |

**Backend Environment Variables:**
| Variable | Purpose | Required |
|----------|---------|----------|
| `PGHOST` | PostgreSQL hostname | Yes |
| `PGPORT` | PostgreSQL port | Yes |
| `PGDATABASE` | Database name | Yes |
| `PGUSER` | PostgreSQL username | Yes |
| `PGPASSWORD` | PostgreSQL password | Yes |

**ML Environment Variables (from README):**
| Variable | Purpose |
|----------|---------|
| `AZURE_ENDPOINT` | Azure ML endpoint URL |
| `AZURE_API_KEY` | Azure ML API key |

**Secrets Location:**
- `.env` file (not tracked in git)
- Loaded via `python-dotenv` in backend
- Next.js env loading via `@next/env` plugin

**Test Scripts:**
- `scripts/db_test.py` - Test PostgreSQL connection
- `scripts/db_insert_test.py` - Test DB insert operations

## Webhooks & Callbacks

**Incoming:** None

**Outgoing:** None

**Note:** Analysis system is synchronous request-response only. No async job queue or webhook notifications implemented.

## Multi-Language / Internationalization

**Frontend i18n:**
- **Library:** next-intl 4.6.0
- **Locales:** `en` (English), `he` (Hebrew)
- **Default:** `en`
- **Prefix:** `as-needed` (no prefix for default locale)

**Configuration Files:**
| File | Purpose |
|------|---------|
| `frontend/i18n/config.ts` | Locale definitions, default locale |
| `frontend/i18n/request.ts` | Server-side locale resolution |
| `frontend/i18n/navigation.ts` | Locale-aware Link, usePathname, etc. |
| `frontend/middleware.ts` | Locale detection middleware |
| `frontend/messages/en.json` | English translations (233 lines) |
| `frontend/messages/he.json` | Hebrew translations (233 lines) |

**Backend Language Support:**
- `documents.language` field: `he`, `en`, or `auto`
- `users.locale` preference: defaults to `he`
- `rules.language` field: bilingual rule support
- `glossary_terms.language` field: bilingual glossary

**RTL Support:**
- Hebrew (he) requires RTL layout
- Handled by frontend components (not explicitly configured)

## Database Privacy Features

**Private Mode Constraint:**
```sql
ALTER TABLE documents
ADD CONSTRAINT chk_private_storage
CHECK (
  (private_mode = TRUE AND text_storage_ref IS NULL)
  OR
  (private_mode = FALSE)
);
```
- When `private_mode = TRUE`: No text storage allowed
- Default: `private_mode = TRUE`

**Data Retention:**
- Soft deletes: `documents.deleted_at` TIMESTAMP
- Expiration: `documents.expires_at` TIMESTAMP

**Audit Trail:**
- `audit_log` table: action, actor, target, IP hash, timestamp

**Text Handling:**
- SHA256 hash: `documents.text_sha256` (for deduplication/verification)
- External storage ref: `documents.text_storage_ref` (future cloud storage)

## Integration Status Summary

| Integration | Status | Priority |
|-------------|--------|----------|
| PostgreSQL | Schema ready, connection code written, NOT connected | P0 |
| LLM Inference (Azure ML) | POC validated, endpoint not deployed | P1 |
| PDF Processing (Docling) | R&D validated, migration pending | P2 |
| Authentication | Schema ready, no implementation | P2 |
| CI/CD (Azure deploy) | Not started | P1 |
| Docker containerization | Not started | P1 |
| Error tracking (Sentry) | Not started | P3 |
| Cloud file storage | Not started | P3 |

---

*Integration audit: 2026-03-09*
