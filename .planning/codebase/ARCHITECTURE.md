# Architecture

**Analysis Date:** 2026-03-09

## Pattern Overview

**Overall:** Distributed Layered Architecture with API Contract Bridge

Inclusify follows a three-tier web architecture with clear boundaries between frontend, backend API, and database layers. A fourth ML inference layer exists as a separate Python service (not yet integrated into the main application flow).

**Key Characteristics:**
- **Frontend-Backend Separation**: Next.js frontend communicates with FastAPI backend via REST API (`/api/v1/*`)
- **Locale-Aware Routing**: All frontend routes use `[locale]` dynamic segments for HE/EN support with RTL/LTR handling
- **Hybrid Detection Strategy**: Rule-based fallback with LLM-powered analysis planned (LLM integration pending)
- **Async/Await Throughout**: FastAPI with asyncpg for non-blocking database operations
- **Privacy-First Design**: Database enforces `private_mode` via CHECK constraint - `text_storage_ref` must be NULL when private
- **Repository Pattern**: Backend uses a repository layer (`app/db/repository.py`) for all database operations

## Layers

**Presentation Layer (Frontend - Next.js 16):**
- Purpose: User interface for document upload, analysis display, results visualization
- Location: `frontend/`
- Contains: App Router pages, React components, i18n config (`next-intl`), API client, UI utilities
- Depends on: Backend API via HTTP calls
- Used by: End users (researchers, academics) via browser
- Key files:
  - `frontend/app/[locale]/layout.tsx` - Locale-aware root layout
  - `frontend/app/[locale]/analyze/page.tsx` - Main analysis workflow
  - `frontend/lib/api/client.ts` - Backend API client

**API Layer (Backend - FastAPI):**
- Purpose: REST endpoints for document ingestion and text analysis
- Location: `backend/app/`
- Contains: FastAPI main app, module routers, Pydantic models, business logic
- Depends on: Database layer, document parsers (PyMuPDF, future Docling)
- Used by: Frontend client, future ML inference service
- Key files:
  - `backend/app/main.py` - FastAPI app initialization, CORS, router registration
  - `backend/app/modules/analysis/router.py` - Text analysis endpoint
  - `backend/app/modules/ingestion/router.py` - PDF upload endpoint

**Data Access Layer:**
- Purpose: Database operations and connection management
- Location: `backend/app/db/`
- Contains: Connection pool (`connection.py`), FastAPI dependency injection (`deps.py`), repository functions (`repository.py`)
- Depends on: PostgreSQL via asyncpg
- Used by: API layer routers
- Key files:
  - `backend/app/db/repository.py` - All SQL operations as async functions
  - `backend/app/db/deps.py` - `get_db` dependency for connection injection

**Database Layer (PostgreSQL):**
- Purpose: Canonical source of truth for organizations, users, documents, findings, suggestions
- Location: `db/schema.sql` (canonical schema definition), `db/seed.sql` (test data)
- Contains: 14 tables with relationships and constraints
- Key tables: `organizations`, `users`, `documents`, `analysis_runs`, `findings`, `suggestions`, `glossary_terms`
- Privacy constraint: `text_storage_ref IS NULL` when `private_mode = TRUE`

**ML Inference Layer (Standalone):**
- Purpose: LLM-based classification of text for inclusive language compliance
- Location: `ml/`
- Contains: Fine-tuned model inference (`inference_demo.py`), data pipeline (`pipeline.py`), LoRA adapters
- Depends on: HuggingFace transformers, PEFT for LoRA, PyTorch, bitsandbytes for 4-bit quantization
- Used by: Not yet integrated - runs as standalone CLI demo
- Key files:
  - `ml/inference_demo.py` - Interactive CLI for model inference
  - `ml/LoRA_Adapters/` - Fine-tuned adapter weights

## Data Flow

**Document Upload Flow:**

1. User drops PDF in `FileDropzone` component or clicks upload
2. `PaperUpload.tsx` handles file selection, validates type/size
3. Frontend would call `uploadFile()` in `frontend/lib/api/client.ts`
4. HTTP POST to `/api/v1/ingestion/upload` with FormData
5. Backend router (`backend/app/modules/ingestion/router.py`) validates PDF content type
6. PyMuPDF (`fitz`) extracts text page by page
7. Response returns `{filename, content_type, page_count, text_preview, full_text_length}`

**Text Analysis Flow (Current - Demo Mode):**

1. User has text ready (from upload or sample)
2. Frontend calls `analyzeText()` in `frontend/lib/api/client.ts`
3. HTTP POST to `/api/v1/analysis/analyze` with `{text, language, private_mode}`
4. Backend router receives `AnalysisRequest` (Pydantic validation)
5. Rule-based `find_issues()` function scans text against `TERM_RULES` dictionary
6. Keyword matching finds all occurrences (case-insensitive), records character positions
7. Returns `AnalysisResponse` with `{original_text, analysis_status, issues_found[]}`
8. Frontend `transformResponse()` maps backend `Issue[]` to frontend `Annotation[]`
9. Severity mapping handles both direct values and legacy mappings (low→outdated, etc.)
10. UI renders highlighted text in analyze page with `IssueTooltip` components

**Text Analysis Flow (Future - With LLM + DB):**

1. Same as above through step 4
2. Hybrid detection: rule-based scan for high-precision matches first
3. LLM inference via Azure ML endpoint for contextual analysis (returns JSON with category, severity, explanation)
4. Combine results with confidence scores
5. Database transaction begins:
   - Create document record via `repo.create_document()` with SHA256 hash
   - Create analysis_run record via `repo.create_run()` with config snapshot
   - Insert findings via `repo.insert_finding()` (severity mapped: offensive→high, biased/incorrect→medium, outdated→low)
   - Insert suggestions via `repo.insert_suggestion()` for each finding
   - Update run status via `repo.finish_run()` with runtime_ms
6. Return `AnalysisResponse` with DB references

**Demo Mode Flow (Current Frontend):**
- Uses `getSampleText(locale)` from `lib/utils/demoData.ts`
- Runs `analyzeDemoText()` with local term maps (English/Hebrew)
- No backend call required - fully client-side for demonstration

**State Management:**
- **Frontend State**: React `useState` hooks in page components (no Redux/Zustand)
- **View States**: `'upload' | 'processing' | 'results'` in analyze page
- **Analysis Data**: `AnalysisData` type with text, annotations, results, counts, summary
- **No Global State**: State is per-page, passed as props to children
- **Demo Data**: `lib/utils/demoData.ts` provides sample texts and term detection

## Key Abstractions

**AnalysisRequest (Backend API Contract):**
- Purpose: Incoming request validation for text analysis
- Location: `backend/app/modules/analysis/router.py`

```python
class AnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    language: Optional[Literal['en', 'he', 'auto']] = 'auto'
    private_mode: Optional[bool] = True
    org_slug: Optional[str] = None     # For future multi-org support
    user_email: Optional[str] = None   # For future user tracking
```

**Issue (Backend):**
- Purpose: Represents a single detected language issue
- Location: `backend/app/modules/analysis/router.py`

```python
class Issue(BaseModel):
    span: str                    # The problematic text matched
    severity: Literal['outdated', 'biased', 'offensive', 'incorrect']
    type: str                    # Category name (e.g., "Outdated Terminology")
    description: str             # Explanation for the user
    suggestion: Optional[str]    # Inclusive alternative
    start: int                   # Character offset start
    end: int                     # Character offset end
```

**AnalysisResponse (Backend):**
- Purpose: Standardized response structure
- Location: `backend/app/modules/analysis/router.py`

```python
class AnalysisResponse(BaseModel):
    original_text: str
    analysis_status: str
    issues_found: list[Issue]
    corrected_text: Optional[str] = None
    note: Optional[str] = None
```

**Annotation (Frontend):**
- Purpose: Frontend representation of an issue for UI rendering
- Location: `frontend/components/AnnotatedText.tsx`

```typescript
export type Annotation = {
  start: number;
  end: number;
  severity: Severity;
  label: string;
  suggestion?: string;
  explanation?: string;
  references?: Array<{ label: string; url: string }>;
};
```

**Severity (Frontend):**
- Purpose: Categorize issue severity for UI styling and prioritization
- Location: `frontend/components/SeverityBadge.tsx`
- Values: `'outdated' | 'biased' | 'offensive' | 'incorrect'`
- Styling: sky (outdated), amber (biased), rose (offensive), red (incorrect)

**Repository Functions (Backend):**
- Purpose: Encapsulate all database operations as async functions
- Location: `backend/app/db/repository.py`
- Pattern: Each function accepts `asyncpg.Connection` as first parameter
- Functions:
  - `get_org_by_slug()`, `get_latest_org()` - Organization lookup
  - `get_user_by_email()`, `get_latest_user()` - User lookup
  - `create_document()` - Insert document with privacy handling
  - `create_run()`, `finish_run()` - Analysis run lifecycle
  - `insert_finding()` - Store detected issues
  - `insert_suggestion()` - Store replacement suggestions

**InclusifyOutput (ML):**
- Purpose: Structured output from LLM inference
- Location: `ml/inference_demo.py`

```python
@dataclass
class InclusifyOutput:
    category: str      # Rule category (e.g., 'Historical Pathologization')
    severity: str      # 'Correct', 'Outdated', 'Biased', 'Potentially Offensive', 'Factually Incorrect'
    explanation: str   # Detailed reasoning
```

## Entry Points

**Frontend Root Layout:**
- Location: `frontend/app/layout.tsx` (minimal) + `frontend/app/[locale]/layout.tsx` (main)
- Triggers: Next.js App Router on any page load
- Responsibilities: Locale validation, font loading, theme initialization, NextIntlClientProvider, Navbar/Footer

**Frontend Analyze Page:**
- Location: `frontend/app/[locale]/analyze/page.tsx`
- Triggers: Navigation to `/en/analyze` or `/he/analyze`
- Responsibilities: Full analysis workflow - manages view states (upload/processing/results), handles file selection, calls analysis (demo or API), renders highlighted text with tooltips

**Frontend Landing Page:**
- Location: `frontend/app/[locale]/page.tsx`
- Triggers: Navigation to `/` or `/en` or `/he`
- Responsibilities: Hero section, features grid, CTA, demo preview

**Backend Main:**
- Location: `backend/app/main.py`
- Triggers: `uvicorn app.main:app --reload --port 8000`
- Responsibilities: FastAPI app creation, CORS middleware (localhost:3000 allowed), router registration at `/api/v1/*`

**Analysis Router:**
- Location: `backend/app/modules/analysis/router.py`
- Endpoint: `POST /api/v1/analysis/analyze`
- Responsibilities: Validate request, run `find_issues()` detection, return `AnalysisResponse`

**Ingestion Router:**
- Location: `backend/app/modules/ingestion/router.py`
- Endpoint: `POST /api/v1/ingestion/upload`
- Responsibilities: Validate PDF content type, extract text via PyMuPDF, return preview

**ML Inference Demo:**
- Location: `ml/inference_demo.py`
- Triggers: `python inference_demo.py` or `python inference_demo.py -s "sentence"`
- Responsibilities: Load base model + LoRA adapter, run interactive classification, parse JSON output

## Error Handling

**Strategy:** Per-layer error handling with HTTP status codes and descriptive messages

**Frontend Patterns:**
- API calls use fetch with explicit error checking
- Status checked, error message extracted from response
- Location: `frontend/lib/api/client.ts`

```typescript
if (!response.ok) {
  const errorText = await response.text();
  throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
}
```

**Backend Patterns:**
- FastAPI `HTTPException` for client errors
- 400: Invalid file type, missing required data
- 403: User-organization mismatch (in DB integration code)
- 500: Database errors, processing failures
- Location: `backend/app/modules/ingestion/router.py`, `backend/app/modules/analysis/router.py`

```python
if file.content_type != "application/pdf":
    raise HTTPException(status_code=400, detail="Invalid file type. Currently only PDF is supported.")
```

**Database Patterns (Prepared):**
- Transaction wrapper ensures atomicity
- Exception caught and raised as HTTPException 500
- Location: `backend/app/modules/analysis/router.py` (commented section)

**ML Patterns:**
- JSON parsing errors returned with raw output for debugging
- Model loading failures logged with warnings
- Graceful degradation if LoRA adapter not found

## Cross-Cutting Concerns

**Logging:**
- Backend: `print()` statements in ingestion router (development)
- ML: Python `logging` module with INFO level, stdout handler
- Frontend: Browser console only
- No centralized logging framework configured

**Validation:**
- Backend: Pydantic v2 models with `Field()` constraints (min_length, Literal types)
- Frontend: TypeScript types (compile-time only)
- Database: PostgreSQL CHECK constraints (e.g., `severity IN ('low','medium','high')`, `role IN ('user','org_admin','site_admin')`)

**Authentication:**
- Current: None (open access for demo)
- Prepared in DB: `users.role`, `users.password_hash`, `users.sso_provider`
- Future: User/org association for multi-tenant support

**Internationalization (i18n):**
- Frontend: `next-intl` with `[locale]` routing (`/en/*`, `/he/*`)
- Messages: `frontend/messages/en.json`, `frontend/messages/he.json`
- RTL Support: `dir` attribute set by locale in `LocaleLayout`
- Backend: Term rules include both English and Hebrew entries in `TERM_RULES`

**Privacy Mode:**
- Database constraint: `text_storage_ref IS NULL` when `private_mode = TRUE`
- Frontend default: `private_mode: true` in API calls
- Purpose: Ensure no full text is stored for sensitive documents
- Implementation: `chk_private_storage` CHECK constraint in `db/schema.sql`

---

*Architecture analysis: 2026-03-09*
