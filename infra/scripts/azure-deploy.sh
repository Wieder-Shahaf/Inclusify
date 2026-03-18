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

# Database configuration
PG_SERVER="${PG_SERVER:-inclusify-db}"
PG_USER="${PG_USER:-inclusifyadmin}"
PG_DATABASE="${PG_DATABASE:-inclusify}"

# vLLM VM private IP (from VNet setup)
VLLM_PRIVATE_IP="${VLLM_PRIVATE_IP:-10.0.0.4}"
VLLM_PORT="${VLLM_PORT:-8001}"

# Check for required secrets
if [ -z "${PG_PASSWORD:-}" ]; then
  echo "Error: PG_PASSWORD environment variable required"
  echo "Usage: PG_PASSWORD=<password> JWT_SECRET=<secret> ./infra/scripts/azure-deploy.sh"
  exit 1
fi

if [ -z "${JWT_SECRET:-}" ]; then
  echo "Error: JWT_SECRET environment variable required"
  echo "Generate with: openssl rand -base64 32"
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
  --build-arg NEXT_PUBLIC_USE_DEMO_MODE="false" \
  -t "${ACR_NAME}.azurecr.io/inclusify-frontend:${IMAGE_TAG}" \
  .
docker push "${ACR_NAME}.azurecr.io/inclusify-frontend:${IMAGE_TAG}"

# Step 4: Deploy/update backend Container App
echo "[4/7] Deploying backend Container App..."
if app_exists "$BACKEND_APP"; then
  echo "  Backend app exists, updating..."

  # Update secrets
  az containerapp secret set \
    --name "$BACKEND_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --secrets "db-password=$PG_PASSWORD" "jwt-secret=$JWT_SECRET" \
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
      "VLLM_URL=http://${VLLM_PRIVATE_IP}:${VLLM_PORT}" \
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
    --secrets "db-password=$PG_PASSWORD" "jwt-secret=$JWT_SECRET" \
    --env-vars \
      "PGHOST=${PG_SERVER}.postgres.database.azure.com" \
      "PGPORT=5432" \
      "PGDATABASE=$PG_DATABASE" \
      "PGUSER=$PG_USER" \
      "PGPASSWORD=secretref:db-password" \
      "PGSSL=require" \
      "JWT_SECRET=secretref:jwt-secret" \
      "VLLM_URL=http://${VLLM_PRIVATE_IP}:${VLLM_PORT}" \
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
      "NEXT_PUBLIC_USE_DEMO_MODE=false" \
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
      "NEXT_PUBLIC_USE_DEMO_MODE=false" \
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
echo "  - Backend connects to PostgreSQL at ${PG_SERVER}.postgres.database.azure.com"
echo "  - Backend connects to vLLM at http://${VLLM_PRIVATE_IP}:${VLLM_PORT}"
echo "  - CORS configured for https://${FRONTEND_FQDN}"
echo "  - Secrets stored in Container Apps secrets (db-password, jwt-secret)"
echo ""
