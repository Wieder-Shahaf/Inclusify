# Requirements: Inclusify

## v1 Requirements

Requirements extracted from PROJECT.md for roadmap tracking.

### Infrastructure

| ID | Requirement | Priority | Phase |
|----|-------------|----------|-------|
| INFRA-01 | Docker containerization (frontend + backend) | Critical | 1 |
| INFRA-02 | Azure deployment (containers + managed PostgreSQL) | Critical | 1, 5 |

### Database

| ID | Requirement | Priority | Phase |
|----|-------------|----------|-------|
| DB-01 | Database connected to backend (activate existing asyncpg layer) | Critical | 1 |

### Authentication

| ID | Requirement | Priority | Phase |
|----|-------------|----------|-------|
| AUTH-01 | Authentication (email/password + optional SSO) | Critical | 2 |
| AUTH-02 | Simple RBAC (user and admin roles) | Critical | 2 |

### Document Processing

| ID | Requirement | Priority | Phase |
|----|-------------|----------|-------|
| DOC-01 | Docling replaces PyMuPDF for document parsing | High | 2 |

### LLM Integration

| ID | Requirement | Priority | Phase |
|----|-------------|----------|-------|
| LLM-01 | vLLM deployed on Azure VM with T4 GPU | Critical | 3 |
| LLM-02 | LLM inference integrated into analysis endpoint | Critical | 3 |

### Frontend

| ID | Requirement | Priority | Phase |
|----|-------------|----------|-------|
| FE-01 | Frontend wired to real backend API (remove demo mode) | Critical | 4 |

### Admin

| ID | Requirement | Priority | Phase |
|----|-------------|----------|-------|
| ADMIN-01 | Admin dashboard with real analytics | High | 6 |
| ADMIN-02 | Admin user/organization management | High | 6 |

### Privacy & Accessibility

| ID | Requirement | Priority | Phase |
|----|-------------|----------|-------|
| PRIV-01 | Private mode enforcement (per-document, no text storage) | High | 7 |
| A11Y-01 | WCAG 2.1 accessibility compliance | High | 7 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 | Phase 1 | Pending |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1, 5 | Complete |
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| DOC-01 | Phase 2 | Pending |
| LLM-01 | Phase 3 | Pending |
| LLM-02 | Phase 3 | Pending |
| FE-01 | Phase 4 | Pending |
| ADMIN-01 | Phase 6 | Pending |
| ADMIN-02 | Phase 6 | Pending |
| PRIV-01 | Phase 7 | Pending |
| A11Y-01 | Phase 7 | Pending |

**Coverage:** 13/13 requirements mapped to phases

## Out of Scope (v2+)

From PROJECT.md:
- Complex RBAC (org_admin level)
- Mobile app
- Real-time collaboration
- Video/audio analysis
- OAuth provider management UI
- Model retraining pipeline
- Custom glossary management
- Batch document processing
- Webhooks / API SDK
- Advanced analytics
- Audit logs

---

*Created: 2026-03-08*
*Source: PROJECT.md Active requirements*
