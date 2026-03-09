# Roadmap: Inclusify

## Overview

Inclusify transforms from a working POC with demo data into a production-deployed LGBTQ+ inclusive language analyzer. The journey activates existing infrastructure (DB, repository layer), deploys the fine-tuned LLM on Azure GPU, integrates all components end-to-end, adds authentication and admin capabilities, then hardens for production. Milestone 1 targets April 15, 2026 (E2E Demo). Milestone 2 targets July 8, 2026 (Final Presentation).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

### Milestone 1: E2E Demo (Target: April 15, 2026)

- [x] **Phase 1: Infrastructure Foundation** - Docker builds, Azure setup, DB activation
- [x] **Phase 2: Core Services** - Authentication, Docling parsing, RBAC middleware
- [ ] **Phase 3: LLM Integration** - vLLM deployment, inference client, hybrid detection
- [ ] **Phase 4: Frontend Integration** - Wire to real API, remove demo mode
- [ ] **Phase 5: Production Deployment** - Azure Container Apps, E2E verification

### Milestone 2: Final Presentation (Target: July 8, 2026)

- [ ] **Phase 6: Admin & Analytics** - Admin dashboard, user/org management, analytics
- [ ] **Phase 7: Production Hardening** - Private mode, accessibility, polish

## Phase Details

### Phase 1: Infrastructure Foundation
**Goal**: Establish containerized services with database connectivity ready for development
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01 (Docker containerization), INFRA-02 (Azure deployment foundation), DB-01 (DB connected to backend)
**Success Criteria** (what must be TRUE):
  1. `docker compose up` starts frontend, backend, and PostgreSQL locally
  2. Backend connects to PostgreSQL and executes queries via asyncpg pool
  3. Azure Container Registry exists and accepts image pushes
  4. Azure PostgreSQL Flexible Server is provisioned and accessible
  5. Health check endpoint returns 200 with DB connection status
**Risk Flags**:
  - asyncpg pool exhaustion (PITFALLS.md #4) - configure timeouts and pool size
  - Azure Managed Identity token expiry (PITFALLS.md #5) - plan refresh callback
**Plans**: 3 plans in 2 waves

Plans:
- [x] 01-01-PLAN.md — Docker multi-stage builds and compose setup (INFRA-01)
- [x] 01-02-PLAN.md — Azure infrastructure provisioning via CLI scripts (INFRA-02)
- [x] 01-03-PLAN.md — Activate asyncpg connection pool and health endpoint (DB-01)

### Phase 2: Core Services
**Goal**: Users can authenticate and upload documents with proper text extraction
**Depends on**: Phase 1
**Requirements**: AUTH-01 (Authentication email/password), AUTH-02 (Simple RBAC), DOC-01 (Docling replaces PyMuPDF)
**Success Criteria** (what must be TRUE):
  1. User can register with email/password and receive JWT tokens
  2. User can log in and access protected endpoints
  3. User role (user/admin) is enforced on API routes
  4. PDF upload extracts text with proper layout preservation via Docling
  5. JWT refresh works without logging user out (Redis-backed)
**Risk Flags**:
  - passlib deprecation (PITFALLS.md #3) - use FastAPI Users 13.x + pwdlib
  - Docling memory exhaustion (PITFALLS.md #2) - page limits, subprocess isolation
  - JWT refresh race condition (PITFALLS.md #10) - implement mutex pattern
**Parallelization**: Auth (02-01) and Docling (02-02) can run in parallel (Wave 1). RBAC (02-03) depends on Auth (Wave 2).
**Plans**: 3 plans in 2 waves

Plans:
- [x] 02-01-PLAN.md — JWT authentication with FastAPI Users 13.x and Redis (AUTH-01)
- [x] 02-02-PLAN.md — Docling document parsing with subprocess isolation (DOC-01)
- [x] 02-03-PLAN.md — RBAC middleware and protected routes (AUTH-02)

### Phase 3: LLM Integration
**Goal**: Text analysis uses the fine-tuned LLM for contextual inclusive language detection
**Depends on**: Phase 2
**Requirements**: LLM-01 (vLLM deployed on Azure VM), LLM-02 (LLM inference integrated into analysis endpoint)
**Success Criteria** (what must be TRUE):
  1. vLLM server runs on Azure T4 VM with fine-tuned model loaded
  2. Analysis endpoint calls vLLM and returns contextual findings
  3. Hybrid detection merges rule-based and LLM results (deduped)
  4. Analysis completes in under 10 seconds for typical documents
  5. Fallback to rule-based works when vLLM is unavailable
**Risk Flags**:
  - vLLM OOM on T4 (PITFALLS.md #1) - use `--dtype=float`, reduce context to 2048
  - vLLM timeout cascading (ARCHITECTURE.md) - 30s timeout + fallback
  - Hebrew tokenization (PITFALLS.md #12) - validate with Hebrew test set
**Critical Path**: This phase gates the E2E demo. vLLM must be working.
**Plans**: TBD

Plans:
- [ ] 03-01: vLLM deployment on Azure GPU VM
- [ ] 03-02: vLLM client integration in FastAPI
- [ ] 03-03: Hybrid detection logic (rule + LLM merge)

### Phase 4: Frontend Integration
**Goal**: Frontend displays real analysis results from the production backend
**Depends on**: Phase 3
**Requirements**: FE-01 (Frontend wired to real backend API)
**Success Criteria** (what must be TRUE):
  1. Frontend calls real backend API (no demo mode or mock data)
  2. User can upload PDF, see processing state, and view real analysis results
  3. Analysis findings display with severity, description, and suggestions
  4. Hebrew and English analysis both work with proper RTL/LTR handling
  5. Error states display meaningful messages (not raw HTTP errors)
**Risk Flags**:
  - CORS in production (PITFALLS.md #7) - configure allowed origins
  - Next.js static files missing (PITFALLS.md #8) - copy in Dockerfile
  - RTL rendering breaks (PITFALLS.md #9) - test Hebrew flow
**Plans**: TBD

Plans:
- [ ] 04-01: Wire frontend API client to real backend
- [ ] 04-02: Error handling and loading states
- [ ] 04-03: Hebrew/English end-to-end testing

### Phase 5: Production Deployment
**Goal**: Application is deployed to Azure and accessible for E2E demo
**Depends on**: Phase 4
**Requirements**: INFRA-02 (Azure deployment complete)
**Success Criteria** (what must be TRUE):
  1. Frontend and backend containers run on Azure Container Apps
  2. vLLM service accessible from backend container
  3. Complete flow works: upload PDF -> analysis -> view results
  4. Application accessible via public URL with HTTPS
  5. Secrets managed via Azure Key Vault (no env vars with credentials)
**Risk Flags**:
  - Cold start delays (PITFALLS.md #11) - keep minReplicas=1
  - Streaming broken by proxy (PITFALLS.md #6) - disable buffering
**Demo Checkpoint**: April 15, 2026 deadline
**Plans**: TBD

Plans:
- [ ] 05-01: Azure Container Apps deployment
- [ ] 05-02: E2E integration testing and demo preparation

---

### Phase 6: Admin & Analytics
**Goal**: Administrators can manage users/organizations and view usage analytics
**Depends on**: Phase 5
**Requirements**: ADMIN-01 (Admin dashboard with real analytics), ADMIN-02 (Admin user/organization management)
**Success Criteria** (what must be TRUE):
  1. Admin can view list of users and organizations
  2. Admin can create, edit, and deactivate users
  3. Admin can view usage metrics (analyses run, documents processed)
  4. Dashboard shows aggregate statistics (total users, recent activity)
  5. Non-admin users cannot access admin routes
**Plans**: TBD

Plans:
- [ ] 06-01: Admin dashboard backend (analytics queries, admin routes)
- [ ] 06-02: Admin dashboard frontend (user/org management UI)

### Phase 7: Production Hardening
**Goal**: Application meets privacy and accessibility requirements for final presentation
**Depends on**: Phase 6
**Requirements**: PRIV-01 (Private mode enforcement), A11Y-01 (WCAG 2.1 accessibility)
**Success Criteria** (what must be TRUE):
  1. Private mode documents have no text stored in database (DB constraint enforced)
  2. User can enable private mode per document before analysis
  3. Application passes WCAG 2.1 AA automated checks
  4. Keyboard navigation works throughout application
  5. Screen reader announces analysis results properly
**Plans**: TBD

Plans:
- [ ] 07-01: Private mode enforcement and verification
- [ ] 07-02: WCAG 2.1 accessibility audit and fixes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 (Milestone 1) -> 6 -> 7 (Milestone 2)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure Foundation | 3/3 | Complete | 2026-03-09 |
| 2. Core Services | 3/3 | Complete | 2026-03-09 |
| 3. LLM Integration | 0/3 | Not started | - |
| 4. Frontend Integration | 0/3 | Not started | - |
| 5. Production Deployment | 0/2 | Not started | - |
| 6. Admin & Analytics | 0/2 | Not started | - |
| 7. Production Hardening | 0/2 | Not started | - |

**Milestone Progress:**
- Milestone 1 (E2E Demo): 6/14 plans - Target April 15, 2026
- Milestone 2 (Final): 0/4 plans - Target July 8, 2026

## Requirement Coverage

All 13 v1 requirements mapped:

| Requirement | Description | Phase |
|-------------|-------------|-------|
| DB-01 | Database connected to backend | Phase 1 |
| INFRA-01 | Docker containerization | Phase 1 |
| INFRA-02 | Azure deployment | Phase 1, 5 |
| AUTH-01 | Authentication (email/password) | Phase 2 |
| AUTH-02 | Simple RBAC (user/admin) | Phase 2 |
| DOC-01 | Docling replaces PyMuPDF | Phase 2 |
| LLM-01 | vLLM deployed on Azure VM | Phase 3 |
| LLM-02 | LLM inference integrated | Phase 3 |
| FE-01 | Frontend wired to real API | Phase 4 |
| ADMIN-01 | Admin dashboard with analytics | Phase 6 |
| ADMIN-02 | Admin user/org management | Phase 6 |
| PRIV-01 | Private mode enforcement | Phase 7 |
| A11Y-01 | WCAG 2.1 accessibility | Phase 7 |

Coverage: 13/13 requirements mapped

## Critical Path

```
Phase 1 (Infrastructure)
    |
    v
Phase 2 (Auth + Docling) -- parallel tracks possible
    |
    v
Phase 3 (vLLM) <-- CRITICAL: Gates entire demo
    |
    v
Phase 4 (Frontend Wire-up)
    |
    v
Phase 5 (Deploy) --> April 15 Demo
    |
    v
Phase 6 (Admin)
    |
    v
Phase 7 (Hardening) --> July 8 Final
```

**Bottleneck**: Phase 3 (LLM Integration) is on the critical path. If vLLM deployment fails, demo is blocked. Mitigation: Start VM provisioning early, have quantization fallback ready.

---

*Created: 2026-03-08*
*Targeting: Milestone 1 (April 15, 2026), Milestone 2 (July 8, 2026)*
