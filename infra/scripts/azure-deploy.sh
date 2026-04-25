#!/bin/bash
set -euo pipefail

# Inclusify Azure Container Apps Deployment
# Run with: ./infra/scripts/azure-deploy.sh
# Requires: az login, PG_PASSWORD, JWT_SECRET environment variables

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-Group07}"
ACR_NAME="${ACR_NAME:-inclusifyacr}"
CONTAINERAPPS_ENV="${CONTAINERAPPS_ENV:-inclusify-env}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# App names
BACKEND_APP="${BACKEND_APP:-inclusify-backend}"
FRONTEND_APP="${FRONTEND_APP:-inclusify-frontend}"

# Database — production server name in Group07
PG_SERVER="${PG_SERVER:-inclusify-postgres}"
PG_USER="${PG_USER:-inclusifyadmin}"
PG_DATABASE="${PG_DATABASE:-inclusify}"

# vLLM VM private IP (from VNet setup)
VLLM_PRIVATE_IP="${VLLM_PRIVATE_IP:-10.0.0.4}"
VLLM_PORT="${VLLM_PORT:-8001}"

# Azure Blob Storage — production account is inclusifystorage
# Get conn string: az storage account show-connection-string -g Group07 -n inclusifystorage -o tsv
AZURE_STORAGE_CONN_STR="${AZURE_STORAGE_CONN_STR:-}"
AZURE_STORAGE_CONTAINER="${AZURE_STORAGE_CONTAINER:-texts}"

# Email
SMTP_USER="${SMTP_USER:-inclusify.support@gmail.com}"
RESEND_API_KEY="${RESEND_API_KEY:-}"
SMTP_PASSWORD="${SMTP_PASSWORD:-}"

# Google OAuth
GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"

# vLLM model name as served by the vLLM instance
VLLM_MODEL_NAME="${VLLM_MODEL_NAME:-/home/azureuser/models/Qwen2.5-3B-Instruct}"

# Check for required secrets
if [ -z "${PG_PASSWORD:-}" ]; then
  echo "Error: PG_PASSWORD environment variable required"
  echo "Usage: PG_PASSWORD=<password> JWT_SECRET=<secret> AZURE_STORAGE_CONN_STR=<conn> ./infra/scripts/azure-deploy.sh"
  exit 1
fi

if [ -z "${JWT_SECRET:-}" ]; then
  echo "Error: JWT_SECRET environment variable required"
  echo "Generate with: openssl rand -base64 32"
  exit 1
fi

if [ -z "${AZURE_STORAGE_CONN_STR:-}" ]; then
  echo "Error: AZURE_STORAGE_CONN_STR required for inclusifystorage"
  echo "Get it: az storage account show-connection-string -g Group07 -n inclusifystorage -o tsv"
  exit 1
fi

if [ -z "${GOOGLE_CLIENT_ID:-}" ] || [ -z "${GOOGLE_CLIENT_SECRET:-}" ]; then
  echo "Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET required for OAuth"
  exit 1
fi

echo "=== Inclusify Container Apps Deployment ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "Container Apps Environment: $CONTAINERAPPS_ENV"
echo "Image Tag: $IMAGE_TAG"
echo ""

# Helper function to check if app exists
app_exists() {
  local app_name=$1
  az containerapp show \
    --name "$app_name" \
    --resource-group "$RESOURCE_GROUP" \
    &>/dev/null
}

# Step 1: Log into ACR
echo "[1/7] Logging into Azure Container Registry..."
az acr login --name "$ACR_NAME"

# Step 2: Build and push backend image
echo "[2/7] Building and pushing backend image..."
docker build \
  --platform linux/amd64 \
  -f infra/docker/backend.Dockerfile \
  --target runtime \
  -t "${ACR_NAME}.azurecr.io/inclusify-backend:${IMAGE_TAG}" \
  .
docker push "${ACR_NAME}.azurecr.io/inclusify-backend:${IMAGE_TAG}"

# Step 3: Build and push frontend image
echo "[3/7] Building and pushing frontend image..."
# Get backend FQDN first (needed for build arg)
BACKEND_FQDN_FOR_BUILD=""
if app_exists "$BACKEND_APP"; then
  BACKEND_FQDN_FOR_BUILD=$(az containerapp show \
    --name "$BACKEND_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
fi

docker build \
  --platform linux/amd64 \
  -f infra/docker/frontend.Dockerfile \
  --target runner \
  --build-arg NEXT_PUBLIC_API_URL="https://${BACKEND_FQDN_FOR_BUILD}" \
  -t "${ACR_NAME}.azurecr.io/inclusify-frontend:${IMAGE_TAG}" \
  .
docker push "${ACR_NAME}.azurecr.io/inclusify-frontend:${IMAGE_TAG}"

# Step 4: Deploy/update backend Container App
echo "[4/7] Deploying backend Container App..."
if app_exists "$BACKEND_APP"; then
  echo "  Backend app exists, updating..."

  # Update secrets (storage conn string stored as secret to avoid key exposure in env)
  az containerapp secret set \
    --name "$BACKEND_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --secrets \
      "db-password=$PG_PASSWORD" \
      "jwt-secret=$JWT_SECRET" \
      "google-client-id=$GOOGLE_CLIENT_ID" \
      "google-client-secret=$GOOGLE_CLIENT_SECRET" \
      "azure-storage-conn-str=$AZURE_STORAGE_CONN_STR" \
    --output none

  # Update image and environment
  az containerapp update \
    --name "$BACKEND_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --image "${ACR_NAME}.azurecr.io/inclusify-backend:${IMAGE_TAG}" \
    --set-env-vars \
      "PGHOST=${PG_SERVER}.postgres.database.azure.com" \
      "PGPORT=5432" \
      "PGDATABASE=$PG_DATABASE" \
      "PGUSER=$PG_USER" \
      "PGPASSWORD=secretref:db-password" \
      "PGSSL=require" \
      "JWT_SECRET=secretref:jwt-secret" \
      "GOOGLE_CLIENT_ID=secretref:google-client-id" \
      "GOOGLE_CLIENT_SECRET=secretref:google-client-secret" \
      "AZURE_STORAGE_CONNECTION_STRING=secretref:azure-storage-conn-str" \
      "AZURE_STORAGE_CONTAINER=$AZURE_STORAGE_CONTAINER" \
      "VLLM_URL=http://${VLLM_PRIVATE_IP}:${VLLM_PORT}" \
      "VLLM_MODEL_NAME=$VLLM_MODEL_NAME" \
      "RESEND_API_KEY=$RESEND_API_KEY" \
      "SMTP_USER=$SMTP_USER" \
      "SMTP_PASSWORD=$SMTP_PASSWORD" \
    --output none
else
  echo "  Creating new backend app..."
  az containerapp create \
    --name "$BACKEND_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINERAPPS_ENV" \
    --image "${ACR_NAME}.azurecr.io/inclusify-backend:${IMAGE_TAG}" \
    --registry-server "${ACR_NAME}.azurecr.io" \
    --target-port 8000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --secrets \
      "db-password=$PG_PASSWORD" \
      "jwt-secret=$JWT_SECRET" \
      "google-client-id=$GOOGLE_CLIENT_ID" \
      "google-client-secret=$GOOGLE_CLIENT_SECRET" \
      "azure-storage-conn-str=$AZURE_STORAGE_CONN_STR" \
    --env-vars \
      "PGHOST=${PG_SERVER}.postgres.database.azure.com" \
      "PGPORT=5432" \
      "PGDATABASE=$PG_DATABASE" \
      "PGUSER=$PG_USER" \
      "PGPASSWORD=secretref:db-password" \
      "PGSSL=require" \
      "JWT_SECRET=secretref:jwt-secret" \
      "GOOGLE_CLIENT_ID=secretref:google-client-id" \
      "GOOGLE_CLIENT_SECRET=secretref:google-client-secret" \
      "AZURE_STORAGE_CONNECTION_STRING=secretref:azure-storage-conn-str" \
      "AZURE_STORAGE_CONTAINER=$AZURE_STORAGE_CONTAINER" \
      "VLLM_URL=http://${VLLM_PRIVATE_IP}:${VLLM_PORT}" \
      "VLLM_MODEL_NAME=$VLLM_MODEL_NAME" \
      "RESEND_API_KEY=$RESEND_API_KEY" \
      "SMTP_USER=$SMTP_USER" \
      "SMTP_PASSWORD=$SMTP_PASSWORD" \
    --output none
fi

# Configure health probes for backend via YAML patch
echo "  Configuring health probes..."
PROBE_YAML=$(mktemp)
cat > "$PROBE_YAML" << 'PROBEEOF'
properties:
  template:
    containers:
      - name: inclusify-backend
        probes:
          - type: Startup
            httpGet:
              path: /
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 3
            failureThreshold: 30
          - type: Liveness
            httpGet:
              path: /health
              port: 8000
            periodSeconds: 30
PROBEEOF
az containerapp update \
  --name "$BACKEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --yaml "$PROBE_YAML" \
  --output none 2>/dev/null || echo "  Warning: Could not configure health probes via YAML (may need manual setup)"
rm -f "$PROBE_YAML"

# Get backend FQDN
BACKEND_FQDN=$(az containerapp show \
  --name "$BACKEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)
echo "  Backend URL: https://${BACKEND_FQDN}"

# Step 5: Deploy/update frontend Container App
echo "[5/7] Deploying frontend Container App..."
if app_exists "$FRONTEND_APP"; then
  echo "  Frontend app exists, updating..."
  az containerapp update \
    --name "$FRONTEND_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --image "${ACR_NAME}.azurecr.io/inclusify-frontend:${IMAGE_TAG}" \
    --set-env-vars \
      "NEXT_PUBLIC_API_URL=https://${BACKEND_FQDN}" \
    --output none
else
  echo "  Creating new frontend app..."
  az containerapp create \
    --name "$FRONTEND_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINERAPPS_ENV" \
    --image "${ACR_NAME}.azurecr.io/inclusify-frontend:${IMAGE_TAG}" \
    --registry-server "${ACR_NAME}.azurecr.io" \
    --target-port 3000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --env-vars \
      "NEXT_PUBLIC_API_URL=https://${BACKEND_FQDN}" \
    --output none
fi

# Get frontend FQDN
FRONTEND_FQDN=$(az containerapp show \
  --name "$FRONTEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)
echo "  Frontend URL: https://${FRONTEND_FQDN}"

# Step 6: Update backend CORS with frontend URL
echo "[6/7] Updating backend CORS configuration..."
az containerapp update \
  --name "$BACKEND_APP" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars "ALLOWED_ORIGINS=https://${FRONTEND_FQDN}" \
  --output none

# Step 7: Print deployment summary
echo "[7/7] Deployment complete!"
echo ""
echo "=== Deployment Summary ==="
echo ""
echo "Frontend URL: https://${FRONTEND_FQDN}"
echo "Backend URL:  https://${BACKEND_FQDN}"
echo ""
echo "Health Check Commands:"
echo "  curl https://${BACKEND_FQDN}/health"
echo "  curl https://${FRONTEND_FQDN}"
echo ""
echo "View logs:"
echo "  az containerapp logs show -n $BACKEND_APP -g $RESOURCE_GROUP --follow"
echo "  az containerapp logs show -n $FRONTEND_APP -g $RESOURCE_GROUP --follow"
echo ""
echo "Configuration:"
echo "  - PostgreSQL:   ${PG_SERVER}.postgres.database.azure.com / db=${PG_DATABASE}"
echo "  - Blob storage: inclusifystorage / container=${AZURE_STORAGE_CONTAINER}"
echo "  - vLLM:         http://${VLLM_PRIVATE_IP}:${VLLM_PORT} (model=${VLLM_MODEL_NAME})"
echo "  - CORS:         https://${FRONTEND_FQDN}"
echo "  - Secrets:      db-password, jwt-secret, google-client-id/secret, azure-storage-conn-str"
echo ""
