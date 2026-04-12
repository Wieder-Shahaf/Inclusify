# Inclusify

## What This Is

An LGBTQ+ inclusive language analyzer for academic texts, built for the Achva LGBT organization. Users upload Hebrew or English documents (PDF or pasted text), and the system detects LGBTQphobic, outdated, biased, or pathologizing language using a fine-tuned LLM. Results show severity-graded alerts with explanations, inclusive alternatives, and downloadable reports.

The platform is fully deployed on Azure Container Apps with a fine-tuned Qwen2.5-3B model running on a T4 GPU via vLLM, a hybrid detection engine, JWT + Google OAuth authentication, and WCAG 2.1 AA accessibility.

## Core Value

Academics and researchers can identify and fix non-inclusive language in their work before publication, making their writing more respectful and accurate.

## Requirements

### Validated

- ✓ Frontend UI for document upload and analysis visualization — POC
- ✓ FastAPI backend with REST API structure (`/api/v1/*`) — POC
- ✓ PostgreSQL schema with multi-tenant support — POC
- ✓ i18n support for Hebrew/English with RTL handling — POC
- ✓ Frontend API client with type transformations — POC
- ✓ Backend repository layer (asyncpg queries) — POC
- ✓ Fine-tuned LLM model (Qwen2.5-3B + QLoRA) — POC + v1.0
- ✓ Rule-based detection fallback (127 terms) — POC
- ✓ Severity taxonomy (outdated/biased/offensive/incorrect) — POC
- ✓ Docker containerization (frontend + backend) — v1.0
- ✓ Azure deployment (Container Apps + managed PostgreSQL) — v1.0
- ✓ Database connected to backend (asyncpg pool activated) — v1.0
- ✓ Authentication (email/password + Google OAuth) — v1.0
- ✓ Simple RBAC (user/admin roles) — v1.0
- ✓ Docling replaces PyMuPDF for document parsing — v1.0
- ✓ vLLM deployed on Azure VM with T4 GPU — v1.0
- ✓ LLM inference integrated into analysis endpoint (HybridDetector) — v1.0
- ✓ Hebrew language support (dataset, model, RTL UI) — v1.0
- ✓ Frontend wired to real backend API (demo mode removed) — v1.0
- ✓ Admin dashboard with real analytics — v1.0
- ✓ Admin user management — v1.0
- ✓ Private mode enforcement (per-document, no text storage) — v1.0
- ✓ WCAG 2.1 accessibility compliance — v1.0
- ✓ GitHub Actions CI/CD pipeline — v1.0
- ✓ Guest mode (anonymous analysis with DB persistence) — v1.0

### Active

<!-- v2 scope — July 8, 2026 final presentation prep -->

- [ ] Presentation polish and final demo rehearsal
- [ ] Any remaining integration gaps discovered during April 15 demo
- [ ] Hebrew model adapter (extend beyond English-only LoRA)

### Out of Scope

- Complex RBAC (org_admin level) — simpler user/admin model sufficient
- Mobile app — web-first, responsive design handles mobile browsers
- Real-time collaboration — single-user analysis workflow
- Video/audio analysis — text-only scope
- OAuth provider management UI — SSO config via environment variables
- Custom glossary management — v2+ consideration
- Batch document processing — v2+ consideration
- Webhooks / API SDK — v2+ consideration
- Advanced analytics — v2+ consideration

## Context

**v1.0 State (2026-04-12):**
- Full stack deployed on Azure: frontend + backend on Container Apps, PostgreSQL Flexible Server, vLLM on T4 GPU VM
- Fine-tuned Qwen2.5-3B (qwen_r8_d0.2): 90.0% F1, 100% Precision, 81.9% Recall, 34.5 req/sec
- HybridDetector: vLLM contextual + 127-term rule-based with span deduplication
- Auth: JWT email/password + Google OAuth, guest mode with DB persistence
- Admin dashboard: KPI metrics, user list, RBAC-protected
- Accessibility: WCAG 2.1 AA, LiveAnnouncer, RTL keyboard nav
- CI/CD: GitHub Actions auto-deploy on push to main
- ~19,100 LOC (TypeScript + Python), 415 commits

**Team:** Shahaf Wieder, Barak Sharon, Rasha Daher, Lama Zarka, Adan Daxa

**Academic Context:** Built for Achva College, serves LGBTQ+ advocacy in academic settings.

## Constraints

- **Deadline**: April 15, 2026 — Full E2E demo ✅ (met)
- **Deadline**: July 8, 2026 — Final presentation
- **Infrastructure**: Microsoft Azure (course requirement)
- **GPU**: Single T4 GPU on Azure VM for inference
- **Languages**: Hebrew and English only (no other languages in v1)
- **Budget**: Academic project, Azure student credits

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| vLLM for inference | Optimized serving, supports LoRA adapters natively | ✓ Good — 34.5 req/sec, stable |
| Docling over PyMuPDF | Better layout preservation, validated in R&D | ✓ Good — subprocess isolation solved memory issues |
| Simple user/admin RBAC | Faster to implement, sufficient for academic use | ✓ Good — sufficient for all demo scenarios |
| Per-document private mode | User control, matches research workflow | ✓ Good — default OFF per user feedback |
| Email/password + Google OAuth | Flexibility without SSO complexity required | ✓ Good — auto-link by email works smoothly |
| GPTQ-Int4 over AWQ | T4 GPU compute 7.5 incompatible with AWQ (requires 8.0+) | ✓ Good — GPTQ works on T4 |
| FastAPI Users 13.x + pwdlib | passlib deprecated; 13.x has cleaner OAuth integration | ✓ Good — no migration issues |
| Hybrid detection (LLM preferred) | LLM covers context, rules cover high-precision known terms | ✓ Good — 50% span overlap threshold works |
| Azure CLI scripts over Terraform | Course simplicity, team familiarity | ✓ Good — idempotent provisioning works |
| Guest mode with DB persistence | Enable anonymous analysis, convert to user later | ✓ Good — Redis-backed session tracking |
| QLoRA rank=8, dropout=0.2 | Best from 9-config grid search | ✓ Good — 90% F1, exceeded 80% target |

---
*Last updated: 2026-04-12 after v1.0 milestone*
