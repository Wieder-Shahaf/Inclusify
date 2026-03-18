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
| **Framework** | pytest 8.x (installed in Plan 01-03 Task 0) |
| **Config file** | none — created during execution |
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
| 01-01-01 | 01 | 1 | INFRA-01 | integration | `docker build -f infra/docker/backend.Dockerfile -t test .` | N/A (compose) | ⬜ pending |
| 01-01-02 | 01 | 1 | INFRA-01 | integration | `docker build -f infra/docker/frontend.Dockerfile -t test .` | N/A (compose) | ⬜ pending |
| 01-01-03 | 01 | 1 | INFRA-01 | integration | `docker compose config --quiet` | N/A (compose) | ⬜ pending |
| 01-02-01 | 02 | 1 | INFRA-02 | syntax | `bash -n infra/scripts/azure-setup.sh` | N/A (script) | ⬜ pending |
| 01-02-02 | 02 | 1 | INFRA-02 | syntax | `bash -n infra/scripts/azure-teardown.sh && bash -n infra/scripts/azure-push.sh` | N/A (script) | ⬜ pending |
| 01-02-03 | 02 | 1 | INFRA-02 | manual | checkpoint:human-verify (Azure Portal) | N/A (manual) | ⬜ pending |
| 01-03-00 | 03 | 2 | DB-01 | unit | `pip install pytest pytest-asyncio httpx -q` | ✅ requirements.txt | ⬜ pending |
| 01-03-01 | 03 | 2 | DB-01 | unit | `python -c "from app.db.connection import create_pool"` | N/A (import) | ⬜ pending |
| 01-03-02 | 03 | 2 | DB-01 | unit | `python -c "from app.db.deps import get_db"` | N/A (import) | ⬜ pending |
| 01-03-03 | 03 | 2 | DB-01 | unit | `pytest backend/tests/test_health.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 tasks are embedded in Plan 01-03 Task 0:

- [ ] `backend/tests/` — directory structure
- [ ] `backend/tests/conftest.py` — shared fixtures (mock pool, test client)
- [ ] `backend/tests/test_health.py` — health endpoint validation
- [ ] `backend/requirements.txt` — updated with `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `httpx>=0.26.0`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ACR accepts image push | INFRA-02 | Requires Azure credentials | 1. `az acr login --name inclusifyacr` 2. `docker push inclusifyacr.azurecr.io/backend:latest` 3. Verify in Azure Portal |
| Azure PostgreSQL accessible | INFRA-02 | External cloud resource | 1. `psql "host=inclusify-db.postgres.database.azure.com ..."` 2. Run `SELECT 1` 3. Verify connection succeeds |

---

## Requirement Coverage

| Requirement | Plans | Tasks | Coverage |
|-------------|-------|-------|----------|
| INFRA-01 | 01-01 | 01-01-01, 01-01-02, 01-01-03 | Docker builds, compose config |
| INFRA-02 | 01-02 | 01-02-01, 01-02-02, 01-02-03 | Azure scripts, human verify |
| DB-01 | 01-03 | 01-03-00, 01-03-01, 01-03-02, 01-03-03 | Pool, deps, health tests |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
