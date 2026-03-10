# Phase 5: Production Deployment - Research

**Researched:** 2026-03-10
**Domain:** Azure Container Apps deployment, VNet integration, GitHub Actions CI/CD
**Confidence:** HIGH

## Summary

Phase 5 deploys the Inclusify frontend and backend to Azure Container Apps with VNet integration to the existing vLLM VM. The project has existing infrastructure scaffolding (ACR, PostgreSQL, Dockerfiles, azure-setup.sh) that needs extension for Container Apps.

Key deployment architecture:
- Container Apps Environment with VNet integration (shares VNet with vLLM VM)
- Frontend and backend as separate Container Apps in same environment
- VNet integration enables backend to reach vLLM via private IP
- GitHub Actions workflow for CI/CD on push to main
- Secrets via Container Apps secrets (not Key Vault per user decision)
- Azure-provided HTTPS URLs (*.azurecontainerapps.io)

**Primary recommendation:** Extend existing `azure-setup.sh` with Container Apps Environment creation and add `azure-deploy.sh` for container app deployment. Use `azure/container-apps-deploy-action@v1` in GitHub Actions with service principal authentication.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Secrets Management: Azure Container Apps secrets (not Key Vault). Simpler setup, sufficient for academic project.
- Population: Manual one-time setup via `az containerapp secret set`. Document required secrets in README.
- Separation: Only secrets (passwords, keys) go in Container Apps secrets. Non-secret config (URLs, feature flags) goes in regular environment variables.
- Deployment Strategy: Direct replacement. New image replaces old container. Brief downtime acceptable.
- Rollback: Manual revert to previous image tag. No automatic rollback.
- CI/CD: GitHub Actions workflow triggered on push to main branch.
- VNet access: Container Apps Environment shares VNet with vLLM VM. Backend reaches vLLM via private IP.
- Container Apps: Frontend and backend in same Container Apps Environment.
- PostgreSQL: Public access with firewall rules. Only Container Apps Environment IPs allowed.
- Domain: Azure-provided URL (*.azurecontainerapps.io). Free, automatic HTTPS.
- Certificates: Azure-managed certificates.
- Backend exposure: Public URL with CORS. Frontend calls backend directly at separate Container Apps URL.
- HTTPS enforcement: Yes, HTTP redirects to HTTPS.

### Claude's Discretion
- Specific Container Apps scaling settings (minReplicas, maxReplicas)
- GitHub Actions workflow structure and secrets naming
- VNet address space and subnet configuration
- Health probe configuration and timeouts
- Resource naming conventions in Azure

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-02 | Azure deployment (containers + managed PostgreSQL) | Container Apps deployment patterns, VNet integration commands, GitHub Actions workflow templates, health probe configuration |

</phase_requirements>

## Standard Stack

### Core Azure Resources
| Resource | Configuration | Purpose | Why Standard |
|----------|---------------|---------|--------------|
| Container Apps Environment | Workload profiles, VNet integrated | Hosts container apps | Required for VNet access to vLLM VM |
| Container App (Backend) | minReplicas=1, maxReplicas=3 | FastAPI backend | Prevents cold start (PITFALLS.md #11) |
| Container App (Frontend) | minReplicas=1, maxReplicas=3 | Next.js frontend | Prevents cold start (PITFALLS.md #11) |
| VNet Subnet | /27 CIDR, delegated to Microsoft.App/environments | Container Apps networking | Minimum size for workload profiles environment |

### CI/CD Stack
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| GitHub Actions | N/A | CI/CD pipeline | Team uses GitHub, existing CI workflow |
| azure/login@v1 | 1.x | Azure authentication | Official action |
| azure/container-apps-deploy-action@v1 | 1.x | Deploy to Container Apps | Official action, builds and deploys |
| Service Principal | N/A | GitHub to Azure auth | Simpler than OIDC for academic project |

### Existing Resources (from Phase 1)
| Resource | Configuration | Status |
|----------|---------------|--------|
| Azure Container Registry (ACR) | inclusifyacr, Basic SKU | Provisioned |
| PostgreSQL Flexible Server | B1ms, public access | Provisioned |
| Resource Group | inclusify-rg | Provisioned |
| vLLM VM | Standard_NC4as_T4_v3, VNet: InclusifyModel-vnet | Provisioned (Group07) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Service Principal | OIDC Federated Identity | OIDC more secure but more setup, overkill for academic demo |
| Container Apps secrets | Azure Key Vault | Key Vault better for audit/rotation but adds complexity |
| Direct replacement deploy | Blue-green deployment | Zero downtime but requires 2x resources, unnecessary for demo |

## Architecture Patterns

### Recommended Project Structure (additions)
```
infra/
  scripts/
    azure-setup.sh        # Existing - extend with Container Apps Environment
    azure-deploy.sh       # NEW - deploy/update container apps
    azure-push.sh         # Existing - push images to ACR
  azure/
    vllm-vm/              # Existing - vLLM VM setup
.github/
  workflows/
    ci.yml                # Existing - sanity checks
    deploy.yml            # NEW - deployment workflow
```

### Pattern 1: VNet-Integrated Container Apps Environment
**What:** Create Container Apps Environment in same VNet as vLLM VM
**When to use:** When containers need to access private resources (vLLM VM)
**Example:**
```bash
# Source: https://learn.microsoft.com/en-us/azure/container-apps/vnet-custom

# Delegate subnet to Container Apps
az network vnet subnet update \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $SUBNET_NAME \
  --delegations Microsoft.App/environments

# Create environment with VNet
az containerapp env create \
  --name $CONTAINERAPPS_ENVIRONMENT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --infrastructure-subnet-resource-id $INFRASTRUCTURE_SUBNET
```

### Pattern 2: Container Apps Secrets
**What:** Store sensitive values as Container Apps secrets, reference in env vars
**When to use:** For database passwords, JWT secrets, API keys
**Example:**
```bash
# Source: https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets

# Set secrets
az containerapp secret set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --secrets "db-password=$PG_PASSWORD" "jwt-secret=$JWT_SECRET"

# Reference in environment variables (during create/update)
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENVIRONMENT \
  --image $IMAGE \
  --env-vars "PGPASSWORD=secretref:db-password" "JWT_SECRET=secretref:jwt-secret"
```

### Pattern 3: GitHub Actions Deployment
**What:** Build, push to ACR, deploy to Container Apps
**When to use:** On push to main branch
**Example:**
```yaml
# Source: https://learn.microsoft.com/en-us/azure/container-apps/github-actions
name: Deploy to Azure Container Apps

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Log in to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and deploy Backend
        uses: azure/container-apps-deploy-action@v1
        with:
          appSourcePath: ${{ github.workspace }}
          dockerfilePath: infra/docker/backend.Dockerfile
          acrName: inclusifyacr
          containerAppName: inclusify-backend
          resourceGroup: inclusify-rg
          imageToDeploy: inclusifyacr.azurecr.io/inclusify-backend:${{ github.sha }}
```

### Pattern 4: Health Probes for ML Backends
**What:** Configure startup probe with longer timeout for model loading
**When to use:** Applications with slow startup (vLLM, Docling)
**Example:**
```bash
# Source: https://learn.microsoft.com/en-us/azure/container-apps/health-probes

az containerapp create \
  --name $APP_NAME \
  ... \
  --startup-probe-path /health \
  --startup-probe-initial-delay 10 \
  --startup-probe-period 5 \
  --startup-probe-timeout 3 \
  --startup-probe-failure-threshold 30
```

### Anti-Patterns to Avoid
- **Deploying without VNet integration:** Backend cannot reach vLLM VM without shared VNet
- **Using minReplicas=0:** Causes cold start delays for first request (PITFALLS.md #11)
- **Hardcoding secrets in Dockerfiles:** Exposes credentials in image layers
- **Skipping health probes:** Container may receive traffic before ready
- **Using `latest` tag in deployment:** Causes caching issues, use commit SHA

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Container deployment | Custom az CLI scripts | azure/container-apps-deploy-action | Handles build, push, deploy atomically |
| SSL certificates | Manual cert management | Azure-managed certificates | Auto-renewal, zero config |
| Image tagging | Manual version numbers | Git commit SHA (${{ github.sha }}) | Unique, traceable, no conflicts |
| Secrets in CI | Environment variables in workflow | GitHub encrypted secrets | Secure, auditable |
| VNet routing | Custom route tables | Container Apps VNet integration | Automatic DNS resolution |

**Key insight:** Azure Container Apps handles most networking, scaling, and SSL complexity automatically. Focus on configuration, not infrastructure code.

## Common Pitfalls

### Pitfall 1: VNet Subnet Too Small
**What goes wrong:** Container Apps Environment creation fails with "subnet CIDR too small"
**Why it happens:** Workload profiles environment requires minimum /27 subnet
**How to avoid:** Use /27 or larger CIDR for infrastructure subnet
**Warning signs:** `az containerapp env create` fails with subnet error

### Pitfall 2: Subnet Not Delegated
**What goes wrong:** Environment creation fails with delegation error
**Why it happens:** Forgot to delegate subnet to Microsoft.App/environments
**How to avoid:** Run `az network vnet subnet update --delegations Microsoft.App/environments` before env creation
**Warning signs:** Error mentioning "subnet delegation required"

### Pitfall 3: Cold Start Delays (PITFALLS.md #11)
**What goes wrong:** First request after idle period times out
**Why it happens:** minReplicas=0 causes container to scale to zero
**How to avoid:** Set minReplicas=1 for both frontend and backend
**Warning signs:** 30-60 second delays on first request after period of inactivity

### Pitfall 4: CORS Not Configured (PITFALLS.md #7)
**What goes wrong:** Frontend cannot call backend, 403 errors in browser
**Why it happens:** Backend ALLOWED_ORIGINS doesn't include frontend URL
**How to avoid:** Add frontend Container Apps URL to ALLOWED_ORIGINS env var
**Warning signs:** Browser console shows "CORS policy" errors

### Pitfall 5: Service Principal Credentials Expired
**What goes wrong:** GitHub Actions deployment fails with auth error
**Why it happens:** Service principal credentials have default 1-year expiry
**How to avoid:** Note expiry date, set reminder to rotate
**Warning signs:** Deployment worked before, now fails with "invalid_client" or auth errors

### Pitfall 6: PostgreSQL Firewall Blocks Container Apps
**What goes wrong:** Backend cannot connect to database
**Why it happens:** Container Apps outbound IPs not in PostgreSQL firewall rules
**How to avoid:** Add Container Apps Environment outbound IPs to firewall, or use VNet service endpoints
**Warning signs:** Connection timeout errors in backend logs

### Pitfall 7: Image Tag Caching Issues
**What goes wrong:** New deployment doesn't pick up code changes
**Why it happens:** Using `latest` tag, ACR serves cached image
**How to avoid:** Use unique tags like git commit SHA
**Warning signs:** Code changes not reflected after deployment

## Code Examples

Verified patterns from official sources:

### Create Service Principal for GitHub Actions
```bash
# Source: https://learn.microsoft.com/en-us/azure/container-apps/github-actions

# Create SP with Contributor role on resource group
az ad sp create-for-rbac \
  --name "inclusify-github-deploy" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/inclusify-rg \
  --json-auth \
  --output json

# Save output as AZURE_CREDENTIALS GitHub secret
```

### Container Apps Environment with VNet
```bash
# Source: https://learn.microsoft.com/en-us/azure/container-apps/vnet-custom

# Variables (matching existing infrastructure)
RESOURCE_GROUP="inclusify-rg"
LOCATION="eastus"
VLLM_VNET="InclusifyModel-vnet"
VLLM_RG="Group07"
CONTAINERAPPS_ENV="inclusify-env"
SUBNET_NAME="containerapps-subnet"

# Create subnet in existing vLLM VNet (need /27 for workload profiles)
az network vnet subnet create \
  --resource-group $VLLM_RG \
  --vnet-name $VLLM_VNET \
  --name $SUBNET_NAME \
  --address-prefixes 10.0.2.0/27 \
  --delegations Microsoft.App/environments

# Get subnet ID
INFRASTRUCTURE_SUBNET=$(az network vnet subnet show \
  --resource-group $VLLM_RG \
  --vnet-name $VLLM_VNET \
  --name $SUBNET_NAME \
  --query id -o tsv)

# Create Container Apps Environment
az containerapp env create \
  --name $CONTAINERAPPS_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --infrastructure-subnet-resource-id $INFRASTRUCTURE_SUBNET
```

### Deploy Backend Container App
```bash
# Source: https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets

ACR_NAME="inclusifyacr"
APP_NAME="inclusify-backend"
IMAGE_TAG="latest"  # Use $GIT_SHA in CI

az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENV \
  --image "${ACR_NAME}.azurecr.io/inclusify-backend:${IMAGE_TAG}" \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --secrets "db-password=$PG_PASSWORD" "jwt-secret=$JWT_SECRET" "redis-password=$REDIS_PASSWORD" \
  --env-vars \
    "PGHOST=inclusify-db.postgres.database.azure.com" \
    "PGPORT=5432" \
    "PGDATABASE=inclusify" \
    "PGUSER=inclusifyadmin" \
    "PGPASSWORD=secretref:db-password" \
    "PGSSL=require" \
    "JWT_SECRET=secretref:jwt-secret" \
    "VLLM_URL=http://10.0.1.4:8001" \
    "ALLOWED_ORIGINS=https://inclusify-frontend.azurecontainerapps.io"
```

### Deploy Frontend Container App
```bash
# Frontend needs backend URL at build time for Next.js
BACKEND_URL=$(az containerapp show \
  --name inclusify-backend \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

az containerapp create \
  --name inclusify-frontend \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENV \
  --image "${ACR_NAME}.azurecr.io/inclusify-frontend:${IMAGE_TAG}" \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --target-port 3000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars "NEXT_PUBLIC_API_URL=https://${BACKEND_URL}"
```

### GitHub Actions Workflow Structure
```yaml
# Source: https://learn.microsoft.com/en-us/azure/container-apps/github-actions
# .github/workflows/deploy.yml

name: Deploy to Azure

on:
  push:
    branches: [main]

env:
  RESOURCE_GROUP: inclusify-rg
  ACR_NAME: inclusifyacr
  CONTAINERAPPS_ENV: inclusify-env

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Log in to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Log in to ACR
        run: az acr login --name ${{ env.ACR_NAME }}

      - name: Build and push Backend
        run: |
          docker build \
            -f infra/docker/backend.Dockerfile \
            --target runtime \
            --build-arg GIT_COMMIT=${{ github.sha }} \
            --build-arg BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
            -t ${{ env.ACR_NAME }}.azurecr.io/inclusify-backend:${{ github.sha }} \
            .
          docker push ${{ env.ACR_NAME }}.azurecr.io/inclusify-backend:${{ github.sha }}

      - name: Deploy Backend
        run: |
          az containerapp update \
            --name inclusify-backend \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --image ${{ env.ACR_NAME }}.azurecr.io/inclusify-backend:${{ github.sha }}

      # Similar steps for frontend...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Docker Compose on VM | Container Apps | 2022 | Managed scaling, SSL, networking |
| Manual deployments | GitHub Actions CI/CD | Standard | Automated, traceable |
| AKS for simple apps | Container Apps | 2023 | Less ops overhead |
| Self-managed SSL | Azure-managed certs | Default | Zero maintenance |
| Service Principal secrets | OIDC federated identity | 2023 | More secure but more setup |

**Deprecated/outdated:**
- Using `--admin-enabled` for ACR in production (use managed identity instead)
- Consumption-only environment type (workload profiles preferred for VNet)

## Open Questions

1. **Container Apps outbound IP for PostgreSQL firewall**
   - What we know: Container Apps Environment has outbound IPs
   - What's unclear: Whether these IPs are stable or change on scale
   - Recommendation: After env creation, get outbound IPs via `az containerapp env show --query properties.outboundIpAddresses` and add to PostgreSQL firewall

2. **VNet peering between resource groups**
   - What we know: vLLM VM in Group07, Container Apps in inclusify-rg
   - What's unclear: Whether subnet can be created across resource groups
   - Recommendation: Create Container Apps subnet in same VNet (InclusifyModel-vnet in Group07), or peer VNets if in separate VNets

3. **Image build in GitHub Actions vs ACR Tasks**
   - What we know: Both can build images, action builds on runner
   - What's unclear: Whether ACR Tasks would be faster for ARM builds
   - Recommendation: Start with GitHub Actions runner builds (simpler), optimize later if slow

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | None (uses pytest defaults) |
| Quick run command | `cd backend && pytest tests/test_health.py -x` |
| Full suite command | `cd backend && pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| INFRA-02 | Container health endpoint responds | smoke | `curl https://$BACKEND_URL/health` | N/A (manual after deploy) |
| INFRA-02 | Frontend loads | smoke | `curl https://$FRONTEND_URL` | N/A (manual after deploy) |
| INFRA-02 | Backend can reach vLLM | integration | Requires deployed environment | N/A |
| INFRA-02 | Full E2E flow works | e2e | Manual: upload PDF, view results | manual-only |

### Sampling Rate
- **Per task commit:** N/A (infrastructure deployment, not code changes)
- **Per wave merge:** Smoke tests against deployed environment
- **Phase gate:** Full E2E demo flow works (upload PDF -> analysis -> results)

### Wave 0 Gaps
None - this phase is infrastructure deployment, not code changes. Testing is post-deployment smoke tests against live environment.

## Sources

### Primary (HIGH confidence)
- [Azure Container Apps VNet Integration](https://learn.microsoft.com/en-us/azure/container-apps/vnet-custom) - Subnet requirements, delegation, CLI commands
- [Container Apps Secrets Management](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets) - Secret creation, environment variable references
- [Container Apps Health Probes](https://learn.microsoft.com/en-us/azure/container-apps/health-probes) - Startup, liveness, readiness configuration
- [GitHub Actions for Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/github-actions) - Workflow structure, authentication

### Secondary (MEDIUM confidence)
- [Azure Container Apps Deploy Action](https://github.com/Azure/container-apps-deploy-action) - GitHub Marketplace documentation
- [OIDC Authentication for Azure](https://docs.github.com/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure) - Alternative to service principal

### Project Context (HIGH confidence)
- Existing infrastructure scripts: `infra/scripts/azure-setup.sh`, `azure-push.sh`
- Existing Dockerfiles: `infra/docker/backend.Dockerfile`, `frontend.Dockerfile`
- vLLM VM setup: `infra/azure/vllm-vm/setup.sh`
- Health endpoint: `backend/app/routers/health.py` (/health path, returns JSON)
- CORS configuration: `backend/app/main.py` (ALLOWED_ORIGINS env var)
- PITFALLS.md: Cold start (#11), CORS (#7), streaming proxy (#6)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Azure documentation, existing project patterns
- Architecture: HIGH - Based on verified VNet integration docs and existing infrastructure
- Pitfalls: HIGH - Documented in PITFALLS.md + official troubleshooting guides

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable Azure services, 30 days)
