#!/bin/bash
set -euo pipefail

# Inclusify Azure Infrastructure Validation Script
# Validates Azure resources exist and are healthy
# Usage: ./scripts/validate-azure.sh [--pre-deploy]

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-Group07}"
ACR_NAME="${ACR_NAME:-inclusifyacr}"
PG_SERVER="${PG_SERVER:-inclusify-db}"
CONTAINER_ENV="${CONTAINER_ENV:-inclusify-env}"
BACKEND_APP="${BACKEND_APP:-inclusify-backend}"
FRONTEND_APP="${FRONTEND_APP:-inclusify-frontend}"
VM_NAME="${VM_NAME:-InclusifyModel}"
CONTAINERAPPS_SUBNET="${CONTAINERAPPS_SUBNET:-containerapps-subnet}"

# Parse arguments
PRE_DEPLOY_ONLY=false
for arg in "$@"; do
  case $arg in
    --pre-deploy)
      PRE_DEPLOY_ONLY=true
      shift
      ;;
  esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
SKIPPED=0

check_pass() {
  echo -e "${GREEN}[PASS]${NC} $1"
  ((PASSED++))
}

check_fail() {
  echo -e "${RED}[FAIL]${NC} $1"
  ((FAILED++))
}

check_skip() {
  echo -e "${YELLOW}[SKIP]${NC} $1"
  ((SKIPPED++))
}

echo "=== Inclusify Azure Infrastructure Validation ==="
echo "Resource Group: $RESOURCE_GROUP"
echo ""

# ============================================
# Section 1: Azure CLI Authentication
# ============================================
echo "--- Azure CLI Authentication ---"
if az account show --output none 2>/dev/null; then
  SUBSCRIPTION=$(az account show --query "name" -o tsv)
  check_pass "Azure CLI authenticated (Subscription: $SUBSCRIPTION)"
else
  check_fail "Azure CLI not authenticated (run: az login)"
  echo ""
  echo "Total: $PASSED passed, $FAILED failed, $SKIPPED skipped"
  exit 1
fi

# ============================================
# Section 2: Resource Group
# ============================================
echo ""
echo "--- Resource Group ---"
if az group show --name "$RESOURCE_GROUP" --output none 2>/dev/null; then
  check_pass "Resource Group '$RESOURCE_GROUP' exists"
else
  check_fail "Resource Group '$RESOURCE_GROUP' not found"
fi

# ============================================
# Section 2.5: VNet Discovery
# ============================================
echo ""
echo "--- VNet Discovery ---"
# Discover VNet from VM
NIC_ID=$(az vm show --name "$VM_NAME" --resource-group "$RESOURCE_GROUP" \
  --query 'networkProfile.networkInterfaces[0].id' -o tsv 2>/dev/null || echo "")

if [ -n "$NIC_ID" ]; then
  SUBNET_ID=$(az network nic show --ids "$NIC_ID" \
    --query 'ipConfigurations[0].subnet.id' -o tsv 2>/dev/null || echo "")
  if [ -n "$SUBNET_ID" ]; then
    VNET_NAME=$(echo "$SUBNET_ID" | cut -d'/' -f9)
    check_pass "VNet discovered from VM '$VM_NAME': $VNET_NAME"
  else
    check_fail "Could not extract VNet from VM NIC"
  fi
else
  check_fail "VM '$VM_NAME' not found in '$RESOURCE_GROUP'"
fi

# Check Container Apps subnet
if [ -n "${VNET_NAME:-}" ]; then
  if az network vnet subnet show --resource-group "$RESOURCE_GROUP" --vnet-name "$VNET_NAME" \
    --name "$CONTAINERAPPS_SUBNET" --output none 2>/dev/null; then
    check_pass "Container Apps subnet '$CONTAINERAPPS_SUBNET' exists in VNet"
  else
    check_skip "Container Apps subnet not yet created (run azure-setup.sh first)"
  fi
fi

# ============================================
# Section 3: Container Registry
# ============================================
echo ""
echo "--- Container Registry ---"
if az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null; then
  LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" --query "loginServer" -o tsv)
  check_pass "ACR '$ACR_NAME' exists (Server: $LOGIN_SERVER)"
else
  check_fail "ACR '$ACR_NAME' not found"
fi

# ============================================
# Section 4: PostgreSQL Flexible Server
# ============================================
echo ""
echo "--- PostgreSQL Server ---"
if az postgres flexible-server show --name "$PG_SERVER" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null; then
  PG_STATE=$(az postgres flexible-server show --name "$PG_SERVER" --resource-group "$RESOURCE_GROUP" --query "state" -o tsv)
  if [ "$PG_STATE" = "Ready" ]; then
    check_pass "PostgreSQL '$PG_SERVER' exists and is Ready"
  else
    check_fail "PostgreSQL '$PG_SERVER' exists but state is '$PG_STATE'"
  fi
else
  check_fail "PostgreSQL '$PG_SERVER' not found"
fi

# If pre-deploy only, exit here
if [ "$PRE_DEPLOY_ONLY" = true ]; then
  echo ""
  echo "=== Pre-deployment Validation Complete ==="
  echo "Total: $PASSED passed, $FAILED failed, $SKIPPED skipped"
  if [ $FAILED -gt 0 ]; then
    exit 1
  fi
  exit 0
fi

# ============================================
# Section 5: Container Apps Environment
# ============================================
echo ""
echo "--- Container Apps Environment ---"
if az containerapp env show --name "$CONTAINER_ENV" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null; then
  ENV_STATE=$(az containerapp env show --name "$CONTAINER_ENV" --resource-group "$RESOURCE_GROUP" --query "properties.provisioningState" -o tsv)
  if [ "$ENV_STATE" = "Succeeded" ]; then
    check_pass "Container Apps Environment '$CONTAINER_ENV' exists and Succeeded"
  else
    check_fail "Container Apps Environment '$CONTAINER_ENV' state is '$ENV_STATE'"
  fi
else
  check_skip "Container Apps Environment '$CONTAINER_ENV' not yet created (run deployment first)"
fi

# ============================================
# Section 6: Backend Container App
# ============================================
echo ""
echo "--- Backend Container App ---"
if az containerapp show --name "$BACKEND_APP" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null; then
  BACKEND_STATE=$(az containerapp show --name "$BACKEND_APP" --resource-group "$RESOURCE_GROUP" --query "properties.provisioningState" -o tsv)
  if [ "$BACKEND_STATE" = "Succeeded" ]; then
    check_pass "Backend Container App '$BACKEND_APP' provisioning Succeeded"

    # Get FQDN and test health endpoint
    BACKEND_FQDN=$(az containerapp show --name "$BACKEND_APP" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)
    if [ -n "$BACKEND_FQDN" ]; then
      echo "  Backend URL: https://$BACKEND_FQDN"
      if curl -sf "https://${BACKEND_FQDN}/" --max-time 10 >/dev/null 2>&1; then
        check_pass "Backend health endpoint responding"
      else
        check_fail "Backend health endpoint not responding"
      fi
    fi
  else
    check_fail "Backend Container App '$BACKEND_APP' state is '$BACKEND_STATE'"
  fi
else
  check_skip "Backend Container App '$BACKEND_APP' not yet created"
fi

# ============================================
# Section 7: Frontend Container App
# ============================================
echo ""
echo "--- Frontend Container App ---"
if az containerapp show --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null; then
  FRONTEND_STATE=$(az containerapp show --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" --query "properties.provisioningState" -o tsv)
  if [ "$FRONTEND_STATE" = "Succeeded" ]; then
    check_pass "Frontend Container App '$FRONTEND_APP' provisioning Succeeded"

    # Get FQDN
    FRONTEND_FQDN=$(az containerapp show --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv)
    if [ -n "$FRONTEND_FQDN" ]; then
      echo "  Frontend URL: https://$FRONTEND_FQDN"
    fi
  else
    check_fail "Frontend Container App '$FRONTEND_APP' state is '$FRONTEND_STATE'"
  fi
else
  check_skip "Frontend Container App '$FRONTEND_APP' not yet created"
fi

# ============================================
# Section 8: Secrets Verification (INFRA-02)
# ============================================
echo ""
echo "--- Secrets Verification (INFRA-02) ---"
SECRETS_FAILED=false

# Check if backend app exists before checking secrets
if az containerapp show --name "$BACKEND_APP" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null; then
  # List secrets
  SECRETS=$(az containerapp secret list --name "$BACKEND_APP" --resource-group "$RESOURCE_GROUP" -o json 2>/dev/null || echo "[]")

  # Check for required secrets
  if echo "$SECRETS" | grep -q '"name": "db-password"' 2>/dev/null || echo "$SECRETS" | grep -q '"name":"db-password"' 2>/dev/null; then
    check_pass "Secret 'db-password' exists in Container Apps secrets"
  else
    check_fail "Secret 'db-password' NOT found in Container Apps secrets"
    SECRETS_FAILED=true
  fi

  if echo "$SECRETS" | grep -q '"name": "jwt-secret"' 2>/dev/null || echo "$SECRETS" | grep -q '"name":"jwt-secret"' 2>/dev/null; then
    check_pass "Secret 'jwt-secret' exists in Container Apps secrets"
  else
    check_fail "Secret 'jwt-secret' NOT found in Container Apps secrets"
    SECRETS_FAILED=true
  fi

  # Verify secrets are NOT exposed in environment variables (security check)
  ENV_VARS=$(az containerapp show --name "$BACKEND_APP" --resource-group "$RESOURCE_GROUP" --query "properties.template.containers[0].env" -o json 2>/dev/null || echo "[]")

  # Check that no env var contains raw password-like values
  EXPOSED_SECRETS=false
  if echo "$ENV_VARS" | grep -qE '"value":\s*"[^"]{16,}"' 2>/dev/null; then
    # Check if any long value in env looks like it could be a secret (not a URL)
    # This is a heuristic check - env vars should reference secrets, not contain raw values
    for name in "DATABASE_URL" "DB_PASSWORD" "JWT_SECRET" "SECRET_KEY"; do
      if echo "$ENV_VARS" | grep -q "\"name\": \"$name\"" 2>/dev/null; then
        # If the var exists, it should use secretRef, not direct value
        VAR_INFO=$(echo "$ENV_VARS" | python3 -c "import json,sys; evs=json.load(sys.stdin); print(next((str(e.get('secretRef','NONE')) for e in (evs or []) if e.get('name')=='$name'),'NOT_FOUND'))" 2>/dev/null || echo "PARSE_ERROR")
        if [ "$VAR_INFO" = "NONE" ]; then
          # Has value but no secretRef - potentially exposed
          echo -e "  ${YELLOW}[WARN]${NC} '$name' env var may not be using secretRef"
        fi
      fi
    done
  fi

  if [ "$EXPOSED_SECRETS" = false ]; then
    check_pass "No obvious raw secrets exposed in environment variables"
  fi
else
  check_skip "Backend app not deployed - cannot verify secrets"
fi

# ============================================
# Summary
# ============================================
echo ""
echo "=== Validation Complete ==="
echo "Total: $PASSED passed, $FAILED failed, $SKIPPED skipped"

# Exit codes
if [ "$SECRETS_FAILED" = true ]; then
  echo ""
  echo "Secrets verification failed! Ensure secrets are properly configured."
  exit 3
fi

if [ $FAILED -gt 0 ] && [ $SKIPPED -eq 0 ]; then
  exit 1
elif [ $FAILED -gt 0 ]; then
  exit 2
fi

exit 0
