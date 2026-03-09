---
phase: 2
slug: core-services
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.0 + pytest-asyncio 0.23.0 |
| **Config file** | none — Wave 0 installs |
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | AUTH-01 | unit | `pytest backend/tests/test_auth.py::test_register -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | AUTH-01 | unit | `pytest backend/tests/test_auth.py::test_login -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | AUTH-01 | unit | `pytest backend/tests/test_auth.py::test_invalid_token -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | AUTH-01 | unit | `pytest backend/tests/test_auth.py::test_refresh -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | DOC-01 | integration | `pytest backend/tests/test_docling.py::test_pdf_upload -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | DOC-01 | unit | `pytest backend/tests/test_docling.py::test_page_limit -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | DOC-01 | unit | `pytest backend/tests/test_docling.py::test_password_protected -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | AUTH-02 | unit | `pytest backend/tests/test_rbac.py::test_admin_access -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | AUTH-02 | unit | `pytest backend/tests/test_rbac.py::test_user_forbidden -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_auth.py` — stubs for AUTH-01 (registration, login, token, refresh)
- [ ] `backend/tests/test_rbac.py` — stubs for AUTH-02 (admin access, user forbidden)
- [ ] `backend/tests/test_docling.py` — stubs for DOC-01 (upload, page limit, password-protected)
- [ ] `backend/tests/conftest.py` — shared fixtures (mock Redis, mock Docling subprocess)
- [ ] `pyproject.toml [tool.pytest.ini_options]` — asyncio_mode = "auto"

*Wave 0 creates test infrastructure before feature implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Progress UX shows spinner | DOC-01 | Visual UX verification | Upload PDF, observe "Extracting text..." status in UI |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
