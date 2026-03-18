# Codebase Concerns

**Analysis Date:** 2026-03-08

## Tech Debt

**Database Integration Disabled:**
- Issue: Core database layer is fully implemented and commented out; backend runs in demo/placeholder mode
- Files: `backend/app/modules/analysis/router.py` (lines 34-36, 292-394)
- Impact: No persistence of analyses, user data, or audit logs. Cannot satisfy multi-org/multi-user requirements (org_slug, user_email parameters exist but unused). Production deployment impossible without uncommenting DB code.
- Fix approach: Uncomment DB imports and transaction logic in `router.py`. Set up PostgreSQL instance. Test org/user resolution and transaction handling. Consider implementing database connection pooling.

**Rule-Based Detection as Production Placeholder:**
- Issue: Analysis endpoint uses hardcoded keyword matching (127 English/Hebrew rules in memory dictionary) instead of LLM model
- Files: `backend/app/modules/analysis/router.py` (lines 78-214, 221-256)
- Impact: Detection lacks contextual understanding, linguistic nuance, and language-specific morphology. Cannot detect novel or context-dependent bias. No confidence scores provided. High false-positive rate expected in production.
- Fix approach: Integrate Azure ML endpoint for vLLM inference using fine-tuned model. Create inference client in `backend/app/modules/inference.py`. Load system prompt and handle streaming responses. Add confidence score extraction.

**LLM Model Not Integrated:**
- Issue: Fine-tuned lightblue/suzume-llama-3-8B-multilingual model trained and validated locally, but not connected to API
- Files: `ml/inference_demo.py` (works locally), `ml/LoRA_Adapters/` (weights ready), backend analysis router
- Impact: Cannot leverage ML capabilities for production. Azure GPU VM deployment not configured. Inference service disconnected from API flow.
- Fix approach: Create Azure ML Online Endpoint. Deploy vLLM container with LoRA adapter weights. Implement `InferenceClient` class with retry logic. Add model version tracking to analysis_runs table.

**Document Parsing Uses Deprecated PyMuPDF:**
- Issue: `backend/app/modules/ingestion/router.py` uses PyMuPDF (fitz) for PDF extraction. Docling library has been validated as superior replacement but not integrated
- Files: `backend/app/modules/ingestion/router.py` (line 2-27)
- Impact: PDF extraction quality suboptimal. Docling provides better layout preservation, table extraction, and multi-modal content handling. Code duplication maintenance risk.
- Fix approach: Replace PyMuPDF with Docling. Update `/api/v1/ingestion/upload` to use Docling's document parser. Test with real academic PDFs. Update dependencies in `requirements.txt`.

**Data Pipeline Offline:**
- Issue: ML data collection pipeline (scraping, sentence splitting, clustering) not integrated into backend; runs only as standalone script
- Files: `ml/pipeline.py` (lines 160-174), `ml/data_collection/`, `ml/preprocessing/`, `ml/clustering/`
- Impact: Cannot update training data or perform weak labeling at runtime. Manual multi-step process required for model retraining. No way to collect user corrections as feedback.
- Fix approach: Expose pipeline as backend service endpoints or async job queue. Create `/api/v1/admin/data-collection` endpoint. Implement feedback loop from user corrections to training pipeline.

**No Test Coverage:**
- Issue: Zero unit/integration/E2E tests across codebase
- Files: No test files found in `frontend/`, `backend/`, `ml/`
- Impact: Cannot safely refactor. Regressions undetected until production. Cannot verify bug fixes. Integration between frontend-backend-DB untested.
- Fix approach: Set up pytest for backend, vitest for frontend. Write tests for: DB repository functions, analysis detection accuracy, API contracts, PDF upload flow, multilingual support. Target 70%+ coverage before April 2026 presentation.

**Shared Types Not Populated:**
- Issue: `shared/` directory exists but is empty; types duplicated across frontend/backend
- Files: `shared/` (empty), `frontend/lib/api/client.ts`, `backend/app/modules/analysis/router.py`
- Impact: Type drift between frontend/backend responses. API contract fragility. Breaking changes hard to detect.
- Fix approach: Create `shared/types.ts` with AnalysisRequest, Issue, AnalysisResponse, BackendAnalysisResponse. Export from both frontend/backend. Use TypeScript for type checking across API boundary.

**Infrastructure Configuration Empty:**
- Issue: `infra/` directory exists but contains no Docker, Kubernetes, or Azure deployment configs
- Files: `infra/` (empty)
- Impact: No container images built. Azure VM deployment manual and undocumented. No CI/CD pipeline. Production deployment path unclear before July 2026 deadline.
- Fix approach: Create Dockerfile for backend (FastAPI + Python 3.11) and frontend (Next.js). Write docker-compose.yml for local dev. Create GitHub Actions workflow for CI/CD. Write Azure deployment manifests for vLLM endpoint.

---

## Known Bugs

**Ingestion Endpoint Error Handling Insufficient:**
- Symptoms: File processing failures return generic 500 error with no context
- Files: `backend/app/modules/ingestion/router.py` (lines 38-40)
- Trigger: Upload malformed PDF, oversized file, or unsupported format
- Workaround: None. Errors logged to stdout only.
- Fix approach: Implement structured error responses. Add file size validation (set reasonable limit). Distinguish between validation errors (400) and processing errors (500). Return specific error codes for PDF parsing failures.

**Frontend API Error Handling Incomplete:**
- Symptoms: Network failures or invalid responses crash page; no fallback UI
- Files: `frontend/lib/api/client.ts` (lines 144-170, 173-193)
- Trigger: Backend endpoint times out, returns invalid JSON, or response.ok=false
- Workaround: Manual page reload required
- Fix approach: Implement retry logic with exponential backoff in client. Add error boundary in analyze page. Display user-friendly error messages for common scenarios (server down, network timeout, invalid response).

**Severity Mapping Fragile:**
- Symptoms: Multiple severity taxonomies (rule: outdated/biased/offensive/incorrect; DB: low/medium/high; frontend maps both ways)
- Files: `backend/app/modules/analysis/router.py` (lines 58, 254-358), `frontend/lib/api/client.ts` (lines 36-50)
- Trigger: Adding new severity level or changing mapping logic breaks frontend display
- Workaround: None. Inconsistent severity representation in UI.
- Fix approach: Define single canonical severity enum in `shared/types.ts`. Update backend to use only this enum. Remove mapping logic from frontend.

**CORS Configuration Hardcoded to localhost:**
- Symptoms: Cannot deploy frontend/backend separately; fails in production with origin mismatch
- Files: `backend/app/main.py` (lines 12-21)
- Trigger: Deploy to production URL different from localhost:3000
- Workaround: Manual header injection (not recommended)
- Fix approach: Read CORS origins from environment variable. Support multiple origins for staging/production. Add wildcard logic for subdomains if needed.

---

## Security Considerations

**Unvalidated File Upload:**
- Risk: No file size limit, MIME type validation only checks content-type header (easily spoofed). Large/malicious PDFs could cause DoS
- Files: `backend/app/modules/ingestion/router.py` (lines 6-40)
- Current mitigation: Content-type header check
- Recommendations: Implement max file size (e.g., 50MB). Validate PDF structure with fitz.open error handling. Consider virus scanning for public deployment. Rate-limit uploads per user/org.

**Private Mode Not Enforced in Demo:**
- Risk: When DB is enabled, private_mode prevents full text storage (only SHA256 hash), but current rule-based demo stores full text in response
- Files: `backend/app/modules/analysis/router.py` (lines 49, 284-285)
- Current mitigation: DB schema has CHECK constraint for private_mode; client-side setting ignored in demo
- Recommendations: Enforce private_mode logic in demo endpoint. Return redacted response when private_mode=true (only char ranges, no text). Add audit logging for private vs non-private mode usage.

**API Key / Authentication Not Implemented:**
- Risk: /api/v1 endpoints accessible without authentication. No rate limiting. Public endpoint can be abused by scrapers
- Files: `backend/app/main.py`, all router files
- Current mitigation: None
- Recommendations: Implement Bearer token auth or API key validation. Add rate limiting middleware (FastAPI-Limiter). Require org_id / user_email (currently optional). Log all API calls for audit trail.

**Environment Configuration Incomplete:**
- Risk: Database credentials, Azure API keys, model endpoints likely to be hardcoded or stored in .env (which is .gitignored but still a risk)
- Files: `.env*` files not present in repo (good), but backend may need DB_URL, AZURE_ENDPOINT, MODEL_KEY
- Current mitigation: .env is .gitignored
- Recommendations: Create .env.example with placeholder values. Use pydantic-settings for config validation. Implement secrets rotation policy. Document all required env vars in README.

**Foreign Key Cascade Deletes:**
- Risk: Deleting org cascades to users, documents, runs, findings. Orphan data possible if deletion logic flawed
- Files: `db/schema.sql` (lines 20, 42, 80, 142)
- Current mitigation: Schema design is correct for use case
- Recommendations: Implement soft-delete pattern (deleted_at timestamp) for audit trails. Add deletion confirmations in admin UI. Test cascade behavior thoroughly.

---

## Performance Bottlenecks

**Rule-Based Detection O(n*m) Complexity:**
- Problem: For each of 127 rules, does full-text search with string.lower().find(). Text length n, rules m. No indexing or early termination.
- Files: `backend/app/modules/analysis/router.py` (lines 221-256)
- Cause: Simple linear scan per rule. No trie, regex compilation, or NLP tokenization
- Improvement path: Use regex compilation with re.finditer(). Implement trie structure for keyword matching. Cache compiled patterns. Consider parallel rule evaluation. Profile with large texts (>1MB).

**PDF Text Extraction to Memory:**
- Problem: Full PDF loaded into memory (file_content, then doc object, then all text concatenated). Large PDFs (>100MB) cause memory exhaustion
- Files: `backend/app/modules/ingestion/router.py` (lines 17-27)
- Cause: await file.read() loads entire upload into RAM. fitz iterates all pages sequentially. No streaming.
- Improvement path: Implement chunked file reading with SpooledTemporaryFile. Extract text page-by-page and stream to S3/storage. Set file size limit (50MB max). Monitor memory usage in production.

**No Caching:**
- Problem: Identical analysis requests recompute findings. No caching layer for model responses or extracted text
- Files: Analysis router stateless; database repo not integrated
- Cause: Demo mode doesn't store or cache anything. LLM integration will be slow without response cache
- Improvement path: Implement Redis cache for repeated text analyses (key: text_sha256, ttl: 24h). Cache PDF extractions per document_id. Consider caching model embeddings for clustering.

**Frontend API Client No Timeouts:**
- Problem: fetch() calls have no timeout. Hung requests block UI indefinitely
- Files: `frontend/lib/api/client.ts` (lines 151, 177)
- Cause: Fetch API default timeout is 90s; should be 30s for user experience
- Improvement path: Wrap fetch with AbortController and 30s timeout. Add loading state timeout warnings at 20s. Implement request cancellation.

---

## Fragile Areas

**Analysis Router State Coherence:**
- Files: `backend/app/modules/analysis/router.py`
- Why fragile: Four independent code paths (demo mode + commented DB code). Parameter validation loose. severity enum used inconsistently (outdated/biased vs low/medium/high). Changes to one path don't propagate.
- Safe modification: Create shared Issue dataclass with strict validation. Extract severity mapping to enum. Write tests for both demo + DB paths side-by-side. Use type hints strictly.
- Test coverage: Zero. All paths untested.

**Frontend Demo Data Generation:**
- Files: `frontend/lib/utils/demoData.ts` (assumed to exist)
- Why fragile: Demo data format must match actual API response format. No schema validation. Changes to backend response break frontend without error
- Safe modification: Share Issue schema between frontend/backend via TypeScript. Use Zod or ts-rest for runtime validation. Add integration tests that verify response shape.
- Test coverage: No tests found.

**Multilingual Support Assumptions:**
- Files: `frontend/app/[locale]/analyze/page.tsx` (uses useLocale()), analysis router (language parameter)
- Why fragile: Language detection is 'auto' by default but not implemented. Locale routing exists but not all pages translated. Translation keys may be missing.
- Safe modification: Implement language auto-detection (use langdetect library in backend). Validate all translation keys exist in both locales. Add language-specific test fixtures.
- Test coverage: No multilingual tests.

**Configuration Snapshot in DB:**
- Files: `db/schema.sql` (config_snapshot JSONB), `backend/app/db/repository.py` (line 69)
- Why fragile: Schema is stored as JSON string without validation. Migration path unclear if config structure changes
- Safe modification: Use Pydantic model for config validation before JSON serialization. Version config snapshots. Add migration scripts for schema changes.
- Test coverage: No roundtrip tests for config serialization/deserialization.

---

## Scaling Limits

**In-Memory Rule Dictionary:**
- Current capacity: 127 rules (English + Hebrew)
- Limit: At ~500 rules, linear search becomes noticeably slow (O(n*m) for each request)
- Scaling path: Migrate to database rules table with index. Use Elasticsearch for keyword matching. Partition rules by language/category. Cache compiled regexes.

**PyMuPDF PDF Processing:**
- Current capacity: Single-threaded processing, ~100MB PDF per request acceptable
- Limit: Large PDFs (>500MB) cause memory spikes. Concurrent uploads exhaust resources
- Scaling path: Use async PDF processing with process pool. Implement streaming text extraction. Store extracted text in object storage (S3). Use message queue (Celery) for background jobs.

**Database Connections:**
- Current capacity: asyncpg default (10-20 connections)
- Limit: At ~50 concurrent users analyzing documents, connection pool exhaustion possible
- Scaling path: Configure connection pooling (pgBouncer). Implement connection timeout and retry logic. Monitor pool utilization in production.

**Frontend Build Size:**
- Current capacity: Next.js 16, Tailwind v4, framer-motion, lucide-react reasonable bundle
- Limit: Adding more components/libraries could exceed 500KB (main bundle). Mobile users affected
- Scaling path: Use dynamic imports for heavy components. Tree-shake unused animation functions. Monitor bundle size in CI.

---

## Dependencies at Risk

**PyMuPDF (pymupdf==1.23.8):**
- Risk: PyMuPDF has known CVE history (PDF parsing vulnerabilities). Library is bindings to C library (mupdf). Maintenance concerns.
- Impact: Security vulnerabilities in PDF parsing. Slow updates from upstream.
- Migration plan: Replace with Docling (already validated in R&D). Docling is actively maintained, supports more formats, better layout understanding.

**Prisma in Frontend but Not Used:**
- Risk: `@prisma/client` in package.json but frontend has no ORM need. Dead dependency.
- Impact: Bundle bloat. False signal about architecture (implies backend/DB integration doesn't exist yet).
- Migration plan: Remove @prisma/client and prisma from package.json. If backend needs ORM, use SQLAlchemy (Python, not Node).

**Hardcoded GLAAD Reference URL:**
- Risk: Reference URL in frontend code hardcoded to https://www.glaad.org/reference (lines 94, 110, 126)
- Impact: URL rot possible. No way to update references without code changes. Should be configuration or API response
- Migration plan: Move reference URLs to backend config table. Return references from analysis endpoint. Allow org customization of resources.

**Next.js 16 / React 19 Cutting Edge:**
- Risk: Very recent versions. May have undiscovered bugs or breaking changes in minor updates
- Impact: Stability concerns for long-term maintenance. Ecosystem tools may lag
- Migration plan: Pin to stable minor versions (16.0.x). Test before upgrading. Monitor release notes. Consider upgrading on quarterly cadence.

---

## Missing Critical Features

**User Authentication / Authorization:**
- Problem: No login system. No per-org or per-user access control. org_slug / user_email optional parameters ignored
- Blocks: Cannot support multi-org deployments. Admin features unimplementable. Audit trail incomplete
- Path: Implement FastAPI security (OAuth2, JWT, or SSO). Create auth middleware. Add role checks (user, org_admin, site_admin per schema). Require user context on all endpoints.

**Report Generation / Export:**
- Problem: Analysis results visible in UI only. No PDF report, CSV export, or shareable link
- Blocks: Cannot meet business requirement for downloadable reports
- Path: Add endpoint `/api/v1/analysis/{run_id}/export` supporting formats: PDF, JSON, CSV. Use reportlab or weasyprint for PDF generation.

**Feedback / Model Improvement Loop:**
- Problem: No way to report false positives/negatives or provide corrections. Model training is one-time offline process
- Blocks: Cannot improve model quality post-deployment. No way to collect LGBTQ+ community input
- Path: Add `/api/v1/feedback/{finding_id}` endpoint to record corrections. Implement periodic retraining pipeline triggered by feedback accumulation. Create feedback dashboard for admins.

**Glossary / Knowledge Base:**
- Problem: Frontend has glossary page route but likely unimplemented. No glossary API or content
- Blocks: Cannot provide term definitions or educational content
- Path: Create `/api/v1/glossary` endpoint returning terms/definitions. Store glossary in DB (terms table). Support multiple languages. Link from analysis results to glossary entries.

**Admin Dashboard:**
- Problem: Frontend has admin page route but likely unimplemented. No stats, user management, or configuration UI
- Blocks: Cannot monitor usage, manage organizations, or configure rules
- Path: Implement `/api/v1/admin/stats` (usage, error rates). Create admin UI for rule management, user/org CRUD, log viewing.

**Webhook / Async Analysis:**
- Problem: All analysis synchronous. No way to queue long-running analyses or receive notifications
- Blocks: Cannot handle large documents. No progress indication for slow analyses
- Path: Implement message queue (Celery/Redis or async task system). Create webhook endpoints for async job notifications. Add `/api/v1/analysis/async` endpoint returning job_id.

---

## Test Coverage Gaps

**Backend Analysis Detection Untested:**
- What's not tested: Rule matching accuracy, edge cases (empty text, special chars, Hebrew morphology), severity mapping, multilingual support
- Files: `backend/app/modules/analysis/router.py`
- Risk: Changes to TERM_RULES or find_issues() function break undetected. False positive/negative rates unknown
- Priority: High

**Database Layer Untested:**
- What's not tested: All repository functions in `backend/app/db/repository.py`. Transaction logic, cascade deletes, constraint enforcement
- Files: `backend/app/db/repository.py`
- Risk: DB integration enablement without validation. Data corruption possible. Org/user isolation violations undetected
- Priority: High

**Frontend API Integration Untested:**
- What's not tested: analyzeText() client function, response transformation, error handling, retry logic
- Files: `frontend/lib/api/client.ts`
- Risk: Frontend silently fails to parse backend response. Error states not caught until user reports bug
- Priority: High

**PDF Upload Flow Untested:**
- What's not tested: File validation, extraction accuracy, error handling for malformed PDFs
- Files: `backend/app/modules/ingestion/router.py`
- Risk: Malicious/oversized files could crash server. Extraction quality unknown
- Priority: Medium

**Multilingual Support Untested:**
- What's not tested: Hebrew text handling, right-to-left layout, language auto-detection, translation key completeness
- Files: Frontend locale routing, backend language parameter
- Risk: Hebrew rendering breaks in production. Missing translations cause blank UI. Language detection fails
- Priority: Medium

**API Contract Testing:**
- What's not tested: Frontend/backend request/response schema validation, versioning strategy, breaking changes
- Files: All API endpoints
- Risk: Changes to one side break the other. No schema documentation
- Priority: Medium

---

*Concerns audit: 2026-03-08*
