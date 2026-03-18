# Phase 5: Production Deployment - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy frontend and backend to Azure Container Apps, connect to vLLM VM, and make the application accessible via public HTTPS URL for E2E demo. This phase delivers:
- Container Apps deployment for frontend and backend
- Network connectivity between backend and vLLM VM
- PostgreSQL firewall configuration for Container Apps
- GitHub Actions CI/CD pipeline for automated deployments
- Public HTTPS URLs with Azure-managed certificates

</domain>

<decisions>
## Implementation Decisions

### Secrets Management
- Storage: Azure Container Apps secrets (not Key Vault). Simpler setup, sufficient for academic project. Aligns with Phase 1 decision.
- Population: Manual one-time setup via `az containerapp secret set`. Document required secrets in README.
- Separation: Only secrets (passwords, keys) go in Container Apps secrets. Non-secret config (URLs, feature flags) goes in regular environment variables.
- Secret inventory: Claude's discretion based on what codebase actually uses.

### Deployment Strategy
- Method: Direct replacement. New image replaces old container. Brief downtime acceptable for academic demo.
- Rollback: Manual revert to previous image tag. No automatic rollback.
- CI/CD: GitHub Actions workflow triggered on push to main branch. Automatic deployment after merge.
- Trigger: Push to main only. No tag-based releases or manual triggers needed.

### Network Topology
- vLLM access: VNet integration. Container Apps Environment shares VNet with vLLM VM. Backend reaches vLLM via private IP.
- Container Apps: Frontend and backend in same Container Apps Environment. Simplified networking, shared VNet.
- PostgreSQL: Public access with firewall rules. Only Container Apps Environment IPs allowed. Works with student Azure accounts.

### Domain & HTTPS
- Domain: Azure-provided URL (*.azurecontainerapps.io). Free, automatic HTTPS, sufficient for demo.
- Certificates: Azure-managed certificates. Zero configuration.
- Backend exposure: Public URL with CORS. Frontend calls backend directly at separate Container Apps URL.
- HTTPS enforcement: Yes, HTTP redirects to HTTPS.

### Claude's Discretion
- Specific Container Apps scaling settings (minReplicas, maxReplicas)
- GitHub Actions workflow structure and secrets naming
- VNet address space and subnet configuration
- Health probe configuration and timeouts
- Resource naming conventions in Azure

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `infra/scripts/azure-setup.sh`: Provisions Resource Group, ACR, PostgreSQL. Idempotent, ready to extend.
- `infra/scripts/azure-push.sh`: Tags and pushes Docker images to ACR. Ready to use.
- `infra/docker/backend.Dockerfile`: Multi-stage build for FastAPI backend.
- `infra/docker/frontend.Dockerfile`: Multi-stage build for Next.js frontend.
- `infra/docker/docker-compose.yml`: Local dev compose with profiles.
- `infra/azure/vllm-vm/`: vLLM VM setup scripts, systemd service file.

### Established Patterns
- Azure CLI scripts (`az` commands in bash) for infrastructure provisioning (Phase 1)
- Idempotent provisioning with `|| echo "already exists"` pattern
- Container Apps secrets for sensitive values (Phase 1 decision)
- CORS via ALLOWED_ORIGINS environment variable (Phase 4)
- Non-root containers: appuser (backend), nextjs (frontend)

### Integration Points
- `backend/app/main.py`: CORS configuration reads ALLOWED_ORIGINS env var
- `infra/scripts/azure-setup.sh`: Extend with Container Apps Environment and App creation
- New files needed: GitHub Actions workflow (`.github/workflows/deploy.yml`)
- New files needed: Container Apps deployment script (`infra/scripts/azure-deploy.sh`)

</code_context>

<specifics>
## Specific Ideas

- GitHub Actions on push to main — professional workflow, team already uses GitHub
- VNet integration keeps vLLM private while allowing Container Apps access
- Azure-provided URLs are sufficient for academic demo — no custom domain complexity
- Same Container Apps Environment for frontend/backend simplifies networking
- PostgreSQL public access with firewall is pragmatic for student Azure accounts

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-production-deployment*
*Context gathered: 2026-03-10*
