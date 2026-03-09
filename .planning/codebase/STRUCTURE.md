# Codebase Structure

**Analysis Date:** 2026-03-09

## Directory Layout

```
inclusify/
├── frontend/               # Next.js 16 frontend app (Node.js, TypeScript, React 19)
├── backend/                # FastAPI backend (Python 3.11+)
├── db/                     # PostgreSQL schema and seed scripts (canonical source)
├── ml/                     # Model fine-tuning, LoRA adapters, inference pipeline
├── data/                   # Training datasets and processed outputs
├── shared/                 # Shared types (empty placeholder)
├── infra/                  # Deployment configs (empty placeholder)
├── scripts/                # Utility scripts (DB tests, ML venv setup)
├── docs/                   # Documentation (placeholder)
├── .planning/              # GSD planning artifacts
├── .github/                # GitHub Actions workflows
├── .claude/                # Claude Code configuration and custom commands
├── package.json            # Root monorepo workspace config
├── CLAUDE.md               # Project instructions for Claude agents
└── README.md               # Project overview
```

## Directory Purposes

### frontend/

**Purpose:** Next.js 16 web application for document upload and analysis visualization

**Contains:**
- `app/` - Next.js App Router pages and layouts
- `components/` - Reusable React components
- `lib/` - API client and utilities
- `i18n/` - Internationalization config (next-intl)
- `messages/` - Translation JSON files (en.json, he.json)
- `prisma/` - Prisma schema (not canonical - use db/schema.sql)
- `public/` - Static assets (logos, icons)

**Key files:**
- `frontend/app/[locale]/analyze/page.tsx` - Main analyzer page
- `frontend/app/[locale]/page.tsx` - Landing page
- `frontend/lib/api/client.ts` - Backend API functions
- `frontend/middleware.ts` - next-intl locale routing

### frontend/app/

**Purpose:** Next.js App Router entry points

**Structure:**
```
app/
├── layout.tsx              # Root layout (minimal)
├── globals.css             # Global CSS with Tailwind
├── favicon.ico             # Site favicon
└── [locale]/               # Locale-specific routes
    ├── layout.tsx          # Locale layout (theme, fonts, providers)
    ├── page.tsx            # Landing page
    ├── analyze/page.tsx    # Main analyzer (file upload + results)
    ├── glossary/page.tsx   # Terminology glossary
    └── admin/page.tsx      # Admin dashboard
```

**Routing:** `[locale]` segment enables `/en/*` and `/he/*` URL routing

### frontend/components/

**Purpose:** Reusable React components

**Structure:**
```
components/
├── AnalysisSummary.tsx       # Results summary display
├── AnnotatedText.tsx         # Text with inline annotations
├── AnnotationSidePanel.tsx   # Side panel for annotation details
├── FileDropzone.tsx          # Drag-and-drop file upload
├── Footer.tsx                # Site footer
├── IssueTooltip.tsx          # Tooltip for flagged issues
├── LanguageSwitcher.tsx      # EN/HE toggle
├── Navbar.tsx                # Navigation bar
├── PaperUpload.tsx           # Upload flow orchestration
├── ProcessingAnimation.tsx   # Loading animation
├── ResultCard.tsx            # Individual result card
├── SeverityBadge.tsx         # Severity level indicator
├── ThemeToggle.tsx           # Dark/light mode toggle
├── ui/                       # Base UI primitives (shadcn)
│   └── sheet.tsx             # Sheet/modal component
├── landing/                  # Landing page sections
│   ├── CTASection.tsx
│   ├── DemoPreview.tsx
│   ├── FeaturesGrid.tsx
│   ├── HeroSection.tsx
│   └── HowItWorks.tsx
├── dashboard/                # Admin dashboard components
│   ├── AdminDashboard.tsx    # Main dashboard (~36KB)
│   ├── DonutChart.tsx
│   ├── KpiCard.tsx
│   └── SimpleLineChart.tsx
└── glossary/
    └── GlossaryClient.tsx    # Glossary interactive view
```

### frontend/lib/

**Purpose:** Helper utilities and API integration

**Structure:**
```
lib/
├── utils.ts                  # cn() classname helper
├── api/
│   └── client.ts             # API functions (analyzeText, uploadFile)
└── utils/
    ├── demoData.ts           # Demo/mock analysis data
    ├── mock.ts               # Mock response generators
    └── palette.ts            # Color palette constants
```

**Key:** `lib/api/client.ts` exports `analyzeText()` and `uploadFile()` - ready to wire to backend

### frontend/i18n/

**Purpose:** Internationalization configuration

**Files:**
- `config.ts` - Locale definitions: `locales: ['en', 'he']`, `defaultLocale: 'he'`
- `navigation.ts` - Localized navigation link helper
- `request.ts` - Message loading logic

### frontend/messages/

**Purpose:** Translation strings

**Files:**
- `en.json` (~9KB) - English translations
- `he.json` (~11KB) - Hebrew translations

**Usage:** Components import via `useTranslations('namespace')` hook

### backend/

**Purpose:** FastAPI Python backend

**Structure:**
```
backend/
├── requirements.txt          # Python dependencies
├── .gitignore
└── app/
    ├── __init__.py
    ├── main.py               # FastAPI app entry point
    ├── core/
    │   ├── __init__.py
    │   └── config.py         # Settings (empty placeholder)
    ├── db/
    │   ├── __init__.py
    │   ├── connection.py     # asyncpg pool setup
    │   ├── deps.py           # FastAPI dependency injection
    │   └── repository.py     # Data access layer
    └── modules/
        ├── __init__.py
        ├── ingestion/
        │   ├── __init__.py
        │   └── router.py     # POST /api/v1/ingestion/upload
        └── analysis/
            └── router.py     # POST /api/v1/analysis/analyze
```

### backend/app/modules/

**ingestion/router.py:**
- Endpoint: `POST /api/v1/ingestion/upload`
- Purpose: Handle PDF upload and text extraction
- Uses: PyMuPDF (fitz) for PDF processing

**analysis/router.py:**
- Endpoint: `POST /api/v1/analysis/analyze`
- Contains: TERM_RULES dictionary, `find_issues()` function, Pydantic models
- Status: Rule-based placeholder (LLM integration pending)

### backend/app/db/

**Purpose:** Database connection and repository layer

**Files:**
- `connection.py` - asyncpg pool setup (reads PGHOST, PGPORT, etc.)
- `deps.py` - FastAPI dependency for DB connection
- `repository.py` - Query functions: `get_org_by_slug()`, `create_document()`, `create_run()`, `insert_finding()`, `insert_suggestion()`

### db/

**Purpose:** Canonical PostgreSQL schema definition

**Files:**
- `schema.sql` - 11 tables (organizations, users, documents, analysis_runs, findings, suggestions, glossary_terms, rules, guideline_sources, configs)
- `seed.sql` - Initial test data

**Note:** This is the canonical schema. `frontend/prisma/schema.prisma` is NOT used.

### ml/

**Purpose:** Model fine-tuning and inference utilities

**Structure:**
```
ml/
├── README.md                           # ML pipeline documentation
├── requirements.txt                    # ML Python dependencies
├── finetune_llm_with_lora.ipynb       # Fine-tuning notebook (~404KB)
├── inference_demo.py                   # Local inference demo
├── pipeline.py                         # Inference pipeline module
├── recluster.py                        # Re-clustering utility
├── visualize_results.py                # Results visualization
├── LoRA_Adapters/                      # Fine-tuned LoRA weights
│   ├── README.md
│   ├── adapter_config.json
│   ├── tokenizer.json                  # ~17MB tokenizer
│   ├── tokenizer_config.json
│   ├── chat_template.jinja
│   └── special_tokens_map.json
├── preprocessing/
│   └── sentence_splitter.py            # Text preprocessing
├── data_collection/
│   ├── pdf_scraper.py                  # PDF scraping
│   └── text_extractor.py               # Text extraction
├── embeddings/
│   └── encoder.py                      # Sentence embeddings
├── clustering/
│   └── clusterer.py                    # HDBSCAN clustering
└── outputs/                            # Inference run outputs
    ├── run_20260114_191541/            # Run artifacts
    ├── run_20260116_085543/            # Comparison run
    └── visualizations/                 # Generated charts
```

**Model:** lightblue/suzume-llama-3-8B-multilingual with QLoRA fine-tuning

### data/

**Purpose:** Training and reference datasets

**Structure:**
```
data/
├── Inclusify_Dataset.csv      # Base training dataset (~17KB)
├── augmented_dataset.csv      # Augmented dataset (~214KB)
├── raw_pdfs/                  # Source PDF documents (~77 files)
└── output/
    ├── sentences_raw.csv      # Extracted sentences (~4.8MB)
    └── sentences_clustered.csv # Clustered sentences (~4.9MB)
```

### scripts/

**Purpose:** Operational utilities

**Files:**
- `db_test.py` - Simple DB connection test
- `db_insert_test.py` - DB insert test script
- `setup_ml_venv.sh` - ML virtual environment setup

### .planning/

**Purpose:** GSD planning documents

**Structure:**
```
.planning/
├── PROJECT.md                 # Project scope and goals
├── REQUIREMENTS.md            # Feature requirements
├── ROADMAP.md                 # Phase timeline
├── STATE.md                   # Current project state
├── config.json                # GSD configuration
├── codebase/                  # Codebase analysis documents
│   ├── ARCHITECTURE.md
│   ├── CONCERNS.md
│   ├── CONVENTIONS.md
│   ├── INTEGRATIONS.md
│   ├── STACK.md
│   ├── STRUCTURE.md
│   └── TESTING.md
├── phases/                    # Phase implementation plans
│   └── 01-infrastructure-foundation/
└── research/                  # Research documents
```

### .github/

**Purpose:** GitHub configuration

**Files:**
- `workflows/ci.yml` - CI pipeline
- `workflows/pull_request_template.md` - PR template

### .claude/

**Purpose:** Claude Code configuration

**Structure:**
```
.claude/
├── settings.local.json       # Local Claude settings
├── commands/                 # Custom Claude commands
│   ├── appinsights-instrumentation.md
│   ├── generate-tests.md
│   └── webapp-testing.md
└── agents/                   # Claude agent configs
```

## Key File Locations

**Entry Points:**
- Frontend root: `frontend/app/layout.tsx`
- Frontend locale layout: `frontend/app/[locale]/layout.tsx`
- Frontend analyzer: `frontend/app/[locale]/analyze/page.tsx`
- Backend main: `backend/app/main.py`

**Configuration:**
- Root package.json: `package.json` (workspace config)
- Frontend package.json: `frontend/package.json`
- Backend requirements: `backend/requirements.txt`
- ML requirements: `ml/requirements.txt`
- Frontend TS config: `frontend/tsconfig.json` (path alias: `@/*`)
- Frontend Next config: `frontend/next.config.ts`
- shadcn config: `frontend/components.json`
- i18n config: `frontend/i18n/config.ts`
- Backend core config: `backend/app/core/config.py` (empty)

**Core Logic:**
- Text analysis: `backend/app/modules/analysis/router.py`
- File upload: `backend/app/modules/ingestion/router.py`
- API client: `frontend/lib/api/client.ts`
- Repository (DB): `backend/app/db/repository.py`
- ML inference: `ml/inference_demo.py`
- ML pipeline: `ml/pipeline.py`

**Testing/Demo:**
- Demo data: `frontend/lib/utils/demoData.ts`
- Mock utils: `frontend/lib/utils/mock.ts`
- DB tests: `scripts/db_test.py`, `scripts/db_insert_test.py`

## Naming Conventions

**Files:**
- Components: PascalCase (e.g., `AnalysisSummary.tsx`, `FileDropzone.tsx`)
- Pages: lowercase per Next.js convention (`page.tsx`, `layout.tsx`)
- Utils: camelCase (e.g., `demoData.ts`, `mock.ts`)
- Python modules: snake_case (e.g., `router.py`, `connection.py`, `repository.py`)

**Directories:**
- Feature modules: lowercase (e.g., `ingestion/`, `analysis/`, `components/`)
- Page routes: bracket notation for dynamic segments (`[locale]/`)

**Functions/Variables:**
- Frontend: camelCase (e.g., `handleFileSelect`, `analyzeText`)
- Backend: snake_case (e.g., `find_issues`, `create_document`, `insert_finding`)
- Types/Models: PascalCase (e.g., `AnalysisRequest`, `Issue`, `AnalysisResponse`)

**API Endpoints:**
- Pattern: `/api/v{version}/{module}/{action}`
- Examples: `/api/v1/ingestion/upload`, `/api/v1/analysis/analyze`

## Where to Add New Code

**New Frontend Page:**
1. Create file: `frontend/app/[locale]/{pageName}/page.tsx`
2. Import i18n: `useTranslations()` hook from next-intl
3. Add translations: `frontend/messages/en.json`, `frontend/messages/he.json`
4. Layout is auto-wrapped by locale layout
5. Reference: `frontend/app/[locale]/analyze/page.tsx`

**New Frontend Component:**
1. Create file: `frontend/components/{ComponentName}.tsx`
2. Use `'use client'` directive if interactive
3. Style with Tailwind classes
4. Export default functional component
5. Reference: `frontend/components/SeverityBadge.tsx`

**New UI Primitive (shadcn-style):**
1. Create file: `frontend/components/ui/{component}.tsx`
2. Follow shadcn patterns with CVA for variants
3. Reference: `frontend/components/ui/sheet.tsx`

**New Backend API Endpoint:**
1. Create module: `backend/app/modules/{moduleName}/`
2. Create router: `backend/app/modules/{moduleName}/router.py`
3. Define Pydantic models for request/response
4. Register in `backend/app/main.py`: `app.include_router(router, prefix="/api/v1/{moduleName}")`
5. Reference: `backend/app/modules/analysis/router.py`

**New Database Table:**
1. Add table definition: `db/schema.sql`
2. Add indexes for frequently queried columns
3. Add repository functions: `backend/app/db/repository.py`
4. Add seed data (optional): `db/seed.sql`

**New Utility Function:**
- Frontend: `frontend/lib/utils/{utilName}.ts`
- Backend: `backend/app/{modulePath}/{utilName}.py`
- ML: `ml/{category}/{utilName}.py`

**New ML Component:**
- Preprocessing: `ml/preprocessing/{module}.py`
- Data collection: `ml/data_collection/{module}.py`
- Inference: Update `ml/pipeline.py` or `ml/inference_demo.py`

**Shared Types (future):**
- Location: `shared/`
- Purpose: Shared type definitions for API contracts

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
- Committed: Yes (tracked in repo, ~17MB tokenizer)

**ml/outputs/**
- Purpose: Inference run outputs and comparisons
- Generated: Yes
- Committed: Yes (for reproducibility)

**data/**
- Purpose: Training datasets and processed outputs
- Generated: Partially (outputs are generated, raw data is curated)
- Committed: Yes

**data/raw_pdfs/**
- Purpose: Source PDF documents for training data
- Contains: ~77 PDF files
- Committed: Yes

**.planning/**
- Purpose: GSD planning documents and phase artifacts
- Generated: Yes (created by GSD commands)
- Committed: Yes (for team reference)

**.claude/**
- Purpose: Claude Code configuration and custom commands
- Generated: Manually configured
- Committed: Yes

---

*Structure analysis: 2026-03-09*
