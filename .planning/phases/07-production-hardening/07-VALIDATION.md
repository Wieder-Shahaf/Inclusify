---
phase: 7
slug: production-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | jest 29.x + jest-axe (frontend) |
| **Config file** | frontend/jest.config.ts (Wave 0 creates) |
| **Quick run command** | `cd frontend && npm test -- --testPathPattern=a11y` |
| **Full suite command** | `cd frontend && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --testPathPattern=a11y`
- **After every plan wave:** Run `cd frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | PRIV-01 | unit | `cd frontend && npm test -- --testPathPattern=PrivateModeToggle` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | PRIV-01 | integration | `cd backend && pytest -k private_mode` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | A11Y-01 | unit | `cd frontend && npm test -- --testPathPattern=a11y` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | A11Y-01 | integration | `cd frontend && npm test -- --testPathPattern=keyboard` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/jest.config.ts` — Jest configuration with jsdom
- [ ] `frontend/__tests__/setup.ts` — Jest setup with RTL and jest-axe
- [ ] `frontend/__tests__/a11y/` — Directory for accessibility tests
- [ ] `npm install --save-dev jest jest-environment-jsdom @testing-library/react @testing-library/jest-dom jest-axe @types/jest-axe` — Test dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Screen reader announces results | A11Y-01 | VoiceOver/NVDA requires human verification | 1. Enable VoiceOver 2. Navigate to results 3. Verify announcements |
| Hebrew RTL keyboard navigation | A11Y-01 | Bidirectional focus behavior needs manual check | 1. Switch to Hebrew 2. Use arrow keys 3. Verify direction |
| Lock icon visibility | PRIV-01 | Visual design review | 1. Enable private mode 2. Submit analysis 3. Verify badge shows |

*Note: Automated tests cover functionality; manual tests verify UX quality.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
