# Architecture

**Analysis Date:** 2026-03-08

## Pattern Overview

**Overall:** Distributed Layered with API Contract Bridge

**Key Characteristics:**
- Frontend-backend separation via REST API (`/api/v1/*`)
- Rule-based + LLM hybrid detection pattern (currently rule-based placeholder)
- Async/await throughout backend (FastAPI, asyncpg)
- i18n layer abstracted at frontend (next-intl)
- Private mode enforcement via DB constraint (no text storage when enabled)

## Layers

**Frontend (Next.js):**
- Purpose: User interface for document upload, analysis display, results visualization
- Location: `frontend/`
- Contains: Pages, components, i18n config, API client, UI utilities
- Depends on: Backend API (`/api/v1/*`)
- Used by: End users (browser)

**Backend API (FastAPI):**
- Purpose: REST endpoints for document ingestion, text analysis, database persistence
- Location: `backend/app/`
- Contains: Main app, routers (ingestion, analysis), DB layer, core config
- Depends on: PostgreSQL, asyncpg, document parsers (PyMuPDF/Docling)
- Used by: Frontend, future ML inference service

**Database (PostgreSQL):**
- Purpose: Canonical source of truth for organizations, users, documents, findings, suggestions
- Location: `db/schema.sql` (canonical schema definition)
- Contains: 11 tables (organizations, users, documents, analysis_runs, findings, suggestions, glossary_terms, etc.)
- Depends on: None (source of truth)
- Used by: Backend repository layer via asyncpg

## Data Flow

**Text Analysis Request:**

1. **Upload Phase** (User uploads file)
   - User selects PDF file in frontend (`frontend/app/[locale]/analyze/page.tsx`)
   - File sent to `POST /api/v1/ingestion/upload`
   - Backend extracts text via PyMuPDF (`backend/app/modules/ingestion/router.py`)
   - Returns extracted text and metadata (filename, page count, text preview)

2. **Analysis Phase** (User submits for analysis)
   - Frontend calls `POST /api/v1/analysis/analyze` with text, language, private_mode flag
   - Request body: `AnalysisRequest` with text, language ('en'/'he'/'auto'), private_mode (bool)
   - Backend processes with rule-based detection (`backend/app/modules/analysis/router.py`)

3. **Rule-Based Detection**
   - Keyword matching against `TERM_RULES` dictionary (lines 78-214 in analysis router)
   - Returns list of `Issue` objects with severity (outdated/biased/offensive/incorrect)
   - Each issue includes: span, severity, type, description, suggestion, start position, end position

4. **Database Storage** (Commented out, pending activation)
   - Create document record via `repo.create_document()`
   - Create analysis_run record via `repo.create_run()`
   - Insert findings via `repo.insert_finding()` (severity mapped: offensive→high, biased/incorrect→medium, outdated→low)
   - Insert suggestions via `repo.insert_suggestion()`
   - Update run status via `repo.finish_run()`

5. **Response & Frontend Display**
   - Backend returns `AnalysisResponse` with original_text, issues_found, analysis_status
   - Frontend API client (`frontend/lib/api/client.ts`) transforms to `AnalysisResult`
   - Severity mapping: backend string → frontend severity (outdated/biased/offensive/incorrect)
   - Frontend renders annotations on text, displays issue list in side panel

**State Management:**
- No global state manager (React Context not used)
- Per-page local state: `viewState` (upload/processing/results), `analysis` (AnalysisData), `selectedAnnotation`
- Frontend calls mock demo data when no real backend available (`lib/utils/demoData.ts`)

## Key Abstractions

**AnalysisRequest/Response (API Contract):**
- Purpose: Standardized interface between frontend and backend
- Examples: `backend/app/modules/analysis/router.py` (lines 46-71)
- Pattern: Pydantic models with validation, snake_case (backend), camelCase (frontend)

**Issue Model:**
- Purpose: Represents a single problematic term detection
- Contains: span (matched text), severity, type, description, suggestion, character positions (start/end)
- Used by: Both frontend and backend for displaying/storing findings

**Repository Layer:**
- Purpose: Abstraction over asyncpg connections, encapsulates DB queries
- Location: `backend/app/db/repository.py`
- Functions: `get_org_by_slug()`, `create_document()`, `create_run()`, `insert_finding()`, `insert_suggestion()`
- Pattern: Async functions receiving `asyncpg.Connection`, returning rows or IDs

**API Client:**
- Purpose: Transform backend API responses to frontend component shape
- Location: `frontend/lib/api/client.ts`
- Functions: `analyzeText()`, `uploadFile()`, `healthCheck()`, `transformResponse()`
- Pattern: Fetch-based with error handling and type transformation

## Entry Points

**Frontend Root:**
- Location: `frontend/app/layout.tsx` (minimal passthrough) → `frontend/app/[locale]/layout.tsx` (locale setup, Navbar, Footer, NextIntlClientProvider)
- Triggers: User navigates to domain root or locale-prefixed URL
- Responsibilities: Theme initialization, locale validation, message loading

**Frontend Analyze Page:**
- Location: `frontend/app/[locale]/analyze/page.tsx`
- Triggers: User navigates to `/en/analyze` or `/he/analyze`
- Responsibilities: Manage upload/processing/results view states, handle file selection, call analysis API, render highlighted text with annotations

**Backend Main:**
- Location: `backend/app/main.py`
- Triggers: Uvicorn server startup
- Responsibilities: FastAPI app initialization, CORS middleware, router registration

**Analysis Router:**
- Location: `backend/app/modules/analysis/router.py`
- Endpoint: `POST /api/v1/analysis/analyze`
- Triggers: Frontend submits text for analysis
- Responsibilities: Validate request, run rule-based detection, prepare response

**Ingestion Router:**
- Location: `backend/app/modules/ingestion/router.py`
- Endpoint: `POST /api/v1/ingestion/upload`
- Triggers: Frontend uploads PDF
- Responsibilities: Validate file type, extract text via PyMuPDF, return text preview and metadata

## Error Handling

**Strategy:** HTTP exceptions (400/500) with descriptive error messages

**Patterns:**
- Ingestion: 400 for invalid file type, 500 for processing failure (`backend/app/modules/ingestion/router.py` lines 13-40)
- Analysis: 400 for missing organization/user, 403 for permission mismatch, 500 for DB errors (commented in router)
- Frontend API client: Throws error with status code + response text, caught by component error handling

## Cross-Cutting Concerns

**Logging:** `print()` statements (development) in ingestion router. No centralized logging framework configured.

**Validation:** Pydantic models (`AnalysisRequest`, `Issue`, `AnalysisResponse`) enforce type and field validation at API boundary.

**Authentication:** Not implemented. DB schema includes role-based fields (users.role, users.sso_provider) but not wired to API.

**Internationalization (i18n):**
- Frontend: next-intl with locale-prefixed routing (`/en/*`, `/he/*`)
- Backend: Language parameter in requests ('en', 'he', 'auto') but rules use English descriptions
- RTL/LTR: Frontend Layout sets `dir` attribute based on locale

---

*Architecture analysis: 2026-03-08*
