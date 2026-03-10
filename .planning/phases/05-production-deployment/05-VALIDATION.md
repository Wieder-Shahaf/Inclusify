---
phase: 05
slug: production-deployment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
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
| 05-01-01 | 01 | 1 | INFRA-02 | infra | `az containerapp env show --name inclusify-env -g Group07 --query provisioningState` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | INFRA-02 | infra | `az containerapp show --name inclusify-backend -g Group07 --query provisioningState` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | INFRA-02 | infra | `az containerapp show --name inclusify-frontend -g Group07 --query provisioningState` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | INFRA-02 | e2e | `curl -f https://{frontend-fqdn}/health` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | INFRA-02 | e2e | `curl -f https://{backend-fqdn}/health` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | INFRA-02 | e2e | `./scripts/test-e2e-flow.sh` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/validate-azure.sh` — Azure resource validation script
- [ ] `scripts/test-e2e-flow.sh` — E2E flow test (upload PDF → analyze → results)
- [ ] Container Apps Environment created before deployment validation

*Infrastructure validation is command-based rather than unit-test based for this phase.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HTTPS certificate valid | INFRA-02 | Browser trust chain | Open frontend URL in browser, verify lock icon |
| Cold start timing | INFRA-02 | Requires fresh container | Scale to 0, wait 5min, measure first request time |
| Key Vault access | INFRA-02 | Secret inspection | Verify backend logs show secrets resolved, not in env vars |

*Most deployment verifications can be automated via az CLI and curl commands.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
