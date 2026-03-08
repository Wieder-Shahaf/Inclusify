# Codebase Structure

**Analysis Date:** 2026-03-08

## Directory Layout

```
inclusify/
├── frontend/               # Next.js 16 frontend app (Node.js, TypeScript, React 19)
├── backend/                # FastAPI backend (Python 3.11+)
├── db/                     # PostgreSQL schema and seed scripts
├── ml/                     # Fine-tuning notebooks and LoRA adapters
├── data/                   # Training datasets
├── shared/                 # Shared types (empty placeholder)
├── infra/                  # Deployment configs (empty placeholder)
├── scripts/                # Utility scripts (DB tests, ML setup)
├── docs/                   # Documentation
├── .planning/              # GSD planning artifacts
└── .github/                # GitHub Actions workflows
```

## Directory Purposes

**frontend/**
- Purpose: Next.js 16 web application for document upload and analysis visualization
- Contains: Pages (App Router), components (UI, landing, dashboard, glossary), i18n config, API client, utilities
- Key files: `app/[locale]/analyze/page.tsx` (main analyzer), `app/[locale]/page.tsx` (landing)

**frontend/app/**
- Purpose: Next.js App Router entry points
- Contains: Root layout, locale-specific layout, page routes
- Key: `[locale]/` segment enables `/en/*` and `/he/*` routing

**frontend/app/[locale]/**
- Purpose: Locale-specific pages (English and Hebrew variants)
- Contains: `page.tsx` (landing), `analyze/page.tsx` (main analyzer), `glossary/page.tsx`, `admin/page.tsx`

**frontend/components/**
- Purpose: Reusable React components
- Contains: UI components (AnalysisSummary, AnnotationSidePanel, FileDropzone, etc.), landing page sections, dashboard, glossary
- Pattern: Functional components with TypeScript, some use `'use client'` for interactivity

**frontend/lib/**
- Purpose: Helper utilities and API integration
- Contains: `api/client.ts` (API functions), `utils/` (demoData, mock, palette)
- Key: `api/client.ts` contains `analyzeText()`, `uploadFile()` functions used by pages

**frontend/i18n/**
- Purpose: Internationalization configuration
- Contains: `config.ts` (locale list), `request.ts` (message loading), `navigation.ts` (link routing)
- Locales: 'en' (English), 'he' (Hebrew)

**frontend/messages/**
- Purpose: Translation strings
- Contains: `en.json`, `he.json` (messages for all UI text)
- Consumed by: Components via `useTranslations('namespace')` hook

**backend/app/**
- Purpose: FastAPI application core
- Contains: Main app initialization, modules (routers), DB layer, core config
- Entry point: `main.py`

**backend/app/main.py**
- Purpose: FastAPI app setup and router registration
- Contains: CORS middleware, router includes, health check endpoint
- Routers registered: `/api/v1/ingestion` (upload), `/api/v1/analysis` (analyze)

**backend/app/modules/**
- Purpose: Feature-specific API routers
- Contains: `ingestion/` (file upload), `analysis/` (text analysis)

**backend/app/modules/ingestion/router.py**
- Purpose: Handle PDF upload and text extraction
- Endpoint: `POST /api/v1/ingestion/upload`
- Uses: PyMuPDF (fitz) for PDF processing

**backend/app/modules/analysis/router.py**
- Purpose: Handle text analysis with rule-based detection
- Endpoint: `POST /api/v1/analysis/analyze`
- Contains: TERM_RULES (keyword dictionary), `find_issues()` function, request/response models
- Status: Demo/placeholder (real LLM integration pending)

**backend/app/db/**
- Purpose: Database connection and repository layer
- Contains: `connection.py` (asyncpg pool), `deps.py` (FastAPI dependency), `repository.py` (query functions)

**backend/app/db/connection.py**
- Purpose: PostgreSQL connection setup via asyncpg
- Uses: Environment variables (PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD)

**backend/app/db/repository.py**
- Purpose: Data access layer with async query functions
- Functions: `get_org_by_slug()`, `get_user_by_email()`, `create_document()`, `create_run()`, `insert_finding()`, `insert_suggestion()`
- Pattern: Each function takes `asyncpg.Connection` and returns rows or IDs

**db/schema.sql**
- Purpose: Canonical PostgreSQL schema definition
- Contains: 11 tables (organizations, users, documents, analysis_runs, findings, suggestions, glossary_terms, rules, guideline_sources, configs)
- Used by: Manual `psql -f db/schema.sql` to initialize database

**db/seed.sql**
- Purpose: Initial test data for organizations, users, documents
- Used by: Manual `psql -f db/seed.sql` after schema creation

**ml/**
- Purpose: Model fine-tuning and inference utilities
- Contains: LoRA adapters, training notebooks, `inference_demo.py`
- Model: lightblue/suzume-llama-3-8B-multilingual (not yet integrated into backend)

**data/**
- Purpose: Training and reference datasets
- Contains: `Inclusify_Dataset.csv`, `augmented_dataset.csv`

**scripts/**
- Purpose: Operational utilities
- Contains: DB test scripts, ML environment setup scripts

## Key File Locations

**Entry Points:**
- Frontend root: `frontend/app/layout.tsx`
- Frontend locale layout: `frontend/app/[locale]/layout.tsx`
- Frontend analyzer: `frontend/app/[locale]/analyze/page.tsx`
- Backend main: `backend/app/main.py`

**Configuration:**
- Frontend TS config: `frontend/tsconfig.json` (path alias: `@/*`)
- Frontend Next config: `frontend/next.config.ts`
- Backend core config: `backend/app/core/config.py`
- i18n config: `frontend/i18n/config.ts`

**Core Logic:**
- Text analysis: `backend/app/modules/analysis/router.py`
- File upload: `backend/app/modules/ingestion/router.py`
- API client: `frontend/lib/api/client.ts`
- Repository (DB): `backend/app/db/repository.py`

**Testing/Demo:**
- Demo data: `frontend/lib/utils/demoData.ts`
- Mock utils: `frontend/lib/utils/mock.ts`

## Naming Conventions

**Files:**
- Components: PascalCase (e.g., `AnalysisSummary.tsx`, `FileDropzone.tsx`)
- Pages: lowercase or PascalCase per Next.js convention (e.g., `page.tsx`, `layout.tsx`)
- Utils: camelCase (e.g., `demoData.ts`, `mock.ts`)
- Python modules: snake_case (e.g., `router.py`, `connection.py`, `repository.py`)

**Directories:**
- Feature modules: lowercase (e.g., `ingestion/`, `analysis/`, `components/`)
- Page routes: bracket notation for dynamic segments (e.g., `[locale]/`, `[id]/`)

**Functions/Variables:**
- Frontend: camelCase for functions and variables (e.g., `handleFileSelect`, `analyzeText`)
- Backend: snake_case for Python functions (e.g., `find_issues`, `create_document`, `insert_finding`)
- Types/Models: PascalCase for classes/types (e.g., `AnalysisRequest`, `Issue`, `AnalysisResponse`)

**API Endpoints:**
- Pattern: `/api/v{version}/{module}/{action}`
- Examples: `/api/v1/ingestion/upload`, `/api/v1/analysis/analyze`

## Where to Add New Code

**New Frontend Page:**
- Create file: `frontend/app/[locale]/{pageName}/page.tsx`
- Import i18n: `useTranslations()` hook from next-intl
- Layout: Page is wrapped by locale layout automatically
- Example: Follow pattern in `frontend/app/[locale]/analyze/page.tsx`

**New Frontend Component:**
- Create file: `frontend/components/{ComponentName}.tsx`
- Pattern: Export default functional component
- Styling: Use Tailwind classes (no CSS files)
- Example: Follow pattern in `frontend/components/SeverityBadge.tsx`

**New Backend API Endpoint:**
- Create router file: `backend/app/modules/{moduleName}/router.py`
- Define models: Request and response Pydantic models
- Define endpoint: `@router.post()` or `@router.get()` decorated function
- Register in `backend/app/main.py`: `app.include_router(router, prefix="/api/v1/{moduleName}")`
- Example: Follow pattern in `backend/app/modules/analysis/router.py`

**New Database Table:**
- Add table definition: `db/schema.sql`
- Add indexes: For frequently queried columns
- Add repository functions: `backend/app/db/repository.py` with async query functions
- Update seed: `db/seed.sql` with sample data (optional)

**New Utility Function:**
- Frontend: `frontend/lib/utils/{utilName}.ts`
- Backend: `backend/app/{modulePath}/{utilName}.py`

**Shared Types:**
- Location: `shared/` (currently empty)
- Future: Shared type definitions for API contracts (would be referenced by both frontend and backend)

## Special Directories

**frontend/.next/**
- Purpose: Build output from Next.js
- Generated: Yes
- Committed: No (in .gitignore)

**backend/__pycache__/**
- Purpose: Python bytecode cache
- Generated: Yes
- Committed: No (in .gitignore)

**ml/LoRA_Adapters/**
- Purpose: Fine-tuned LoRA weights for llama model
- Generated: Yes (from fine-tuning notebooks)
- Committed: Yes (tracked in repo)

**data/**
- Purpose: Training datasets for model fine-tuning
- Generated: No (curated manually)
- Committed: Yes

**.planning/**
- Purpose: GSD (Get Stuff Done) planning documents
- Generated: Yes (created by GSD commands)
- Committed: Yes (for team reference)

---

*Structure analysis: 2026-03-08*
