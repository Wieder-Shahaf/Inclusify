#!/bin/bash
set -euo pipefail

# Inclusify Azure Infrastructure Teardown
# WARNING: This deletes ALL resources including the vLLM VM and database data

RESOURCE_GROUP="${RESOURCE_GROUP:-Group07}"

echo "=== Inclusify Azure Teardown ==="
echo ""
echo "!!! CRITICAL WARNING !!!"
echo ""
echo "Resource group '$RESOURCE_GROUP' contains the vLLM VM (InclusifyModel)."
echo "Deleting this resource group will DESTROY:"
echo "  - The InclusifyModel VM (vLLM inference server)"
echo "  - All associated disks and network interfaces"
echo "  - Container Registry (inclusifyacr)"
echo "  - PostgreSQL server (inclusify-db) and ALL DATA"
echo "  - Container Apps Environment"
echo ""
echo "This is IRREVERSIBLE and will require full Azure re-provisioning."
echo ""
read -p "Type 'DELETE-ALL-INCLUDING-VM' to confirm: " confirm

if [ "$confirm" != "DELETE-ALL-INCLUDING-VM" ]; then
  echo "Aborted. To delete only Inclusify app resources (keeping VM):"
  echo "  - Delete Container Apps: az containerapp delete --name inclusify-backend --resource-group $RESOURCE_GROUP"
  echo "  - Delete Container Apps: az containerapp delete --name inclusify-frontend --resource-group $RESOURCE_GROUP"
  echo "  - Delete Container Apps Environment: az containerapp env delete --name inclusify-env --resource-group $RESOURCE_GROUP"
  echo "  - Delete PostgreSQL: az postgres flexible-server delete --name inclusify-db --resource-group $RESOURCE_GROUP"
  echo "  - Delete ACR: az acr delete --name inclusifyacr --resource-group $RESOURCE_GROUP"
  exit 1
fi

echo "Deleting resource group '$RESOURCE_GROUP'..."
az group delete \
  --name "$RESOURCE_GROUP" \
  --yes \
  --no-wait

echo "Deletion initiated (runs in background)"
echo "Check status: az group show --name $RESOURCE_GROUP"
