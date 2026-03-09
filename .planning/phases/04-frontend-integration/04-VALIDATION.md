---
phase: 4
slug: frontend-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest + @testing-library/react |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `cd frontend && npm test -- --run` |
| **Full suite command** | `cd frontend && npm test -- --run --coverage` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --run`
- **After every plan wave:** Run `cd frontend && npm test -- --run --coverage`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | FE-01 | unit | `npm test client.test.ts` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | FE-01 | manual | Browser dev tools | N/A | ⬜ pending |
| 04-02-01 | 02 | 1 | FE-01 | unit | `npm test error.test.ts` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | FE-01 | manual | Browser check | N/A | ⬜ pending |
| 04-03-01 | 03 | 2 | FE-01 | manual | Browser in HE locale | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/vitest.config.ts` — vitest configuration
- [ ] `frontend/__tests__/setup.ts` — test setup with jsdom
- [ ] `frontend/__tests__/api/client.test.ts` — API client unit tests
- [ ] `npm install -D vitest @testing-library/react @vitejs/plugin-react jsdom` — framework install

*Note: Given project timeline (April 15 presentation), Phase 4 may use manual testing with test infrastructure added in Phase 7.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real API integration works | FE-01 | Requires running backend | 1. Start backend on :8000 2. Start frontend with USE_DEMO=false 3. Upload PDF 4. Verify results |
| Hebrew RTL displays correctly | FE-01 | Visual verification | 1. Switch to Hebrew locale 2. Upload Hebrew PDF 3. Verify text direction |
| Processing animation matches API stages | FE-01 | Visual/timing verification | 1. Upload file 2. Observe stage transitions match API progress |
| Extended wait message after 15s | FE-01 | Timing verification | 1. Use slow network or large file 2. Wait 15s 3. Verify message appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
