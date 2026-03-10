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

# Container Apps configuration
CONTAINERAPPS_ENV="${CONTAINERAPPS_ENV:-inclusify-env}"

# vLLM VNet configuration (existing resources in Group07)
VLLM_RESOURCE_GROUP="${VLLM_RESOURCE_GROUP:-Group07}"
VLLM_VNET_NAME="${VLLM_VNET_NAME:-InclusifyModel-vnet}"
CONTAINERAPPS_SUBNET="${CONTAINERAPPS_SUBNET:-containerapps-subnet}"
CONTAINERAPPS_SUBNET_PREFIX="${CONTAINERAPPS_SUBNET_PREFIX:-10.0.2.0/27}"

# Check for required password
if [ -z "${PG_PASSWORD:-}" ]; then
  echo "Error: PG_PASSWORD environment variable required"
  echo "Usage: PG_PASSWORD=<secure-password> ./infra/scripts/azure-setup.sh"
  exit 1
fi

echo "=== Inclusify Azure Setup ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Container Apps Environment: $CONTAINERAPPS_ENV"
echo "vLLM VNet: $VLLM_VNET_NAME (in $VLLM_RESOURCE_GROUP)"
echo ""

# Create resource group (idempotent)
echo "[1/9] Creating resource group..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

# Create Container Registry (idempotent)
echo "[2/9] Creating Container Registry..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --output none 2>/dev/null || echo "  ACR already exists, skipping"

# Create PostgreSQL Flexible Server
echo "[3/9] Creating PostgreSQL Flexible Server (this takes ~5 minutes)..."
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
echo "[4/9] Creating database..."
az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$PG_SERVER" \
  --database-name "$PG_DATABASE" \
  --output none 2>/dev/null || echo "  Database already exists, skipping"

# Create Container Apps subnet in vLLM VNet
echo "[5/9] Creating Container Apps subnet in vLLM VNet..."
# Note: VNet is in Group07, but we're creating a subnet for Container Apps
# Minimum /27 required for workload profiles environment
az network vnet subnet create \
  --resource-group "$VLLM_RESOURCE_GROUP" \
  --vnet-name "$VLLM_VNET_NAME" \
  --name "$CONTAINERAPPS_SUBNET" \
  --address-prefixes "$CONTAINERAPPS_SUBNET_PREFIX" \
  --delegations Microsoft.App/environments \
  --output none 2>/dev/null || echo "  Subnet already exists, skipping"

# Get subnet resource ID for Container Apps Environment
echo "[6/9] Getting subnet resource ID..."
INFRASTRUCTURE_SUBNET=$(az network vnet subnet show \
  --resource-group "$VLLM_RESOURCE_GROUP" \
  --vnet-name "$VLLM_VNET_NAME" \
  --name "$CONTAINERAPPS_SUBNET" \
  --query id -o tsv)
echo "  Subnet ID: $INFRASTRUCTURE_SUBNET"

# Create Container Apps Environment with VNet integration
echo "[7/9] Creating Container Apps Environment (this takes ~3 minutes)..."
az containerapp env create \
  --name "$CONTAINERAPPS_ENV" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --infrastructure-subnet-resource-id "$INFRASTRUCTURE_SUBNET" \
  --output none 2>/dev/null || echo "  Container Apps Environment already exists, skipping"

# Get Container Apps Environment outbound IPs
echo "[8/9] Getting Container Apps Environment outbound IPs..."
OUTBOUND_IPS=$(az containerapp env show \
  --name "$CONTAINERAPPS_ENV" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.staticIp" -o tsv 2>/dev/null || echo "")

if [ -n "$OUTBOUND_IPS" ]; then
  echo "  Static IP: $OUTBOUND_IPS"

  # Add firewall rule for Container Apps static IP
  echo "  Adding PostgreSQL firewall rule for Container Apps..."
  az postgres flexible-server firewall-rule create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$PG_SERVER" \
    --rule-name "AllowContainerApps" \
    --start-ip-address "$OUTBOUND_IPS" \
    --end-ip-address "$OUTBOUND_IPS" \
    --output none 2>/dev/null || echo "  Firewall rule already exists, skipping"
else
  echo "  Warning: Could not get Container Apps outbound IP"
  echo "  You may need to manually add firewall rules after deployment"
fi

# Get connection info
echo "[9/9] Getting connection information..."
echo ""
echo "=== Setup Complete ==="
echo ""
echo "ACR Login Server: ${ACR_NAME}.azurecr.io"
echo "PostgreSQL Host: ${PG_SERVER}.postgres.database.azure.com"
echo "PostgreSQL Database: $PG_DATABASE"
echo "PostgreSQL User: $PG_USER"
echo ""
echo "Container Apps Environment: $CONTAINERAPPS_ENV"
echo "VNet Integration: $VLLM_VNET_NAME / $CONTAINERAPPS_SUBNET"
if [ -n "${OUTBOUND_IPS:-}" ]; then
  echo "Container Apps Static IP: $OUTBOUND_IPS"
fi
echo ""
echo "Connection string (save this):"
echo "PGHOST=${PG_SERVER}.postgres.database.azure.com"
echo "PGPORT=5432"
echo "PGDATABASE=$PG_DATABASE"
echo "PGUSER=$PG_USER"
echo "PGPASSWORD=<your-password>"
echo "PGSSL=require"
echo ""
echo "Next step: Run ./infra/scripts/azure-deploy.sh to deploy container apps"
