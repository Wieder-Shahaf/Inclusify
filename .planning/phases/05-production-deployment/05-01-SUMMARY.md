---
phase: 05-production-deployment
plan: 01
subsystem: infra
tags: [azure, container-apps, vnet, docker, deployment]

# Dependency graph
requires:
  - phase: 05-00
    provides: Validation and E2E test scripts
  - phase: 05.1
    provides: Azure infrastructure (ACR, PostgreSQL, resource group)
provides:
  - Azure Container Apps deployment scripts (setup + deploy)
  - Running frontend and backend containers on Azure with HTTPS
  - VNet integration between Container Apps and vLLM VM
  - CORS configuration for frontend-backend communication
affects: [05-02, production-verification]

# Tech tracking
tech-stack:
  added: [azure-container-apps, vnet-subnet-delegation]
  patterns: [idempotent-deployment, secretref-pattern, cross-resource-group-vnet]

key-files:
  created:
    - infra/scripts/azure-deploy.sh
  modified:
    - infra/scripts/azure-setup.sh

key-decisions:
  - "Added --platform linux/amd64 to docker build commands for ARM Mac compatibility"
  - "Container Apps Environment in inclusify-rg referencing VNet subnet in Group07 by resource ID"
  - "Secrets stored via Container Apps secrets with secretref: pattern (not env vars)"
  - "minReplicas=1 to prevent cold starts for April 15 demo"

patterns-established:
  - "Cross-resource-group VNet: reference subnets by full resource ID across groups"
  - "Container Apps secrets: use secretref: prefix for sensitive env vars"
  - "Idempotent deploy: check if app exists before create vs update"

requirements-completed: [INFRA-02]

# Metrics
duration: manual (multi-session with human deployment)
completed: 2026-03-18
---

# Phase 5 Plan 01: Azure Container Apps Deployment Summary

**Frontend and backend deployed to Azure Container Apps with VNet integration to vLLM VM, PostgreSQL connectivity, and CORS — accessible at public HTTPS URLs**

## Performance

- **Duration:** Multi-session (scripting + manual deployment with human action checkpoint)
- **Tasks:** 3/3 complete
- **Files modified:** 2

## Accomplishments
- Extended azure-setup.sh with Container Apps Environment creation, subnet delegation in vLLM VNet, and PostgreSQL firewall rules
- Created azure-deploy.sh with idempotent Container Apps deployment for frontend and backend
- Both containers deployed and accessible at HTTPS URLs (*.azurecontainerapps.io)
- Backend connected to PostgreSQL (inclusify-db.postgres.database.azure.com) and vLLM (10.0.1.4:8001) via VNet
- Secrets managed via Container Apps secrets (db-password, jwt-secret) — not exposed in env vars

## Task Commits

1. **Task 1: Extend azure-setup.sh with Container Apps Environment** - (committed as part of azure-setup.sh updates)
2. **Task 2: Create azure-deploy.sh deployment script** - `535a99f` (feat/fix)
3. **Task 3: Run deployment scripts** - Human action checkpoint (deployment executed by user)

## Files Created/Modified
- `infra/scripts/azure-setup.sh` - Extended with Container Apps Environment, subnet delegation, PostgreSQL firewall rules
- `infra/scripts/azure-deploy.sh` - New deployment script: build, push, deploy/update Container Apps with secrets and health probes

## Deployment Details

| Resource | URL / Address |
|----------|--------------|
| Frontend | https://inclusify-frontend.ashyriver-56608625.eastus.azurecontainerapps.io |
| Backend | https://inclusify-backend.ashyriver-56608625.eastus.azurecontainerapps.io |
| PostgreSQL | inclusify-db.postgres.database.azure.com |
| vLLM (private) | http://10.0.1.4:8001 |
| VNet | InclusifyModel-vnet / containerapps-subnet |
| Static IP | 20.72.135.82 |

## Decisions Made
- Added `--platform linux/amd64` to docker build commands (ARM Mac produces incompatible images for Azure Linux containers)
- Container Apps Environment placed in inclusify-rg but references VNet subnet in Group07 by full resource ID
- Secrets use Container Apps native secrets with `secretref:` pattern per INFRA-02 success criteria
- minReplicas=1 to prevent cold starts before April 15 demo

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added --platform linux/amd64 to docker build**
- **Found during:** Task 3 (deployment execution)
- **Issue:** Docker images built on ARM Mac were incompatible with Azure Container Apps (linux/amd64)
- **Fix:** Added `--platform linux/amd64` flag to both docker build commands in azure-deploy.sh
- **Files modified:** infra/scripts/azure-deploy.sh
- **Committed in:** 535a99f

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for cross-platform Docker builds. No scope creep.

## Issues Encountered
- ARM Mac Docker builds produce images incompatible with Azure Container Apps — resolved by adding `--platform linux/amd64`

## User Setup Required
None - deployment completed via human action checkpoint.

## Next Phase Readiness
- Container Apps running and accessible — ready for CI/CD setup (05-02)
- E2E test script (scripts/test-e2e-flow.sh) can now run against live URLs
- Validation script (scripts/validate-azure.sh) confirms all resources properly configured

---
*Phase: 05-production-deployment*
*Completed: 2026-03-18*
