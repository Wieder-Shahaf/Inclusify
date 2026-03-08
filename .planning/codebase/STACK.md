# Technology Stack

**Analysis Date:** 2026-03-08

## Languages

**Primary:**
- **TypeScript 5** - Frontend application and Next.js configuration
- **Python 3.9+** - Backend API, ML pipeline, database operations
- **SQL** - PostgreSQL schema and queries

**Secondary:**
- **HTML/CSS** - Tailwind v4 for styling
- **JSON** - Configuration files, i18n messages

## Runtime

**Environment:**
- **Node.js** - Frontend runtime (Next.js 16 with npm)
- **Python 3.9+** - Backend runtime (FastAPI + asyncpg)
- **PostgreSQL 13+** - Relational database

**Package Managers:**
- **npm** - Frontend dependencies (`frontend/package.json`)
  - Lockfile: `package-lock.json` (present)
- **pip** - Backend dependencies (`backend/requirements.txt`)
  - No lockfile detected

## Frameworks

**Core Frontend:**
- **Next.js 16.0.10** - App Router, server components, API routes
- **React 19.2.1** - UI component framework
- **Tailwind CSS v4** - Utility-first styling via `@tailwindcss/postcss`

**Core Backend:**
- **FastAPI 0.109.0** - Async REST API framework
- **uvicorn 0.27.0** - ASGI server

**UI Components & Utilities:**
- **Framer Motion 12.23.26** - Animation library for React
- **Radix UI** (@radix-ui/react-dialog 1.1.15) - Unstyled accessible components
- **Lucide React 0.561.0** - Icon library
- **class-variance-authority 0.7.1** - Component variant utility
- **clsx 2.1.1** - Conditional className builder
- **tailwind-merge 3.4.0** - Tailwind CSS class merging

**Internationalization:**
- **next-intl 4.6.0** - Multi-language support for Next.js (Hebrew/English)
  - Configuration: `frontend/i18n/request.ts`, `frontend/i18n/config.ts`, `frontend/i18n/navigation.ts`
  - Messages: `frontend/messages/{locale}.json`

**ORM/Database:**
- **Prisma 7.2.0** - Frontend database client (configured but using async migration pattern)
  - Config: `frontend/prisma.config.ts`
  - Canonical schema: `db/schema.sql` (PostgreSQL-native, not Prisma-generated)
- **asyncpg 0.30.0** - Async PostgreSQL driver for backend
  - Direct async connection handling in `backend/app/db/connection.py`
  - Repository layer in `backend/app/db/repository.py`

**Testing:**
- No test framework detected (pytest, Jest, Vitest not configured)

**Build/Dev Tools:**
- **Next.js ESLint** (eslint-config-next 16.0.10)
- **ESLint 9** - Linting

**ML/NLP Stack:**
- **sentence-transformers 2.2.0** - Embedding models (`ml/embeddings/encoder.py`)
- **torch 2.0.0+** - Deep learning framework
- **scikit-learn 1.3.0** - ML utilities
- **pandas 2.0.0** - Data manipulation
- **numpy 1.24.0** - Numerical computing
- **hdbscan 0.8.33** - Clustering algorithm
- **beautifulsoup4 4.12.0** - HTML/text parsing
- **pdfplumber 0.10.0** - PDF text extraction
- **NLTK 3.8.0** - Natural language processing
- **requests 2.31.0** - HTTP client

**Document Processing:**
- **PyMuPDF (fitz) 1.23.8** - PDF text extraction (current, being replaced by Docling in R&D)
- **python-multipart 0.0.6** - File upload handling in FastAPI

**Configuration & Secrets:**
- **python-dotenv 1.0.1** - Environment variable loading
- **pydantic-settings 2.1.0** - Configuration management for FastAPI
- **pydantic 2.x** (implicit via pydantic-settings) - Data validation

**HTTP:**
- **httpx 0.26.0** - Async HTTP client (backend)

## Key Dependencies

**Critical:**
- **Next.js 16** - Entire frontend framework, routing, SSR
- **FastAPI 0.109.0** - Entire backend API, async support required
- **PostgreSQL** - Canonical source of truth for schema and data
- **asyncpg 0.30.0** - Only async Postgres driver for backend

**Infrastructure:**
- **uvicorn 0.27.0** - ASGI server for FastAPI
- **python-multipart 0.0.6** - Required for file uploads in FastAPI

**ML/Model:**
- **sentence-transformers** - Embedding generation for text analysis
- **torch** - LLM inference (lightblue/suzume-llama-3-8B-multilingual planned)

## Configuration

**Environment Variables:**

**Frontend** (`frontend/`):
- `NEXT_PUBLIC_API_URL` - Backend API base URL (defaults to `http://localhost:8000`)
- Loaded at build/runtime via Next.js env plugin

**Backend** (`backend/`):
- `PGHOST` - PostgreSQL hostname
- `PGPORT` - PostgreSQL port
- `PGDATABASE` - Database name
- `PGUSER` - PostgreSQL user
- `PGPASSWORD` - PostgreSQL password
- Loaded via `python-dotenv` in `backend/app/db/connection.py`

**ML Pipeline** (`ml/`):
- Environment configuration via `.env` file (not tracked in git)

**Build Configuration:**

**Frontend:**
- `frontend/next.config.ts` - Next.js config with `next-intl` plugin
- `frontend/tsconfig.json` - TypeScript compiler options
- `frontend/.next/` - Build output directory
- `frontend/node_modules/` - Dependencies

**Backend:**
- `backend/requirements.txt` - Python dependencies (no version locking via poetry/pip-tools)
- Started via: `uvicorn app.main:app --reload --port 8000`

**Database:**
- `db/schema.sql` - Canonical PostgreSQL schema (303 lines, not auto-generated)
- `db/seed.sql` - Seed data
- Applied via: `psql -f db/schema.sql`

## Platform Requirements

**Development:**
- Node.js 18+ (implied by Next.js 16)
- Python 3.9+ (backend/requirements.txt)
- PostgreSQL 13+ (for asyncpg SSL connection)
- CUDA/GPU (optional, for ML fine-tuning; inference planned for Azure VM with T4)

**Production:**
- **Deployment Target:** Microsoft Azure (course requirement)
- **Infra config:** Empty directory `/infra` - Docker, K8s, ARM templates to be added
- **GPU:** Azure T4 VM for vLLM inference (planned, not yet integrated)
- **Container:** No Dockerfile/docker-compose detected yet

## Async/Concurrency

**Backend:**
- Full async architecture: FastAPI + uvicorn + asyncpg
- Connection pooling via asyncpg (planned via `request.app.state.db_pool` in `backend/app/db/deps.py`)
- Async route handlers across `/api/v1/ingestion` and `/api/v1/analysis`

**Frontend:**
- Next.js SSR + client-side fetching
- Framer Motion animations are client-side only

---

*Stack analysis: 2026-03-08*
