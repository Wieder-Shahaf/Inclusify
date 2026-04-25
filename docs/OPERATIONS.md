# Inclusify — Operations Runbook

All Azure CLI commands for managing the production deployment.
Resource Group: **Group07** | Region: **East US**

---

## Quick Reference — URLs

| Service | URL |
|---------|-----|
| Frontend | https://inclusify-frontend.ashyriver-56608625.eastus.azurecontainerapps.io |
| Backend API | https://inclusify-backend.ashyriver-56608625.eastus.azurecontainerapps.io |
| Backend Health | https://inclusify-backend.ashyriver-56608625.eastus.azurecontainerapps.io/health |
| GPU VM (SSH) | ssh azureuser@52.224.246.238 |
| PostgreSQL | inclusify-postgres.postgres.database.azure.com |
| Blob Storage | https://inclusifystorage.blob.core.windows.net |
| ACR | inclusifyacr.azurecr.io |

---

## 1. Check Status of All Resources

### Container Apps (Backend + Frontend)
```bash
az containerapp list -g Group07 --query "[].{name:name,status:properties.runningStatus}" -o table
```

### PostgreSQL
```bash
az postgres flexible-server show --name inclusify-postgres -g Group07 --query "{name:name,state:state}" -o table
```

### GPU VM
```bash
az vm show -g Group07 --name InclusifyModel --show-details --query "{name:name,powerState:powerState,publicIp:publicIps}" -o table
```

### All resources at once
```bash
az containerapp list -g Group07 --query "[].{name:name,status:properties.runningStatus}" -o table && \
az postgres flexible-server show --name inclusify-postgres -g Group07 --query "{name:name,state:state}" -o table && \
az vm show -g Group07 --name InclusifyModel --show-details --query "{name:name,powerState:powerState}" -o table
```

---

## 2. Start / Stop Resources

### Start everything (in order: DB first, then apps, then VM)
```bash
# 1. Start PostgreSQL (takes ~1 min)
az postgres flexible-server start --name inclusify-postgres -g Group07

# 2. Container Apps are always running (auto-scaled by Azure)
# They reconnect to PG automatically once it's up

# 3. Start GPU VM for LLM inference (takes ~2 min)
az vm start -g Group07 --name InclusifyModel
```

### Stop everything (saves costs — do this when not presenting/testing)
```bash
# 1. Stop GPU VM first (most expensive resource)
az vm deallocate -g Group07 --name InclusifyModel

# 2. Stop PostgreSQL
az postgres flexible-server stop --name inclusify-postgres -g Group07

# Container Apps scale to zero automatically when idle (minimal cost)
```

### Stop GPU VM only (keep backend/frontend running with rule-based fallback)
```bash
az vm deallocate -g Group07 --name InclusifyModel
```
> When VM is off, analysis still works using rule-based detection only (no LLM).

---

## 3. View Live Logs

### Backend logs (FastAPI / Uvicorn)
```bash
az containerapp logs show --name inclusify-backend -g Group07 --follow
```

### Frontend logs (Next.js)
```bash
az containerapp logs show --name inclusify-frontend -g Group07 --follow
```

### Recent logs (last N lines, no streaming)
```bash
az containerapp logs show --name inclusify-backend -g Group07 --tail 50
az containerapp logs show --name inclusify-frontend -g Group07 --tail 50
```

### GPU VM logs (SSH in, then check vLLM)
```bash
ssh azureuser@52.224.246.238
# Once connected:
journalctl -f                    # All system logs
# Or check vLLM process directly:
ps aux | grep vllm               # Check if vLLM is running
```

### PostgreSQL logs
```bash
az postgres flexible-server log list --server-name inclusify-postgres -g Group07
```

---

## 4. Deploy New Version

### Automatic (CI/CD)
Push to `main` branch → GitHub Actions builds images → prints deploy commands.

### Manual deploy after CI builds
```bash
# Get the image tag from the GitHub Actions output, then:
az containerapp update --name inclusify-backend -g Group07 \
  --image inclusifyacr.azurecr.io/inclusify-backend:<TAG>

az containerapp update --name inclusify-frontend -g Group07 \
  --image inclusifyacr.azurecr.io/inclusify-frontend:<TAG>
```

### Check which image is currently running
```bash
az containerapp revision list --name inclusify-backend -g Group07 \
  --query "[?properties.trafficWeight > \`0\`].{name:name,image:properties.template.containers[0].image}" -o table

az containerapp revision list --name inclusify-frontend -g Group07 \
  --query "[?properties.trafficWeight > \`0\`].{name:name,image:properties.template.containers[0].image}" -o table
```

### Build images manually (without GitHub Actions)
```bash
# Backend
az acr build --registry inclusifyacr -g Group07 \
  --image inclusify-backend:manual \
  --file backend/Dockerfile backend/

# Frontend
az acr build --registry inclusifyacr -g Group07 \
  --image inclusify-frontend:manual \
  --file frontend/Dockerfile frontend/ \
  --build-arg NEXT_PUBLIC_API_URL=https://inclusify-backend.ashyriver-56608625.eastus.azurecontainerapps.io \
  --build-arg NEXT_PUBLIC_USE_DEMO_MODE=false
```

---

## 5. Blob Storage Operations

Storage account `inclusifystorage` (Standard LRS, eastus) holds all original uploaded files and extracted text.

### Check storage account
```bash
az storage account show --name inclusifystorage -g Group07 --query "{name:name,location:primaryLocation,status:statusOfPrimary}" -o table
```

### List files in the texts container
```bash
CONN_STR=$(az storage account show-connection-string --name inclusifystorage -g Group07 --query connectionString -o tsv)
az storage blob list --container-name texts --connection-string "$CONN_STR" --query "[].{name:name,size:properties.contentLength}" -o table
```

### Download a specific file
```bash
CONN_STR=$(az storage account show-connection-string --name inclusifystorage -g Group07 --query connectionString -o tsv)
az storage blob download \
  --container-name texts \
  --name "files/<sha256>.<ext>" \
  --file ./downloaded_file \
  --connection-string "$CONN_STR"
```

### File layout in the `texts` container
| Path | Content |
|------|---------|
| `files/{sha256}.pdf` | Original uploaded PDF |
| `files/{sha256}.docx` | Original uploaded DOCX |
| `files/{sha256}.pptx` | Original uploaded PPTX |
| `{sha256}.txt` | Extracted plain text |

### Update connection string on backend (if storage key rotated)
```bash
CONN_STR=$(az storage account show-connection-string --name inclusifystorage -g Group07 --query connectionString -o tsv)
az containerapp update --name inclusify-backend -g Group07 \
  --set-env-vars "AZURE_STORAGE_CONNECTION_STRING=$CONN_STR"
```

---

## 6. Database Operations

### Connect to PostgreSQL
```bash
PGPASSWORD='<password>' psql \
  -h inclusify-postgres.postgres.database.azure.com \
  -U inclusifyadmin \
  -d inclusify
```
> DB password is stored in container app secret `db-password`. Retrieve with:
> ```bash
> az containerapp secret show --name inclusify-backend -g Group07 --secret-name db-password --query "value" -o tsv
> ```

### Apply schema
```bash
PGPASSWORD='<password>' psql \
  -h inclusify-postgres.postgres.database.azure.com \
  -U inclusifyadmin \
  -d inclusify \
  -f db/schema.sql
```

### Apply seed data
```bash
PGPASSWORD='<password>' psql \
  -h inclusify-postgres.postgres.database.azure.com \
  -U inclusifyadmin \
  -d inclusify \
  -f db/seed.sql
```

### Quick DB queries
```bash
# Check users
PGPASSWORD='<password>' psql -h inclusify-postgres.postgres.database.azure.com -U inclusifyadmin -d inclusify \
  -c "SELECT email, role, org_id FROM users;"

# Check recent analyses
PGPASSWORD='<password>' psql -h inclusify-postgres.postgres.database.azure.com -U inclusifyadmin -d inclusify \
  -c "SELECT d.created_at, ar.status, ar.model_version, ar.runtime_ms FROM documents d JOIN analysis_runs ar ON ar.document_id = d.document_id ORDER BY d.created_at DESC LIMIT 10;"

# Check findings
PGPASSWORD='<password>' psql -h inclusify-postgres.postgres.database.azure.com -U inclusifyadmin -d inclusify \
  -c "SELECT category, severity, excerpt_redacted FROM findings ORDER BY created_at DESC LIMIT 10;"

# Promote a user to admin
PGPASSWORD='<password>' psql -h inclusify-postgres.postgres.database.azure.com -U inclusifyadmin -d inclusify \
  -c "UPDATE users SET role = 'site_admin' WHERE email = 'user@example.com';"
```

---

## 7. Environment Variables & Secrets

### View all backend env vars
```bash
az containerapp show --name inclusify-backend -g Group07 \
  --query "properties.template.containers[0].env[].{name:name,value:value,secretRef:secretRef}" -o table
```

### View all frontend env vars
```bash
az containerapp show --name inclusify-frontend -g Group07 \
  --query "properties.template.containers[0].env[].{name:name,value:value}" -o table
```

### Set a new env var
```bash
az containerapp update --name inclusify-backend -g Group07 \
  --set-env-vars MY_VAR=my_value
```

### Set a new secret + env var
```bash
# 1. Create the secret
az containerapp secret set --name inclusify-backend -g Group07 \
  --secrets my-secret=the-secret-value

# 2. Link env var to secret
az containerapp update --name inclusify-backend -g Group07 \
  --set-env-vars MY_SECRET=secretref:my-secret
```

### Current secrets reference

| Env Var | Secret Name | Description |
|---------|-------------|-------------|
| PGPASSWORD | db-password | PostgreSQL password |
| JWT_SECRET | jwt-secret | JWT signing key |
| GOOGLE_CLIENT_ID | google-client-id | Google OAuth client ID |
| GOOGLE_CLIENT_SECRET | google-client-secret | Google OAuth client secret |

---

## 8. Troubleshooting

### Backend returns 503 "Database not available"
PostgreSQL is stopped. Start it:
```bash
az postgres flexible-server start --name inclusify-postgres -g Group07
```

### Analysis returns "rules_only" mode (no LLM)
GPU VM is off. Start it:
```bash
az vm start -g Group07 --name InclusifyModel
```
Then SSH in and verify vLLM is running:
```bash
ssh azureuser@52.224.246.238
curl http://localhost:8001/v1/models
```

### Container app stuck / not responding
Force a new revision:
```bash
az containerapp revision restart --name inclusify-backend -g Group07 \
  --revision <revision-name>
```
Or redeploy the same image:
```bash
az containerapp update --name inclusify-backend -g Group07 \
  --set-env-vars DEPLOY_TS=$(date +%s)
```

### Check GitHub Actions CI status
```bash
gh run list --workflow CI --branch main --limit 5
gh run list --workflow "Build & Deploy" --branch main --limit 5
```

### View failed CI logs
```bash
gh run view <RUN_ID> --log-failed
```

---

## 9. Cost Management

**Most expensive resources (stop when not in use):**

| Resource | ~Cost/hr | Stop Command |
|----------|----------|--------------|
| GPU VM (NC4as T4 v3) | ~$0.53/hr | `az vm deallocate -g Group07 --name InclusifyModel` |
| PostgreSQL (B1ms) | ~$0.02/hr | `az postgres flexible-server stop --name inclusify-postgres -g Group07` |
| Container Apps | ~$0.01/hr | Auto-scales to near-zero |

**Before a demo/presentation:**
```bash
az postgres flexible-server start --name inclusify-postgres -g Group07
az vm start -g Group07 --name InclusifyModel
# Wait ~2 minutes for everything to boot
curl https://inclusify-backend.ashyriver-56608625.eastus.azurecontainerapps.io/health
```

**After a demo/presentation:**
```bash
az vm deallocate -g Group07 --name InclusifyModel
az postgres flexible-server stop --name inclusify-postgres -g Group07
```

---

## Architecture Quick Reference

```
Browser → Frontend (Next.js, Container App)
       → Backend (FastAPI, Container App)
           → PostgreSQL (Azure Flexible Server)
           → GPU VM (vLLM + LoRA adapter, private IP 10.0.0.4:8001)
           → Redis (refresh tokens)
           → Google OAuth2
```

All resources in VNET. Backend talks to GPU VM via private IP (10.0.0.4:8001).
Container Apps connect to PostgreSQL via public FQDN with SSL.
