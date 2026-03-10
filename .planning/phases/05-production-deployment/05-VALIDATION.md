---
phase: 05
slug: production-deployment
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-10
updated: 2026-03-10
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + curl/az CLI validation (infra) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && pytest tests/ -q --tb=short` |
| **Full suite command** | `cd backend && pytest tests/ -v && ./scripts/validate-azure.sh` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/ -q --tb=short`
- **After every plan wave:** Run `cd backend && pytest tests/ -v && ./scripts/validate-azure.sh`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-00-01 | 00 | 0 | INFRA-02 | infra | `test -x scripts/validate-azure.sh` | scripts/validate-azure.sh | pending |
| 05-00-02 | 00 | 0 | INFRA-02 | infra | `test -x scripts/test-e2e-flow.sh` | scripts/test-e2e-flow.sh | pending |
| 05-01-01 | 01 | 1 | INFRA-02 | infra | `grep -q "containerapp env create" infra/scripts/azure-setup.sh` | infra/scripts/azure-setup.sh | pending |
| 05-01-02 | 01 | 1 | INFRA-02 | infra | `grep -q "containerapp create" infra/scripts/azure-deploy.sh` | infra/scripts/azure-deploy.sh | pending |
| 05-01-03 | 01 | 1 | INFRA-02 | infra | `./scripts/validate-azure.sh` | N/A (manual execution) | pending |
| 05-02-01 | 02 | 2 | INFRA-02 | infra | `grep -q "containerapp update" .github/workflows/deploy.yml` | .github/workflows/deploy.yml | pending |
| 05-02-02 | 02 | 2 | INFRA-02 | infra | `test -f docs/DEPLOYMENT.md` | docs/DEPLOYMENT.md | pending |
| 05-02-03 | 02 | 2 | INFRA-02 | e2e | `./scripts/test-e2e-flow.sh && ./scripts/validate-azure.sh` | N/A (uses 05-00 scripts) | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [x] `scripts/validate-azure.sh` — Azure resource validation script (Plan 05-00, Task 1)
- [x] `scripts/test-e2e-flow.sh` — E2E flow test (Plan 05-00, Task 2)
- [x] Secrets verification included in validate-azure.sh (INFRA-02 success criterion 5)

*Wave 0 plan (05-00) creates all required validation scripts before deployment plans execute.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HTTPS certificate valid | INFRA-02 | Browser trust chain | Open frontend URL in browser, verify lock icon |
| Cold start timing | INFRA-02 | Requires fresh container | Scale to 0, wait 5min, measure first request time |
| Visual UI verification | INFRA-02 | Human judgment | Open app, upload PDF, verify results display correctly |

*Most deployment verifications are automated via validate-azure.sh and test-e2e-flow.sh.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 45s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] INFRA-02 secrets verification included (Container Apps secrets, not exposed in env vars)

**Approval:** ready for execution
