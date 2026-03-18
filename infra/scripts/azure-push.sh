#!/bin/bash
set -euo pipefail

# Push Docker images to Azure Container Registry

ACR_NAME="${ACR_NAME:-inclusifyacr}"
TAG="${TAG:-latest}"

echo "=== Push to Azure Container Registry ==="
echo "Registry: ${ACR_NAME}.azurecr.io"
echo "Tag: $TAG"
echo ""

# Login to ACR
echo "[1/4] Logging into ACR..."
az acr login --name "$ACR_NAME"

# Tag images
echo "[2/4] Tagging images..."
docker tag inclusify-backend:latest "${ACR_NAME}.azurecr.io/inclusify-backend:${TAG}"
docker tag inclusify-frontend:latest "${ACR_NAME}.azurecr.io/inclusify-frontend:${TAG}"

# Push images
echo "[3/4] Pushing backend image..."
docker push "${ACR_NAME}.azurecr.io/inclusify-backend:${TAG}"

echo "[4/4] Pushing frontend image..."
docker push "${ACR_NAME}.azurecr.io/inclusify-frontend:${TAG}"

echo ""
echo "=== Push Complete ==="
echo "Backend: ${ACR_NAME}.azurecr.io/inclusify-backend:${TAG}"
echo "Frontend: ${ACR_NAME}.azurecr.io/inclusify-frontend:${TAG}"
