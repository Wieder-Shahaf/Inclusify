---
phase: 1
slug: infrastructure-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (to be installed in Wave 0) |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest backend/tests/ -x -q` |
| **Full suite command** | `pytest backend/tests/ -v --tb=short` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose build && docker compose up -d --wait && curl -f http://localhost:8000/health`
- **After every plan wave:** Run `pytest backend/tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INFRA-01 | integration | `docker compose build` | N/A (compose) | ⬜ pending |
| 01-01-02 | 01 | 1 | INFRA-01 | integration | `docker compose up -d --wait` | N/A (compose) | ⬜ pending |
| 01-02-01 | 02 | 1 | DB-01 | unit | `pytest backend/tests/test_db_pool.py -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | DB-01 | integration | `curl -f http://localhost:8000/health` | N/A (curl) | ⬜ pending |
| 01-02-03 | 02 | 1 | DB-01 | unit | `pytest backend/tests/test_repository.py -x` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | INFRA-02 | manual | `az acr login && docker push` | N/A (manual) | ⬜ pending |
| 01-03-02 | 03 | 2 | INFRA-02 | manual | `psql` connection test | N/A (manual) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/` — directory structure
- [ ] `backend/tests/conftest.py` — shared fixtures (test pool, mock app)
- [ ] `backend/tests/test_db_pool.py` — pool creation, acquire/release tests
- [ ] `backend/tests/test_health.py` — health endpoint validation
- [ ] `backend/pyproject.toml` — pytest configuration
- [ ] `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `httpx>=0.26.0` in requirements.txt

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ACR accepts image push | INFRA-02 | Requires Azure credentials | 1. `az acr login --name inclusifyacr` 2. `docker push inclusifyacr.azurecr.io/backend:latest` 3. Verify in Azure Portal |
| Azure PostgreSQL accessible | INFRA-02 | External cloud resource | 1. `psql "host=inclusify-db.postgres.database.azure.com ..."` 2. Run `SELECT 1` 3. Verify connection succeeds |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
