---
phase: 02-core-services
plan: 02
subsystem: ingestion
tags: [docling, pypdf, pdf-parsing, subprocess, async]

# Dependency graph
requires:
  - phase: 01-infrastructure-foundation
    provides: asyncpg pool, Docker configs with Python 3.12
provides:
  - Docling-based PDF parsing with subprocess isolation
  - 50-page limit enforcement with specific error message
  - Password-protected and corrupted PDF error handling
  - 60-second processing timeout
  - UploadResponse/UploadError Pydantic models
affects: [03-llm-integration, 04-analysis-pipeline]

# Tech tracking
tech-stack:
  added: [docling>=2.69.0, pypdf>=5.0.0]
  removed: [pymupdf]
  patterns: [subprocess isolation for memory-heavy operations, ProcessPoolExecutor for CPU-bound async work]

key-files:
  created:
    - backend/app/modules/ingestion/service.py
    - backend/app/modules/ingestion/schemas.py
  modified:
    - backend/app/modules/ingestion/router.py
    - backend/requirements.txt
    - backend/tests/test_docling.py

key-decisions:
  - "Docling imports inside subprocess to isolate memory per request"
  - "pypdf for lightweight page count before Docling processing"
  - "Python 3.12 venv recreated - docling requires Python 3.10+"
  - "Dependency versions updated for compatibility: pydantic-settings>=2.3.0, python-multipart==0.0.9, pwdlib==0.2.0"

patterns-established:
  - "Subprocess isolation: ProcessPoolExecutor with imports inside worker function"
  - "PDF validation: lightweight pypdf check before heavy Docling processing"
  - "Specific error messages: user-facing messages for password-protected, corrupted, oversized documents"

requirements-completed: [DOC-01]

# Metrics
duration: 8min
completed: 2026-03-09
---

# Phase 02 Plan 02: Docling Integration Summary

**Docling-based PDF parsing with subprocess isolation, 50-page limit, and specific error messages for password-protected and corrupted PDFs**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-09T09:59:52Z
- **Completed:** 2026-03-09T10:08:30Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Replaced PyMuPDF with Docling for superior layout preservation
- Subprocess isolation protects API server from memory exhaustion
- Specific error messages per CONTEXT.md decisions (password-protected, corrupted, page limit, timeout)
- 50MB file size limit prevents DoS attacks
- 10 passing tests covering service layer and endpoint behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Docling service with subprocess isolation** - `557cf9e` (test - RED), `67d7b9d` (feat - GREEN)
2. **Task 2: Update upload router and create tests** - `61166fc` (feat)

**Plan metadata:** TBD (docs: complete plan)

_Note: Task 1 used TDD - test commit followed by implementation commit_

## Files Created/Modified
- `backend/app/modules/ingestion/service.py` - Docling subprocess wrapper with parse_pdf_async
- `backend/app/modules/ingestion/schemas.py` - UploadResponse and UploadError Pydantic models
- `backend/app/modules/ingestion/router.py` - Upload endpoint using Docling service (PyMuPDF removed)
- `backend/requirements.txt` - Added docling, pypdf; fixed version conflicts
- `backend/tests/test_docling.py` - 10 tests for service and endpoint behavior

## Decisions Made
- **Docling imports inside subprocess:** Memory isolation requires imports within _parse_pdf_sync, not at module level
- **pypdf for pre-validation:** Lightweight check for page count and encryption before heavy Docling processing
- **Python 3.12 upgrade:** Recreated venv with Python 3.12.10 (docling requires 3.10+)
- **Dependency fixes:** Updated pydantic-settings, python-multipart, pwdlib to resolve pip conflicts

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Python 3.12 venv required for Docling**
- **Found during:** Task 1 (dependency installation)
- **Issue:** Docling>=2.69.0 requires Python 3.10+, venv was Python 3.9.6
- **Fix:** Installed Python 3.12.10 via pyenv, recreated .venv with new Python
- **Files modified:** .venv (recreated)
- **Verification:** `pip install docling` succeeds, tests run with Python 3.12.10
- **Committed in:** 67d7b9d (part of Task 1)

**2. [Rule 3 - Blocking] Dependency version conflicts**
- **Found during:** Task 1 (pip install)
- **Issue:** fastapi-users 13.0.0 requires pwdlib==0.2.0 (not 0.2.1), python-multipart==0.0.9 (not 0.0.6), pydantic-settings>=2.3.0 (not ==2.1.0)
- **Fix:** Updated requirements.txt versions to match fastapi-users constraints
- **Files modified:** backend/requirements.txt
- **Verification:** `pip install -r requirements.txt` succeeds without conflicts
- **Committed in:** 67d7b9d (part of Task 1)

---

**Total deviations:** 2 auto-fixed (2 blocking issues)
**Impact on plan:** Both fixes necessary to install Docling. No scope creep - core functionality unchanged.

## Issues Encountered
- Initial tests used wrong mock target (`app.modules.ingestion.service.PdfReader` vs `pypdf.PdfReader`) due to runtime imports in _parse_pdf_sync - fixed by patching at the actual import location

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- PDF upload endpoint functional with Docling text extraction
- Ready for Phase 3 (LLM Integration) to consume extracted text
- Phase 4 (Analysis Pipeline) can build on UploadResponse schema

## Self-Check: PASSED

- FOUND: backend/app/modules/ingestion/service.py
- FOUND: backend/app/modules/ingestion/schemas.py
- FOUND: backend/app/modules/ingestion/router.py
- FOUND: backend/tests/test_docling.py
- FOUND: commit 557cf9e (test RED)
- FOUND: commit 67d7b9d (feat GREEN)
- FOUND: commit 61166fc (router update)

---
*Phase: 02-core-services*
*Completed: 2026-03-09*
