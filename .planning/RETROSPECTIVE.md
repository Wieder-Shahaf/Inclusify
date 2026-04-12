# Retrospective: Inclusify

---

## Milestone: v1.0 — Full Platform

**Shipped:** 2026-04-12
**Phases:** 13 | **Plans:** 37
**Timeline:** 2025-12-12 → 2026-04-12 (122 days)

### What Was Built

- Docker containerization + Azure Container Apps with VNet integration
- asyncpg pool activation, PostgreSQL Flexible Server connected
- FastAPI Users 13.x JWT auth + Google OAuth with guest mode
- Docling document parsing (subprocess isolation for memory safety)
- Qwen2.5-3B QLoRA fine-tuning (r=8, dropout=0.2) — 90% F1, 34.5 req/sec
- HybridDetector: vLLM contextual + 127-term rule-based, span deduplication
- Frontend wired to real API — full upload → analysis → results flow
- Admin dashboard with SWR-powered analytics (raw asyncpg SQL)
- WCAG 2.1 AA: LiveAnnouncer, RTL keyboard nav, compliant contrast
- GitHub Actions CI/CD for automated Azure deployment
- Private mode enforcement via DB CHECK constraint

### What Worked

- **Wave-based parallelization** within phases kept execution fast — phases 1–4 completed same day
- **TDD-first pattern (Wave 0 plans)** caught interface issues before implementation in phases 3, 5.4.1
- **Decimal phase insertion** for urgent work (5.1–5.5) kept the roadmap ordered without renumbering
- **Subprocess isolation for Docling** solved the memory exhaustion risk cleanly
- **GPTQ discovery early** — catching AWQ incompatibility with T4 before heavy VM investment saved significant time
- **Raw asyncpg SQL for analytics** — simpler and faster than ORM for aggregate queries

### What Was Inefficient

- **ROADMAP.md checkbox tracking lagged reality** — many plans were complete but checkboxes weren't updated, making the roadmap misleading for milestone completion review
- **Phase 03-01 (VM deployment) was manual** — no automation script for full VM bootstrap; had to be done ad hoc
- **Phase 5.4.1 blocked on API key** — dataset synthesis pipeline was built before the Claude API key was available, causing a stall
- **Multiple urgent insertions (5.1–5.5)** suggest the initial roadmap underestimated the auth and model migration complexity

### Patterns Established

- **Non-root containers**: appuser (UID 1000) / nextjs (UID 1001) — security baseline for all services
- **Profile-based compose**: dev includes postgres, prod uses Azure PostgreSQL — clean environment separation
- **Circuit breaker on vLLM client**: opens after 3 failures, 60s recovery — graceful degradation
- **LiveAnnouncer 50ms pattern**: clear-then-set for ARIA live regions ensures repeated messages announce
- **RTL keyboard flip**: `isRTL ? currentIndex - 1 : currentIndex + 1` for ArrowRight — reusable pattern
- **Backend-only OAuth flow**: code exchange on server, redirect with JWT — keeps credentials off frontend
- **Auto-link OAuth by email**: trust Google email verification, set is_verified=True automatically

### Key Lessons

- **Check GPU compute compatibility early** — T4 is 7.5, not 8.0; AWQ requires 8.0+. Always verify hardware constraints before choosing quantization format.
- **Dependency deprecation can block auth** — passlib deprecated mid-project; always check upstream maintenance status for auth libraries before committing.
- **ROADMAP.md needs updating at plan completion** — checkpoint summaries without roadmap checkbox updates created misleading progress reporting.
- **Wave 0 test infrastructure pays off** — phases with Wave 0 stubs had cleaner execution and fewer integration surprises.
- **Guest mode is high-value, low-cost** — anonymous analysis with DB persistence required minimal extra work but significantly improves demo accessibility.

### Cost Observations

- Sessions: ~40+ across 122 days
- Execution was fast (avg 4–6 min per plan for automated phases)
- Manual phases (03-01 VM setup, 05.4 training runs, 05-02 CI/CD) took longer but were VM-bound, not AI-bound

---

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 13 |
| Plans | 37 |
| Timeline (days) | 122 |
| LOC | ~19,100 |
| Commits | 415 |
| Urgent insertions | 5 decimal phases |
| Requirements shipped | 14/14 |
