#!/bin/bash
set -euo pipefail

# Inclusify Azure Infrastructure Setup
# Run with: ./infra/scripts/azure-setup.sh
# Requires: az login already completed

# Configuration - customize these
RESOURCE_GROUP="${RESOURCE_GROUP:-inclusify-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-inclusifyacr}"
PG_SERVER="${PG_SERVER:-inclusify-db}"
PG_USER="${PG_USER:-inclusifyadmin}"
PG_DATABASE="${PG_DATABASE:-inclusify}"

# Check for required password
if [ -z "${PG_PASSWORD:-}" ]; then
  echo "Error: PG_PASSWORD environment variable required"
  echo "Usage: PG_PASSWORD=<secure-password> ./infra/scripts/azure-setup.sh"
  exit 1
fi

echo "=== Inclusify Azure Setup ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo ""

# Create resource group (idempotent)
echo "[1/5] Creating resource group..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# Create Container Registry (idempotent)
echo "[2/5] Creating Container Registry..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --output none 2>/dev/null || echo "  ACR already exists, skipping"

# Create PostgreSQL Flexible Server
echo "[3/5] Creating PostgreSQL Flexible Server (this takes ~5 minutes)..."
az postgres flexible-server create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$PG_SERVER" \
  --location "$LOCATION" \
  --admin-user "$PG_USER" \
  --admin-password "$PG_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --public-access 0.0.0.0 \
  --yes \
  --output none 2>/dev/null || echo "  PostgreSQL server already exists, skipping"

# Create database
echo "[4/5] Creating database..."
az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$PG_SERVER" \
  --database-name "$PG_DATABASE" \
  --output none 2>/dev/null || echo "  Database already exists, skipping"

# Get connection info
echo "[5/5] Getting connection information..."
echo ""
echo "=== Setup Complete ==="
echo ""
echo "ACR Login Server: ${ACR_NAME}.azurecr.io"
echo "PostgreSQL Host: ${PG_SERVER}.postgres.database.azure.com"
echo "PostgreSQL Database: $PG_DATABASE"
echo "PostgreSQL User: $PG_USER"
echo ""
echo "Connection string (save this):"
echo "PGHOST=${PG_SERVER}.postgres.database.azure.com"
echo "PGPORT=5432"
echo "PGDATABASE=$PG_DATABASE"
echo "PGUSER=$PG_USER"
echo "PGPASSWORD=<your-password>"
echo "PGSSL=require"
