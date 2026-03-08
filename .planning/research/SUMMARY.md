# Research Summary

**Project:** Inclusify - LGBTQ+ Inclusive Language Analyzer
**Synthesized:** 2026-03-08
**Overall Confidence:** HIGH

---

## Key Findings

### Stack Validation (STACK.md)

| Component | Version | Status |
|-----------|---------|--------|
| vLLM | 0.17.0 (March 2026) | Use `--dtype=float` for T4 GPU |
| Docling | 2.76.0 | Replaces PyMuPDF, superior layout |
| FastAPI Users | 13.x | pwdlib (not passlib) |
| asyncpg | 0.30.0 | Built-in pooling, no PgBouncer needed |
| Azure Container Apps | Current | Preferred over AKS |

**Critical:** T4 GPU does NOT support bfloat16 (compute 7.5 < required 8.0).

### Feature Priorities (FEATURES.md)

**MVP Requirements:**
1. Authentication + Org Management (enables multi-tenant)
2. LLM Integration (core product value)
3. Admin Dashboard (required for demo)
4. Export/Reporting (delivers value)
5. Privacy Controls (competitive advantage)

**Defer to v2:** Custom glossaries, batch processing, webhooks, collaboration, audit logs.

### Architecture Patterns (ARCHITECTURE.md)

**Core Principle:** LLM inference MUST be isolated as separate service.

```
Next.js → FastAPI → vLLM (separate GPU VM)
              ↓
        PostgreSQL + Redis + Docling
```

**Key Patterns:**
- vLLM: OpenAI-compatible HTTP API with LoRA per-request
- Docling: Async with `run_in_executor`
- Auth: JWT (15min) + Redis-backed refresh tokens (7d)
- DB: Lifespan-managed asyncpg pool (not startup events)
- Docker: Multi-stage builds (150MB FastAPI, ~300MB Next.js)

### Risk Mitigation (PITFALLS.md)

**Critical Risks (Project Blockers):**
1. vLLM OOM → Use `--dtype=float`, reduce context to 2048
2. Docling memory → Page limits, subprocess isolation
3. passlib deprecated → Use FastAPI Users 13.x + pwdlib
4. Pool exhaustion → Increase max_size, add timeouts
5. Azure token expiry → Implement refresh callback

**High-Risk (Demo Failures):**
- CORS in production → Configure allowed origins
- Streaming broken by proxy → Disable buffering
- Next.js static files missing → Copy in Dockerfile

---

## Roadmap Implications

### Recommended Phase Structure

```
Phase 1: Infrastructure Foundation (Parallel)
├── Azure setup (ACR, PostgreSQL, Key Vault)
├── Docker multi-stage builds
└── DB schema activation

Phase 2: Core Services (Parallel where possible)
├── JWT authentication + Redis
├── asyncpg connection pool
└── Docling document parsing

Phase 3: LLM Integration (Sequential)
├── vLLM deployment on T4 VM
├── Client integration in FastAPI
└── Hybrid detection (rule + LLM)

Phase 4: Frontend Integration
├── Wire frontend to real API
├── Remove demo mode
└── Admin dashboard

Phase 5: Production Hardening
├── Private mode enforcement
├── Export/reporting
└── E2E testing + deployment
```

### Research Flags for Phases

| Phase | Flag | Why |
|-------|------|-----|
| 3 | vLLM benchmarking | Validate latency, batch size, LoRA switching |
| 2 | Docling memory profiling | Large PDF handling |
| 4 | Load testing | Connection pool sizing validation |

---

## Open Questions

**Resolved by Research:**
- vLLM version → 0.17.0 (pinned)
- Auth library → FastAPI Users 13.x + pwdlib
- Document parser → Docling 2.76.0
- Deployment target → Azure Container Apps
- Connection pooling → asyncpg built-in (no PgBouncer)

**Requires Implementation Validation:**
1. vLLM VRAM fit (8B model + adapters on 16GB T4)
2. Docling memory for 100+ page PDFs
3. Hebrew tokenization quality after fine-tuning
4. Azure GPU quota availability on student account

**Out of Scope for v1:**
- Custom glossary UI
- Batch document processing
- Real-time collaboration
- Audit logging

---

## Confidence Summary

| Area | Level | Evidence |
|------|-------|----------|
| Stack versions | HIGH | Official docs, recent releases (March 2026) |
| Architecture patterns | HIGH | Production examples, official best practices |
| Feature priorities | HIGH | Competitor analysis, user workflow alignment |
| Pitfall mitigations | MEDIUM-HIGH | Documented issues, community solutions |
| Azure specifics | MEDIUM | Official docs, but deployment nuances vary |

---

## Next Steps

1. **Create ROADMAP.md** — Phase breakdown with success criteria
2. **Validate GPU availability** — Check Azure T4 quota on student account
3. **Begin Phase 1** — Infrastructure setup (parallel tasks)

---

## Sources Consulted

**Primary (Official Documentation):**
- vLLM: https://docs.vllm.ai/
- Docling: https://docling-project.github.io/
- FastAPI: https://fastapi.tiangolo.com/
- Azure: https://learn.microsoft.com/azure/

**Secondary (Production Guides):**
- vLLM production deployment guides (SitePoint, Azure Tech Community)
- FastAPI best practices 2026
- Docker multi-stage build patterns
- asyncpg connection pooling

**Competitor Analysis:**
- Grammarly, Textio, Trinka (inclusive language tools)
- OpenAI, Google Cloud NLP (API patterns)

---

*Research complete: 2026-03-08*
*Ready for roadmap creation*
