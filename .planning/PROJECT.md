# Inclusify

## What This Is

An LGBTQ+ inclusive language analyzer for academic texts, built for the Achva LGBT organization. Users upload Hebrew or English documents (PDF or pasted text), and the system detects LGBTQphobic, outdated, biased, or pathologizing language using a fine-tuned LLM. Results show severity-graded alerts with explanations, inclusive alternatives, and downloadable reports.

## Core Value

Academics and researchers can identify and fix non-inclusive language in their work before publication, making their writing more respectful and accurate.

## Requirements

### Validated

<!-- Shipped and confirmed working in POC -->

- ✓ Frontend UI for document upload and analysis visualization — POC
- ✓ FastAPI backend with REST API structure (`/api/v1/*`) — POC
- ✓ PostgreSQL schema with multi-tenant support — POC
- ✓ i18n support for Hebrew/English with RTL handling — POC
- ✓ Frontend API client with type transformations — POC
- ✓ Backend repository layer (asyncpg queries) — POC
- ✓ Fine-tuned LLM model (suzume-llama-3-8B with QLoRA) — POC
- ✓ Rule-based detection fallback (127 terms) — POC
- ✓ Severity taxonomy (outdated/biased/offensive/incorrect) — POC

### Active

<!-- Current scope. Building toward these for v1. -->

- [ ] Database connected to backend (activate existing asyncpg layer)
- [ ] vLLM deployed on Azure VM with T4 GPU
- [ ] LLM inference integrated into analysis endpoint
- [ ] Frontend wired to real backend API (remove demo mode)
- [ ] Docling replaces PyMuPDF for document parsing
- [ ] Docker containerization (frontend + backend)
- [ ] Azure deployment (containers + managed PostgreSQL)
- [ ] Authentication (email/password + optional SSO)
- [ ] Simple RBAC (user and admin roles)
- [ ] Admin dashboard with real analytics
- [ ] Admin user/organization management
- [ ] Private mode enforcement (per-document, no text storage)
- [ ] WCAG 2.1 accessibility compliance

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Complex RBAC (org_admin level) — simpler user/admin model sufficient for v1
- Mobile app — web-first, responsive design handles mobile browsers
- Real-time collaboration — single-user analysis workflow
- Video/audio analysis — text-only scope
- OAuth provider management UI — SSO config via environment variables
- Model retraining pipeline — fine-tuning done offline, v2 consideration

## Context

**POC State:**
- Frontend works with demo data, full upload→results flow implemented
- Backend has placeholder rule-based detection, DB code written but commented out
- PostgreSQL schema is production-ready with 11 tables
- Fine-tuned model validated locally via `ml/inference_demo.py`
- Azure VM with T4 GPU provisioned but vLLM not deployed
- Docling validated in R&D as PyMuPDF replacement

**Team:** Shahaf Wieder, Barak Sharon, Rasha Daher, Lama Zarka, Adan Daxa

**Academic Context:** Built for Achva College, serves LGBTQ+ advocacy in academic settings.

## Constraints

- **Deadline**: April 15, 2026 — Full E2E demo (real analysis, DB, deployed)
- **Deadline**: July 8, 2026 — Final presentation
- **Infrastructure**: Microsoft Azure (course requirement)
- **GPU**: Single T4 GPU on Azure VM for inference
- **Languages**: Hebrew and English only (no other languages in v1)
- **Budget**: Academic project, Azure student credits

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| vLLM for inference | Optimized serving, supports LoRA adapters natively | — Pending |
| Docling over PyMuPDF | Better layout preservation, validated in R&D | — Pending |
| Simple user/admin RBAC | Faster to implement, sufficient for academic use | — Pending |
| Per-document private mode | User control, matches research workflow | — Pending |
| Email/password + optional SSO | Flexibility without SSO complexity required | — Pending |

---
*Last updated: 2026-03-08 after initialization*
