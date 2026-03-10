#!/bin/bash
set -euo pipefail

# Inclusify E2E Flow Test Script
# Tests complete upload -> analysis -> results flow
# Usage: ./scripts/test-e2e-flow.sh [BACKEND_URL] [FRONTEND_URL] [TEST_PDF_PATH]

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-inclusify-rg}"
BACKEND_APP="${BACKEND_APP:-inclusify-backend}"
FRONTEND_APP="${FRONTEND_APP:-inclusify-frontend}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0
SKIPPED=0
TOTAL=0

test_pass() {
  echo -e "${GREEN}[PASS]${NC} $1"
  ((PASSED++))
  ((TOTAL++))
}

test_fail() {
  echo -e "${RED}[FAIL]${NC} $1"
  ((FAILED++))
  ((TOTAL++))
}

test_skip() {
  echo -e "${YELLOW}[SKIP]${NC} $1"
  ((SKIPPED++))
  ((TOTAL++))
}

# ============================================
# Section 1: Parse Arguments or Auto-detect URLs
# ============================================
BACKEND_URL="${1:-}"
FRONTEND_URL="${2:-}"
TEST_PDF_PATH="${3:-}"

echo "=== Inclusify E2E Flow Test ==="
echo ""

# Auto-detect Backend URL from Azure if not provided
if [ -z "$BACKEND_URL" ]; then
  echo "Auto-detecting Backend URL from Azure..."
  if command -v az &> /dev/null && az account show --output none 2>/dev/null; then
    BACKEND_FQDN=$(az containerapp show --name "$BACKEND_APP" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    if [ -n "$BACKEND_FQDN" ]; then
      BACKEND_URL="https://${BACKEND_FQDN}"
      echo "  Detected: $BACKEND_URL"
    else
      echo "  Could not detect Backend URL from Azure."
      echo "  Usage: $0 <BACKEND_URL> [FRONTEND_URL] [TEST_PDF_PATH]"
      exit 1
    fi
  else
    echo "  Azure CLI not available or not logged in."
    echo "  Usage: $0 <BACKEND_URL> [FRONTEND_URL] [TEST_PDF_PATH]"
    exit 1
  fi
fi

# Auto-detect Frontend URL from Azure if not provided
if [ -z "$FRONTEND_URL" ]; then
  echo "Auto-detecting Frontend URL from Azure..."
  if command -v az &> /dev/null && az account show --output none 2>/dev/null; then
    FRONTEND_FQDN=$(az containerapp show --name "$FRONTEND_APP" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    if [ -n "$FRONTEND_FQDN" ]; then
      FRONTEND_URL="https://${FRONTEND_FQDN}"
      echo "  Detected: $FRONTEND_URL"
    else
      echo "  Could not detect Frontend URL - will skip frontend tests"
    fi
  fi
fi

echo ""
echo "Backend URL: $BACKEND_URL"
echo "Frontend URL: ${FRONTEND_URL:-not configured}"
echo "Test PDF: ${TEST_PDF_PATH:-not provided (will skip upload test)}"
echo ""

# ============================================
# Section 2: Health Check - Backend
# ============================================
echo "--- Health Checks ---"

# Backend health
echo "Testing Backend health endpoint..."
BACKEND_HEALTH=$(curl -sf "${BACKEND_URL}/" --max-time 10 2>/dev/null || echo "FAIL")
if [ "$BACKEND_HEALTH" != "FAIL" ]; then
  test_pass "Backend health endpoint (${BACKEND_URL}/)"
else
  test_fail "Backend health endpoint not responding"
  echo ""
  echo "=== Test Results ==="
  echo "Passed: $PASSED, Failed: $FAILED, Skipped: $SKIPPED"
  echo ""
  echo "Health checks failed - cannot continue E2E tests."
  exit 1
fi

# Frontend health
if [ -n "$FRONTEND_URL" ]; then
  echo "Testing Frontend health..."
  FRONTEND_HEALTH=$(curl -sf "${FRONTEND_URL}" --max-time 10 2>/dev/null || echo "FAIL")
  if [ "$FRONTEND_HEALTH" != "FAIL" ]; then
    test_pass "Frontend responding (${FRONTEND_URL})"
  else
    test_fail "Frontend not responding"
  fi
else
  test_skip "Frontend URL not configured"
fi

# ============================================
# Section 3: Test Analysis Endpoint
# ============================================
echo ""
echo "--- Analysis Endpoint ---"

# Test with known problematic text that should trigger detection
TEST_TEXT='The homosexual lifestyle is deviant.'

echo "Testing POST ${BACKEND_URL}/api/v1/analysis/analyze..."
ANALYSIS_RESPONSE=$(curl -sf -X POST "${BACKEND_URL}/api/v1/analysis/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"${TEST_TEXT}\", \"language\": \"en\", \"private_mode\": false}" \
  --max-time 30 2>/dev/null || echo "FAIL")

if [ "$ANALYSIS_RESPONSE" = "FAIL" ]; then
  test_fail "Analysis endpoint returned error"
  echo ""
  echo "=== Test Results ==="
  echo "Passed: $PASSED, Failed: $FAILED, Skipped: $SKIPPED"
  echo ""
  echo "Analysis endpoint failed."
  exit 2
fi

# Check response contains issues array
if echo "$ANALYSIS_RESPONSE" | grep -q '"issues"'; then
  test_pass "Analysis endpoint returns response with 'issues' field"
else
  test_fail "Analysis response missing 'issues' field"
  echo "  Response: ${ANALYSIS_RESPONSE:0:200}..."
  exit 2
fi

# Check that at least one issue was detected in the test text
ISSUE_COUNT=$(echo "$ANALYSIS_RESPONSE" | python3 -c "import json,sys; r=json.load(sys.stdin); print(len(r.get('issues',[])))" 2>/dev/null || echo "0")
if [ "$ISSUE_COUNT" -gt 0 ]; then
  test_pass "Detected $ISSUE_COUNT issue(s) in test text"
else
  test_fail "No issues detected in test text (expected at least 1)"
  echo "  Response: ${ANALYSIS_RESPONSE:0:300}..."
fi

# ============================================
# Section 4: Test PDF Upload Endpoint
# ============================================
echo ""
echo "--- Upload Endpoint ---"

if [ -n "$TEST_PDF_PATH" ] && [ -f "$TEST_PDF_PATH" ]; then
  echo "Testing POST ${BACKEND_URL}/api/v1/ingestion/upload..."
  UPLOAD_RESPONSE=$(curl -sf -X POST "${BACKEND_URL}/api/v1/ingestion/upload" \
    -F "file=@${TEST_PDF_PATH}" \
    --max-time 60 2>/dev/null || echo "FAIL")

  if [ "$UPLOAD_RESPONSE" = "FAIL" ]; then
    test_fail "Upload endpoint returned error"
    exit 3
  fi

  # Check response contains extracted text
  if echo "$UPLOAD_RESPONSE" | grep -qE '"(text|extracted_text|full_text)"'; then
    test_pass "Upload endpoint returns extracted text"
  else
    test_fail "Upload response missing text field"
    echo "  Response: ${UPLOAD_RESPONSE:0:200}..."
  fi
else
  test_skip "PDF upload test (no test PDF provided)"
fi

# ============================================
# Section 5: Summary
# ============================================
echo ""
echo "=== E2E Test Results ==="
echo ""
echo "Health checks:      ${GREEN}PASS${NC}"
if [ "$FAILED" -eq 0 ]; then
  echo "Analysis endpoint:  ${GREEN}PASS${NC}"
else
  echo "Analysis endpoint:  ${RED}ISSUES${NC}"
fi
if [ -n "$TEST_PDF_PATH" ] && [ -f "$TEST_PDF_PATH" ]; then
  if [ "$FAILED" -eq 0 ]; then
    echo "Upload endpoint:    ${GREEN}PASS${NC}"
  else
    echo "Upload endpoint:    ${RED}FAIL${NC}"
  fi
else
  echo "Upload endpoint:    ${YELLOW}SKIP${NC} (no test PDF)"
fi
echo ""
echo "Total: $PASSED/$TOTAL tests passed"

if [ "$SKIPPED" -gt 0 ]; then
  echo "Skipped: $SKIPPED tests"
fi

if [ "$FAILED" -gt 0 ]; then
  echo ""
  echo -e "${RED}E2E tests failed!${NC}"
  exit 2
fi

echo ""
echo -e "${GREEN}All E2E tests passed!${NC}"
exit 0
