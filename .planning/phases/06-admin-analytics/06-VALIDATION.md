---
phase: 6
slug: admin-analytics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest (frontend) |
| **Config file** | backend/pytest.ini, frontend/vitest.config.ts |
| **Quick run command** | `pytest backend/tests/test_admin.py -x -q` |
| **Full suite command** | `pytest backend/tests/ && cd frontend && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/test_admin.py -x -q`
- **After every plan wave:** Run `pytest backend/tests/ && cd frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | ADMIN-01 | unit | `pytest backend/tests/test_admin.py::test_analytics_queries -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | ADMIN-01 | unit | `pytest backend/tests/test_admin.py::test_admin_routes -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | ADMIN-02 | unit | `pytest backend/tests/test_admin.py::test_user_management -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | ADMIN-01 | e2e | `cd frontend && npm test -- admin` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | ADMIN-02 | e2e | `cd frontend && npm test -- admin-users` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_admin.py` — stubs for analytics, admin routes, user management
- [ ] `backend/tests/conftest.py` — admin user fixtures (if not exists)
- [ ] `frontend/tests/admin.test.tsx` — admin dashboard component tests

*Existing pytest/vitest infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Non-admin cannot access /admin routes | ADMIN-01 | Requires auth flow with real session | 1. Login as regular user 2. Navigate to /admin 3. Verify redirect to unauthorized |

*All other behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
