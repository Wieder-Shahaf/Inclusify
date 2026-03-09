# Phase 2: Core Services - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can authenticate and upload documents with proper text extraction. This phase delivers:
- JWT authentication with email/password via FastAPI Users 13.x
- Simple RBAC (user and admin roles) enforced on API routes
- Docling-based PDF parsing replacing PyMuPDF
- JWT refresh with Redis backing

</domain>

<decisions>
## Implementation Decisions

### Docling Processing
- Hard page limit: 50 pages maximum. Reject larger documents with clear error message.
- Error handling: Return specific error messages for password-protected ("PDF is password-protected") and corrupted PDFs ("PDF appears corrupted"). User should know exactly what's wrong.
- Progress UX: Indeterminate spinner with status text ("Extracting text..." → "Analyzing content..."). No percentage progress.
- Isolation: Run Docling in subprocess with 60-second timeout. Kill process if exceeded. Protects API server from crashes.

### RBAC Enforcement
- Authorization denial: Return 403 Forbidden with message ("Insufficient permissions"). Don't hide endpoints with 404.
- Role storage: Embed role in JWT claims. Fast checks without DB lookup. Role changes require new token (logout/login).
- Admin scope: View-only access to other users' documents/analyses. Admins can see but not edit/delete user content.
- Rate limiting: Skip for v1. Add later if abuse becomes a problem.

### Claude's Discretion
- JWT token lifetimes (access and refresh durations)
- Password complexity requirements
- Email verification flow (whether required at all)
- Redis connection pooling and error handling
- Docling subprocess communication mechanism

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/db/repository.py`: User and organization CRUD already stubbed (commented out)
- `db/schema.sql`: users table with role column, organizations table ready
- `frontend/lib/api/client.ts`: API client ready to add auth headers
- `backend/app/main.py`: CORS already configured, add middleware here

### Established Patterns
- asyncpg pool: min=2, max=10, 5s acquire timeout (from Phase 1)
- Fail-fast philosophy: 5s timeouts, startup checks
- Environment variables: `PGHOST`, `PGPORT`, etc. pattern established
- FastAPI dependency injection: `get_db` dependency ready

### Integration Points
- `backend/app/main.py`: Add FastAPI Users router, JWT middleware
- `backend/app/modules/ingestion/router.py`: Replace PyMuPDF with Docling
- `backend/app/db/deps.py`: Add `get_current_user`, `require_admin` dependencies
- Redis: New service for JWT refresh token storage

</code_context>

<specifics>
## Specific Ideas

- "Reject documents over 50 pages" - aligns with academic paper length, prevents memory issues
- "User should know exactly what's wrong" - clear error messages for PDF issues
- "View-only admin access" - admins can see but not modify user content
- FastAPI Users 13.x + pwdlib (not passlib - deprecated per PITFALLS.md)
- Subprocess isolation for Docling (per PITFALLS.md memory exhaustion concern)

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 02-core-services*
*Context gathered: 2026-03-09*
