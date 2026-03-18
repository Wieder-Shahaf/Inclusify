# Technology Stack

**Analysis Date:** 2026-03-09

## Languages

**Primary:**
- **TypeScript 5.x** - Frontend application (`frontend/`), Next.js pages, API client, components
- **Python 3.9+** - Backend API (`backend/app/`), ML pipeline (`ml/`), database operations

**Secondary:**
- **SQL (PostgreSQL)** - Database schema (`db/schema.sql`), seed data, queries
- **CSS** - Tailwind v4 utility classes and custom theme (`frontend/app/globals.css`)
- **JSON** - i18n messages (`frontend/messages/en.json`, `frontend/messages/he.json`)

## Runtime

**Environment:**
- **Node.js >=18.0.0** - Frontend runtime (specified in root `package.json` engines)
- **Python 3.9+** - Backend runtime (local system Python 3.9.6 detected)
- **PostgreSQL 13+** - Relational database with pgcrypto extension

**Package Managers:**
- **npm** - Frontend dependencies
  - Root workspace: `package.json` (monorepo with `frontend/`, `backend/`, `shared/` workspaces)
  - Frontend: `frontend/package.json`
  - Lockfile: Present
- **pip** - Backend Python dependencies
  - Backend: `backend/requirements.txt` (8 packages)
  - ML: `ml/requirements.txt` (49+ packages)
  - No lockfile (consider adding `requirements.lock` or using Poetry)

## Frameworks

**Core Frontend:**
- **Next.js 16.0.10** - App Router architecture with `[locale]` dynamic routing
- **React 19.2.1** - UI component library (latest major version)
- **Tailwind CSS v4** - Utility-first CSS via `@tailwindcss/postcss` plugin

**Core Backend:**
- **FastAPI 0.109.0** - Async REST API framework with Pydantic v2
- **uvicorn 0.27.0** - ASGI server for production and development

**UI Components:**
- **Framer Motion 12.23.26** - Animation library for React
- **Radix UI** - Unstyled accessible primitives
  - `@radix-ui/react-dialog 1.1.15`
- **Lucide React 0.561.0** - Icon library (Feather-derived)
- **class-variance-authority 0.7.1** - Component variant utility (shadcn pattern)
- **clsx 2.1.1** - Conditional className builder
- **tailwind-merge 3.4.0** - Intelligent Tailwind class merging
- **tw-animate-css 1.4.0** - Tailwind animation utilities

**Internationalization:**
- **next-intl 4.6.0** - i18n for Next.js App Router
  - Locales: `en`, `he` (English, Hebrew)
  - Default: `en`
  - Prefix strategy: `as-needed`
  - Config: `frontend/i18n/config.ts`, `frontend/i18n/request.ts`, `frontend/i18n/navigation.ts`
  - Messages: `frontend/messages/{locale}.json`

**Database Access:**
- **asyncpg 0.30.0** - Async PostgreSQL driver (backend)
  - Connection: `backend/app/db/connection.py`
  - Repository pattern: `backend/app/db/repository.py`
- **Prisma 7.2.0** - ORM client (frontend, configured but not primary)
  - Config: `frontend/prisma.config.ts`
  - **Note:** Canonical schema is `db/schema.sql`, not Prisma-generated

**Testing:**
- No test framework configured in `package.json` or `requirements.txt`
- No `jest.config.*`, `vitest.config.*`, or `pytest.ini` detected

**Linting/Formatting:**
- **ESLint 9** - Linting for frontend
  - Config: `frontend/eslint.config.mjs`
  - Extends: `eslint-config-next/core-web-vitals`, `eslint-config-next/typescript`

## Key Dependencies

**Critical (Frontend):**
| Package | Version | Purpose |
|---------|---------|---------|
| `next` | 16.0.10 | Full-stack React framework |
| `react` | 19.2.1 | UI library |
| `next-intl` | 4.6.0 | Hebrew/English localization |
| `framer-motion` | 12.23.26 | Animations and transitions |

**Critical (Backend):**
| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.109.0 | REST API framework |
| `uvicorn` | 0.27.0 | ASGI server |
| `asyncpg` | 0.30.0 | Async PostgreSQL driver |
| `pydantic-settings` | 2.1.0 | Configuration management |
| `python-multipart` | 0.0.6 | File upload handling |
| `pymupdf` | 1.23.8 | PDF text extraction (being replaced by Docling) |

**ML Pipeline (`ml/requirements.txt`):**
| Package | Version | Purpose |
|---------|---------|---------|
| `transformers` | >=4.30.0 | Hugging Face model loading |
| `peft` | >=0.4.0 | LoRA adapter support |
| `bitsandbytes` | >=0.41.0 | 4-bit quantization |
| `accelerate` | >=0.20.0 | Model distribution |
| `torch` | >=2.0.0 | Deep learning framework |
| `sentence-transformers` | >=2.2.0 | Embedding models |
| `hdbscan` | >=0.8.33 | Clustering algorithm |
| `scikit-learn` | >=1.3.0 | ML utilities |
| `pandas` | >=2.0.0 | Data manipulation |
| `google-generativeai` | >=0.3.0 | Gemini API (data augmentation) |

**Base Model:**
- `lightblue/suzume-llama-3-8B-multilingual` - Multilingual LLM
- LoRA adapters: `ml/LoRA_Adapters/`
- Quantization: 4-bit NF4 via bitsandbytes

## Configuration

**Environment Variables:**

**Frontend:**
- `NEXT_PUBLIC_API_URL` - Backend API URL (default: `http://localhost:8000`)
- `DATABASE_URL` - Prisma connection string (for Prisma client)

**Backend (PostgreSQL via asyncpg):**
- `PGHOST` - PostgreSQL hostname
- `PGPORT` - PostgreSQL port
- `PGDATABASE` - Database name
- `PGUSER` - PostgreSQL username
- `PGPASSWORD` - PostgreSQL password
- SSL: Required (`ssl="require"` in connection)

**ML Pipeline:**
- Environment loaded via dotenv
- Model paths: Hardcoded to `/home/azureuser/inclusify/ml/LoRA_Adapters` (Azure VM path)

**Build Configuration:**

**Frontend (`frontend/`):**
- `next.config.ts` - Next.js config with next-intl plugin
- `tsconfig.json` - TypeScript: ES2017 target, bundler module resolution
- `postcss.config.mjs` - Tailwind CSS v4 via `@tailwindcss/postcss`
- `eslint.config.mjs` - ESLint 9 flat config
- Path alias: `@/*` -> `./*`

**Backend:**
- No dedicated config file - settings loaded via environment
- Entry point: `uvicorn app.main:app --reload --port 8000`

**Database:**
- Schema: `db/schema.sql` (303 lines, PostgreSQL-native with pgcrypto)
- Seed: `db/seed.sql`
- Apply: `psql -f db/schema.sql`

## Platform Requirements

**Development:**
- **Node.js 18+** - Required by Next.js 16
- **Python 3.9+** - Backend and ML pipeline
- **PostgreSQL 13+** - With pgcrypto extension, SSL support
- **npm** - Frontend package management
- **pip/venv** - Python virtual environment

**Production (Planned):**
- **Target:** Microsoft Azure (course requirement)
- **GPU:** Azure VM with T4 GPU for vLLM inference
- **Infra:** `infra/` directory empty - Docker, CI/CD, ARM templates to be added

**GPU Requirements (ML):**
- **Fine-tuning:** CUDA-capable GPU with 16GB+ VRAM recommended
- **Inference:** T4 GPU sufficient with 4-bit quantization
- **Optional:** Flash Attention 2 for faster inference (falls back to SDPA)

## Development Commands

**Frontend:**
```bash
cd frontend && npm run dev      # Start dev server (port 3000)
cd frontend && npm run build    # Production build
cd frontend && npm run lint     # ESLint check
```

**Backend:**
```bash
cd backend && uvicorn app.main:app --reload --port 8000  # Dev server
```

**Database:**
```bash
psql -f db/schema.sql           # Apply schema
psql -f db/seed.sql             # Load seed data
```

**ML:**
```bash
cd ml && python inference_demo.py                    # Interactive demo
cd ml && python inference_demo.py --sentence "..."   # Single sentence
```

**Root Workspace:**
```bash
npm run dev              # Frontend dev (alias)
npm run backend:dev      # Backend dev
```

## Architecture Notes

**Async Pattern:**
- Backend is fully async: FastAPI + uvicorn + asyncpg
- Frontend uses Next.js Server Components + client-side fetch

**API Contract:**
- Base URL: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`)
- Endpoints:
  - `GET /` - Health check
  - `POST /api/v1/ingestion/upload` - PDF upload
  - `POST /api/v1/analysis/analyze` - Text analysis

**Frontend API Client:**
- Location: `frontend/lib/api/client.ts`
- Functions: `analyzeText()`, `uploadFile()`, `healthCheck()`
- Handles backend response transformation to frontend types

---

*Stack analysis: 2026-03-09*
