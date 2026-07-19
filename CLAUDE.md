# Inclusify — LGBTQ+ Inclusive Language Analyzer for Academic Texts

## Project
NLP web platform for the Achva LGBT organization. Detects LGBTQphobic,
outdated, biased, or pathologizing language in academic texts (Hebrew + English).
Provides severity-graded alerts, explanations, inclusive alternatives, and
downloadable reports.

## Tech Stack
- Frontend: Next.js 16 (App Router), TypeScript, Tailwind v4, next-intl (HE/EN), Framer Motion, shadcn-style components
- Backend: FastAPI (Python 3.11+), async, Pydantic v2, uvicorn
- Database: PostgreSQL (schema in db/schema.sql, seed in db/seed.sql), asyncpg
- ML Model: Qwen/Qwen2.5-3B-Instruct, QLoRA fine-tuned
- LoRA adapters: ml/adapters/ (live: qwen_r8_d0.2_achva_v2, served as model name `inclusify`)
- Inference: vLLM on Modal serverless GPU (T4, scale-to-zero) — infra/modal/vllm_app.py
- Document parsing: Docling
- Infrastructure: Railway (backend + frontend + Postgres) + Modal (GPU) + Cloudflare R2 (storage). Migrated off Azure — see docs/STACK-A-MIGRATION.md

## Repo Structure
- frontend/ — Next.js app with [locale] routing (en/he)
- backend/app/ — FastAPI with modules/ingestion and modules/analysis
- backend/app/db/ — asyncpg connection, deps, repository layer
- db/ — PostgreSQL schema.sql + seed.sql (canonical source of truth)
- ml/ — Fine-tuning notebooks, LoRA adapters (ml/adapters/), data pipeline
- data/ — Training datasets (Inclusify_Dataset.csv, augmented_dataset.csv)
- infra/ — docker/ (Railway Dockerfiles), modal/ (vLLM app), azure/ (legacy, retired)
- scripts/ — DB test scripts, ML venv setup

## Current State (July 2026)
- Frontend: Full flow wired to the real API. Demo data only behind a dev-only `?demo=1` flag.
- Backend: Analysis is LLM-based via vLLM on Modal (VLLMClient in modules/analysis/llm_client.py — bearer auth, circuit breaker, `MODEL_SCALE_TO_ZERO` cold-start handling). Auth is Google OAuth + JWT (fastapi-users).
- DB: Fully wired — asyncpg pool created in main.py lifespan; analysis results persist via the repository layer. NOTE: `glossary_terms`/`rules` tables are seeded but nothing reads them.
- Admin: dashboard at /admin (Overview / Users+roles / Model Performance / Feedback tabs).
- Infra: Backend + frontend deploy on Railway from `main` via infra/docker/*.Dockerfile; GitHub Actions CI runs on push. Modal app deployed separately (`modal deploy infra/modal/vllm_app.py`).
- Ops runbook: docs/OPERATIONS.md. Non-technical guide: docs/operator-handbook.html.

## Ingestion & Ops (July 2026)
- Docling runs in a **recycled spawn subprocess** (`ProcessPoolExecutor`, `max_tasks_per_child=4`) in backend/app/modules/ingestion/service.py — it OOM'd the container when run in-process (its memory ratchets and never returns to the OS). The API parent stays ~40 MB; each conversion's peak is reclaimed. Serialized to one parse at a time; torch threads + glibc arenas capped via the Dockerfile.
- Prod runs on **Railway Hobby** ($5/mo, backend replica 4 GB / 2 vCPU). Full docling incl. Hebrew/English OCR + tables is live (`BLOCK_OCR_DOCUMENTS=false`). The guard remains a code knob for hosts under ~2 GB.
- Logging is **level-split** (backend/app/main.py `dictConfig`): INFO/DEBUG → stdout, WARNING+ → stderr, because Railway tags severity by stream. `LOG_LEVEL` env overrides the INFO default.

## Key Architecture Decisions
- Detection is LLM-only (the `HybridDetector` class name is historical — no rule-based pass; glossary_terms/rules DB tables are unread)
- Private mode: no text storage when enabled (enforced by DB CHECK constraint)
- API contract: POST /api/v1/analysis/analyze → AnalysisResponse with Issue[]
- Frontend API client: frontend/lib/api/client.ts
- Canonical DB schema is db/schema.sql (no migration tooling — prod drifts, apply changes manually)

## API Endpoints (Existing)
- GET / → health check; GET /api/v1/health/model → vLLM availability/circuit-breaker state
- /auth/jwt/*, /auth/google/*, /users/* → fastapi-users auth (login, register, OAuth)
- POST /api/v1/ingestion/upload → PDF upload + text extraction
- POST /api/v1/analysis/analyze → LLM text analysis
- /api/v1/admin/* → analytics, users + role changes, model-metrics, feedback (site_admin only)
- /api/v1/users → profile; /api/v1/contact → contact form (Resend); /api/v1/feedback → user feedback

## Commands
- Frontend dev: cd frontend && npm run dev (port 3000)
- Backend dev: cd backend && uvicorn app.main:app --reload --port 8000
- DB schema apply: psql -f db/schema.sql
- DB seed: psql -f db/seed.sql
- Modal deploy: modal deploy infra/modal/vllm_app.py

## Deadlines
- April 15, 2026: Second results presentation
- July 8, 2026: Final presentation (Part B)
- August 6, 2026: All documents and fixes submitted

## Team
Shahaf Wieder, Barak Sharon, Rasha Daher, Lama Zarka, Adan Daxa

## Git Rules
- Do NOT add "Co-Authored-By" lines to commit messages
- Commits should only include the committer, not AI attribution