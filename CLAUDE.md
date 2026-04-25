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
- LoRA adapters: ml/LoRA_Adapters/
- Inference: vLLM on Azure VM with T4 GPU (not yet integrated)
- Document parsing: Docling (replacing PyMuPDF, validated in R&D)
- Infrastructure: Microsoft Azure (course requirement)

## Repo Structure
- frontend/ — Next.js app with [locale] routing (en/he)
- backend/app/ — FastAPI with modules/ingestion and modules/analysis
- backend/app/db/ — asyncpg connection, deps, repository layer
- db/ — PostgreSQL schema.sql + seed.sql (canonical source of truth)
- ml/ — Fine-tuning notebooks, inference demo, LoRA adapters, pipeline
- data/ — Training datasets (Inclusify_Dataset.csv, augmented_dataset.csv)
- shared/ — Shared types (empty, to be populated)
- infra/ — Deployment configs (empty, to be populated)
- scripts/ — DB test scripts, ML venv setup

## Current State (March 2026)
- Frontend: Full UI flow (upload → processing → results) works with DEMO data
- Backend: Rule-based placeholder in analysis router. DB integration is written but commented out.
- ML: Fine-tuned model validated (POC complete). Adapters ready. inference_demo.py works locally.
- DB: Full schema + seed implemented. Repository layer written. NOT connected to running app.
- Infra: Empty. No Docker, no CI/CD, no Azure deployment configs.
- Data Pipeline: Docling validated as replacement for PyMuPDF. Not yet integrated into ingestion.

## Key Architecture Decisions
- Hybrid detection: rule-based (high-precision known terms) + LLM (contextual analysis)
- Private mode: no text storage when enabled (enforced by DB CHECK constraint)
- API contract: POST /api/v1/analysis/analyze → AnalysisResponse with Issue[]
- Frontend API client already built in frontend/lib/api/client.ts, ready to wire
- Canonical DB schema is db/schema.sql (not frontend/prisma/schema.prisma)

## API Endpoints (Existing)
- GET / → health check
- POST /api/v1/ingestion/upload → PDF upload + text extraction
- POST /api/v1/analysis/analyze → text analysis (currently rule-based demo)

## Commands
- Frontend dev: cd frontend && npm run dev (port 3000)
- Backend dev: cd backend && uvicorn app.main:app --reload --port 8000
- DB schema apply: psql -f db/schema.sql
- DB seed: psql -f db/seed.sql
- ML inference demo: cd ml && python inference_demo.py

## Deadlines
- April 15, 2026: Second results presentation
- July 8, 2026: Final presentation (Part B)
- August 6, 2026: All documents and fixes submitted

## Team
Shahaf Wieder, Barak Sharon, Rasha Daher, Lama Zarka, Adan Daxa

## Git Rules
- Do NOT add "Co-Authored-By" lines to commit messages
- Commits should only include the committer, not AI attribution