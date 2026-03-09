---
phase: 2
slug: core-services
status: approved
nyquist_compliant: true
wave_0_complete: inline
created: 2026-03-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Config file** | pyproject.toml (created in-task) |
| **Quick run command** | `pytest backend/tests/ -x --tb=short` |
| **Full suite command** | `pytest backend/tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/ -x --tb=short`
- **After every plan wave:** Run `pytest backend/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Created In | Status |
|---------|------|------|-------------|-----------|-------------------|------------|--------|
| 02-01-01 | 01 | 1 | AUTH-01 | unit | `pytest backend/tests/test_auth.py::test_register -x` | Task 1 (TDD) | ⬜ pending |
| 02-01-02 | 01 | 1 | AUTH-01 | unit | `pytest backend/tests/test_auth.py::test_login -x` | Task 1 (TDD) | ⬜ pending |
| 02-01-03 | 01 | 1 | AUTH-01 | unit | `pytest backend/tests/test_auth.py::test_invalid_token -x` | Task 1 (TDD) | ⬜ pending |
| 02-01-04 | 01 | 1 | AUTH-01 | unit | `pytest backend/tests/test_auth.py::test_refresh -x` | Task 2 (TDD) | ⬜ pending |
| 02-02-01 | 02 | 1 | DOC-01 | integration | `pytest backend/tests/test_docling.py::test_pdf_upload -x` | Task 1 (TDD) | ⬜ pending |
| 02-02-02 | 02 | 1 | DOC-01 | unit | `pytest backend/tests/test_docling.py::test_page_limit -x` | Task 1 (TDD) | ⬜ pending |
| 02-02-03 | 02 | 1 | DOC-01 | unit | `pytest backend/tests/test_docling.py::test_password_protected -x` | Task 1 (TDD) | ⬜ pending |
| 02-03-01 | 03 | 2 | AUTH-02 | unit | `pytest backend/tests/test_rbac.py::test_admin_access -x` | Task 1 (TDD) | ⬜ pending |
| 02-03-02 | 03 | 2 | AUTH-02 | unit | `pytest backend/tests/test_rbac.py::test_user_forbidden -x` | Task 1 (TDD) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Test Creation Strategy

Tests are created inline during TDD tasks (no separate Wave 0 plan):

- **Plan 02-01 Task 1:** Creates `test_auth.py` with registration/login/token tests
- **Plan 02-01 Task 2:** Adds refresh token tests to `test_auth.py`
- **Plan 02-02 Task 1:** Creates `test_docling.py` with upload/page limit/error tests
- **Plan 02-03 Task 1:** Creates `test_rbac.py` with admin/user access tests
- **conftest.py:** Created as needed with fixtures for mock Redis, test DB
- **pyproject.toml:** pytest-asyncio config added during first test task

*Each TDD task creates tests first, then implements to pass them.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Progress UX shows spinner | DOC-01 | Visual UX verification | Upload PDF, observe "Extracting text..." status in UI |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or inline test creation
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Test infrastructure created inline during TDD tasks
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-09
