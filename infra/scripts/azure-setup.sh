#!/bin/bash
set -euo pipefail

# Inclusify Azure Infrastructure Setup
# Run with: ./infra/scripts/azure-setup.sh
# Requires: az login already completed

# Configuration - customize these
RESOURCE_GROUP="${RESOURCE_GROUP:-Group07}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-inclusifyacr}"
PG_SERVER="${PG_SERVER:-inclusify-postgres}"
PG_USER="${PG_USER:-inclusifyadmin}"
PG_DATABASE="${PG_DATABASE:-inclusify}"

# Container Apps configuration
CONTAINERAPPS_ENV="${CONTAINERAPPS_ENV:-inclusify-env}"

# VM name for VNet discovery (InclusifyModel VM in Group07)
VM_NAME="${VM_NAME:-InclusifyModel}"

# Container Apps subnet configuration
CONTAINERAPPS_SUBNET="${CONTAINERAPPS_SUBNET:-containerapps-subnet}"
CONTAINERAPPS_SUBNET_PREFIX="${CONTAINERAPPS_SUBNET_PREFIX:-10.0.2.0/27}"

# Discover VNet from InclusifyModel VM
discover_vnet_from_vm() {
  local vm_name=$1
  local resource_group=$2

  echo "Discovering VNet from VM '$vm_name' in '$resource_group'..."

  # Get NIC ID
  local nic_id
  nic_id=$(az vm show \
    --name "$vm_name" \
    --resource-group "$resource_group" \
    --query 'networkProfile.networkInterfaces[0].id' \
    -o tsv 2>/dev/null)

  if [ -z "$nic_id" ]; then
    echo "Error: Could not find network interface for VM '$vm_name'"
    echo "Make sure the VM exists in resource group '$resource_group'"
    return 1
  fi

  # Get subnet ID
  local subnet_id
  subnet_id=$(az network nic show \
    --ids "$nic_id" \
    --query 'ipConfigurations[0].subnet.id' \
    -o tsv 2>/dev/null)

  if [ -z "$subnet_id" ]; then
    echo "Error: Could not find subnet for NIC"
    return 1
  fi

  # Parse VNet name (position 9 in /-separated path)
  VNET_NAME=$(echo "$subnet_id" | cut -d'/' -f9)
  echo "  Discovered VNet: $VNET_NAME"
}

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
echo "VM for VNet discovery: $VM_NAME"
echo ""

# Verify resource group exists (Group07 should already exist with vLLM VM)
echo "[1/10] Verifying resource group..."
if az group show --name "$RESOURCE_GROUP" --output none 2>/dev/null; then
  echo "  Resource group '$RESOURCE_GROUP' exists"
else
  echo "Error: Resource group '$RESOURCE_GROUP' not found"
  echo "This script expects Group07 (with vLLM VM) to already exist"
  exit 1
fi

# Discover VNet from VM
echo "[2/10] Discovering VNet from vLLM VM..."
discover_vnet_from_vm "$VM_NAME" "$RESOURCE_GROUP"
if [ -z "${VNET_NAME:-}" ]; then
  echo "Error: Failed to discover VNet. Ensure InclusifyModel VM exists."
  exit 1
fi

# Create Container Registry (idempotent)
echo "[3/10] Creating Container Registry..."
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --output none 2>/dev/null || echo "  ACR already exists, skipping"

# Create PostgreSQL Flexible Server
echo "[4/10] Creating PostgreSQL Flexible Server (this takes ~5 minutes)..."
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
echo "[5/10] Creating database..."
az postgres flexible-server db create \
  --resource-group "$RESOURCE_GROUP" \
  --server-name "$PG_SERVER" \
  --database-name "$PG_DATABASE" \
  --output none 2>/dev/null || echo "  Database already exists, skipping"

# Create Container Apps subnet in discovered VNet
echo "[6/10] Creating Container Apps subnet in VNet '$VNET_NAME'..."
# Minimum /27 required for workload profiles environment
az network vnet subnet create \
  --resource-group "$RESOURCE_GROUP" \
  --vnet-name "$VNET_NAME" \
  --name "$CONTAINERAPPS_SUBNET" \
  --address-prefixes "$CONTAINERAPPS_SUBNET_PREFIX" \
  --delegations Microsoft.App/environments \
  --output none 2>/dev/null || echo "  Subnet already exists, skipping"

# Get subnet resource ID for Container Apps Environment
echo "[7/10] Getting subnet resource ID..."
INFRASTRUCTURE_SUBNET=$(az network vnet subnet show \
  --resource-group "$RESOURCE_GROUP" \
  --vnet-name "$VNET_NAME" \
  --name "$CONTAINERAPPS_SUBNET" \
  --query id -o tsv)
echo "  Subnet ID: $INFRASTRUCTURE_SUBNET"

# Create Container Apps Environment with VNet integration
echo "[8/10] Creating Container Apps Environment (this takes ~3 minutes)..."
az containerapp env create \
  --name "$CONTAINERAPPS_ENV" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --infrastructure-subnet-resource-id "$INFRASTRUCTURE_SUBNET" \
  --output none 2>/dev/null || echo "  Container Apps Environment already exists, skipping"

# Get Container Apps Environment outbound IPs
echo "[9/10] Getting Container Apps Environment outbound IPs..."
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
echo "[10/10] Getting connection information..."
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Resource Group: $RESOURCE_GROUP"
echo "Discovered VNet: $VNET_NAME"
echo ""
echo "ACR Login Server: ${ACR_NAME}.azurecr.io"
echo "PostgreSQL Host: ${PG_SERVER}.postgres.database.azure.com"
echo "PostgreSQL Database: $PG_DATABASE"
echo "PostgreSQL User: $PG_USER"
echo ""
echo "Container Apps Environment: $CONTAINERAPPS_ENV"
echo "VNet Integration: $VNET_NAME / $CONTAINERAPPS_SUBNET"
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
