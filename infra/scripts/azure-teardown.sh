#!/bin/bash
set -euo pipefail

# Inclusify Azure Infrastructure Teardown
# WARNING: This deletes ALL resources including database data

RESOURCE_GROUP="${RESOURCE_GROUP:-inclusify-rg}"

echo "=== Inclusify Azure Teardown ==="
echo ""
echo "WARNING: This will delete ALL resources in '$RESOURCE_GROUP'"
echo "Including: Container Registry, PostgreSQL server, and ALL DATA"
echo ""
read -p "Type 'DELETE' to confirm: " confirm

if [ "$confirm" != "DELETE" ]; then
  echo "Aborted."
  exit 1
fi

echo "Deleting resource group '$RESOURCE_GROUP'..."
az group delete \
  --name "$RESOURCE_GROUP" \
  --yes \
  --no-wait

echo "Deletion initiated (runs in background)"
echo "Check status: az group show --name $RESOURCE_GROUP"
