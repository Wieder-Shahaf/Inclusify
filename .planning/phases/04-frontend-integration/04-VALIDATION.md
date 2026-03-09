---
phase: 4
slug: frontend-integration
status: draft
nyquist_compliant: true
wave_0_complete: false
wave_0_deferred_to: Phase 7
created: 2026-03-09
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest + @testing-library/react |
| **Config file** | none — deferred to Phase 7 |
| **Quick run command** | `cd frontend && npm run build` (type-check only) |
| **Full suite command** | N/A — manual verification for Phase 4 |
| **Estimated runtime** | ~30 seconds (build) |

**Note:** Test infrastructure is deferred to Phase 7 (Production Hardening) per project timeline constraints (April 15 presentation). Phase 4 uses build verification + manual E2E testing.

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run build`
- **After every plan wave:** Manual E2E verification per checkpoint
- **Before `/gsd:verify-work`:** Build must succeed, E2E checkpoint must pass
- **Max feedback latency:** 30 seconds (build time)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 04-01-01 | 01 | 1 | FE-01 | build | `npm run build` | pending |
| 04-01-02 | 01 | 1 | FE-01 | build | `npm run build` | pending |
| 04-01-03 | 01 | 1 | FE-01 | build+grep | `npm run build && grep...` | pending |
| 04-02-01 | 02 | 1 | FE-01 | tsc | `npx tsc --noEmit` | pending |
| 04-02-02 | 02 | 1 | FE-01 | tsc | `npx tsc --noEmit` | pending |
| 04-02-03 | 02 | 1 | FE-01 | build+grep | `npm run build && grep...` | pending |
| 04-02-04 | 02 | 1 | FE-01 | build+grep | `npm run build && grep...` | pending |
| 04-02-05 | 02 | 1 | FE-01 | build+grep | `npm run build && grep...` | pending |
| 04-03-01 | 03 | 2 | FE-01 | python | `python -c "from app.main..."` | pending |
| 04-03-02 | 03 | 2 | FE-01 | build | `npm run build` | pending |
| 04-03-03 | 03 | 2 | FE-01 | build+grep | `grep + npm run build` | pending |
| 04-03-04 | 03 | 2 | FE-01 | manual | E2E checkpoint | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements — DEFERRED

**Decision:** Wave 0 test infrastructure is deferred to Phase 7 (Production Hardening).

**Rationale:**
- April 15 presentation deadline prioritizes E2E demo over test coverage
- Phase 4 scope is integration wiring, not new business logic
- Build verification + manual E2E provides sufficient feedback for integration work
- Phase 7 explicitly includes test infrastructure as part of hardening

**Deferred items:**
- [ ] `frontend/vitest.config.ts` — vitest configuration
- [ ] `frontend/__tests__/setup.ts` — test setup with jsdom
- [ ] `frontend/__tests__/api/client.test.ts` — API client unit tests
- [ ] `npm install -D vitest @testing-library/react @vitejs/plugin-react jsdom` — framework install

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real API integration works | FE-01 | Requires running backend | 1. Start backend on :8000 2. Start frontend with USE_DEMO=false 3. Upload PDF 4. Verify results |
| Hebrew RTL displays correctly | FE-01 | Visual verification | 1. Switch to Hebrew locale 2. Upload Hebrew PDF 3. Verify text direction |
| Processing animation matches API stages | FE-01 | Visual/timing verification | 1. Upload file 2. Observe stage transitions match API progress |
| Extended wait message after 15s | FE-01 | Timing verification | 1. Use slow network or large file 2. Wait 15s 3. Verify message appears |
| Demo mode disabled in production | FE-01 | Requires production build | 1. Build with .env.production 2. Verify no demo data paths |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify elements
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 deferred to Phase 7 with documented rationale
- [x] No watch-mode flags
- [x] Feedback latency < 30s (build time)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready for execution
