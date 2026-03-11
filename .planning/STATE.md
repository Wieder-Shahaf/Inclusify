---
gsd_state_version: 1.0
milestone: v0.6
milestone_name: milestone
status: completed
stopped_at: Completed 05.3-04-PLAN.md
last_updated: "2026-03-11T09:43:37.818Z"
last_activity: 2026-03-11 - Deployed vLLM 0.6.6 with Qwen2.5-3B-Instruct-GPTQ-Int4 on VM
progress:
  total_phases: 11
  completed_phases: 7
  total_plans: 23
  completed_plans: 21
  percent: 89
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-08)

**Core value:** Academics can identify and fix non-inclusive language in their work before publication
**Current focus:** Phase 5 - Production Deployment

## Current Position

Phase: 5.2 of 7 (Model Migration) - COMPLETE
Plan: 1 of 1 in current phase (05.2-01 complete)
Status: Phase 5.2 complete - vLLM deployed with GPTQ model
Last activity: 2026-03-11 - Deployed vLLM 0.6.6 with Qwen2.5-3B-Instruct-GPTQ-Int4 on VM

Progress: [█████████░] 89%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 6.5 min
- Total execution time: 1.2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-infrastructure-foundation | 3 | 31 min | 10 min |
| 02-core-services | 3 | 19 min | 6 min |
| 03-llm-integration | 3 | 10 min | 3.3 min |
| 04-frontend-integration | 2 | 12 min | 6 min |

**Recent Trend:**
- Last 5 plans: 03-02 (4 min), 03-03 (3 min), 04-01 (4 min), 04-02 (8 min)
- Trend: Fast pace continuing, frontend integration efficient

*Updated after each plan completion*
| Phase 04 P03 | 5min | 4 tasks | 2 files |
| Phase 05 P00 | 2min | 2 tasks | 2 files |
| Phase 05.1 P01 | 3min | 3 tasks | 3 files |
| Phase 05.2 P01 | 16min | 3 tasks | 2 files |
| Phase 05.2 P02 | 2min | 3 tasks | 2 files |
| Phase 05.3 P01 | 3min | 3 tasks | 5 files |
| Phase 05.3 P02 | 3min | 3 tasks | 8 files |
| Phase 05.3 P03 | 2 | 3 tasks | 7 files |
| Phase 05.3 P04 | 4min | 4 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap creation: 7 phases across 2 milestones (April 15 E2E demo, July 8 final)
- Phase 3 (LLM) identified as critical path - gates entire demo
- Docker infrastructure: Python 3.12-slim and Node 22-slim (not Alpine) for native module compatibility
- Non-root containers: appuser (UID 1000) for backend, nextjs (UID 1001) for frontend
- Profile-based compose: dev includes postgres, prod uses Azure PostgreSQL
- Azure PostgreSQL B1ms tier (~$15/month) for student credits compatibility
- Azure CLI scripts over Terraform for course simplicity
- Idempotent provisioning pattern for Azure resources
- asyncio.wait_for for Python 3.9 compatibility (not asyncio.timeout)
- asyncpg pool: min=2, max=10, 5s acquire timeout, 60s command timeout
- SQLAlchemy Uuid type for cross-database compatibility (PostgreSQL/SQLite)
- Redis optional for graceful local dev without full Docker stack
- JWT role claim added via custom JWTStrategyWithRole.write_token
- Docling subprocess isolation: imports inside worker function for memory safety
- pypdf for lightweight pre-validation before heavy Docling processing
- Python 3.12 required for Docling (venv recreated via pyenv)
- RBAC: Role hierarchy using numeric levels (site_admin=3 > org_admin=2 > user=1)
- RBAC: 403 with "Insufficient permissions" for role failures (not 404)
- Hebrew not supported by pysbd - falls back to English segmenter
- Circuit breaker opens after 3 failures, recovers after 60 seconds
- VLLMClient returns None on any error (timeout, HTTP, circuit open)
- Hybrid detection: LLM preferred over rules for overlapping spans (50% threshold)
- analysis_mode field reports detection method (llm, hybrid, rules_only)
- Frontend demo mode toggle via NEXT_PUBLIC_USE_DEMO_MODE environment variable
- Added full_text to ingestion response for frontend analysis needs
- Health polling every 30 seconds balances responsiveness with server load
- 15-second threshold for extended wait message during processing
- Error messages mapped from backend error patterns to user-friendly translations
- [Phase 04]: CORS uses ALLOWED_ORIGINS env var with localhost:3000 fallback
- [Phase 05]: Validation script uses SKIP for not-yet-deployed resources (graceful pre-deployment)
- [Phase 05.1]: Group07 as default resource group for all Azure resources
- [Phase 05.1]: VNet discovery from InclusifyModel VM instead of hardcoded VNet name
- [Phase 05.2]: GPTQ instead of AWQ (T4 GPU compute capability 7.5 requires GPTQ)
- [Phase 05.2]: vLLM 0.6.6 with transformers 4.57.6 (5.x incompatible)
- [Phase 05.2]: Dedicated vllm-venv on VM for isolation
- [Phase 05.2]: Model name configurable via VLLM_MODEL_NAME environment variable
- [Phase 05.3]: Token storage in localStorage with expiry tracking (rememberMe: 30 days vs 1 day)
- [Phase 05.3]: Avatar uses email hash for consistent color assignment (no Gravatar)
- [Phase 05.3]: Admin nav link hidden for non-admin users (role-based visibility)
- [Phase 05.3]: Suspense boundaries required for useSearchParams in Next.js 14+
- [Phase 05.3]: Admin page returns 404 for non-admins (not login redirect)

### Key Research Findings

From .planning/research/:
- vLLM v0.6.6 with `--dtype=half` for T4 GPU (0.17.0 requires CUDA 12.9+)
- AWQ incompatible with T4 (compute capability 7.5, requires 8.0+) - use GPTQ-Int4
- FastAPI Users 13.x + pwdlib (not passlib - deprecated)
- Docling 2.76.0 for document parsing
- Azure Container Apps over AKS (simpler)
- asyncpg built-in pooling (no PgBouncer needed)

### Pending Todos

None yet.

### Blockers/Concerns

- vLLM currently localhost only - may need VNet binding for Container Apps access

### Roadmap Evolution

- Phase 05.1 inserted after Phase 05: Azure Infrastructure - Create PostgreSQL, ACR, Container Apps in Group07 (URGENT)
- Phase 05.2 inserted after Phase 05: Model Migration - Install vLLM on VM, download Qwen2.5-3B-AWQ (URGENT)
- Phase 05.3 inserted after Phase 05: Auth Frontend - Build login/register pages with OAuth (URGENT)
- Phase 05.4 inserted after Phase 05: LoRA Retraining - Train unified adapter on Qwen2.5 for Hebrew/English (URGENT)

## Session Continuity

Last session: 2026-03-11T09:38:38.069Z
Stopped at: Completed 05.3-04-PLAN.md
Resume file: None
