#!/bin/bash
# Production Dashboard Test Script
# Tests all endpoints and features

set -e

PROJECT_DIR="/home/iot/attendance-system"
API_KEY=$(grep DASHBOARD_API_KEY "$PROJECT_DIR/.env" | cut -d= -f2)
BASE_URL="https://192.168.1.22"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================================================"
echo "Dashboard Production Tests"
echo "======================================================================"
echo ""

test_count=0
pass_count=0
fail_count=0

# Test function
test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    test_count=$((test_count + 1))
    echo -n "[$test_count] Testing $name... "
    
    response=$(curl -k -s -w "\n%{http_code}" -H "Authorization: Bearer $API_KEY" "$url")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" -eq "$expected_code" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $http_code)"
        pass_count=$((pass_count + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (HTTP $http_code, expected $expected_code)"
        echo "   Response: $body" | head -c 100
        fail_count=$((fail_count + 1))
        return 1
    fi
}

echo -e "${BLUE}=== Core Endpoints ===${NC}"
test_endpoint "Health Check" "$BASE_URL/health"
test_endpoint "System Status" "$BASE_URL/status"
test_endpoint "Metrics" "$BASE_URL/metrics"
echo ""

echo -e "${BLUE}=== Device Endpoints ===${NC}"
test_endpoint "List Devices" "$BASE_URL/devices"
test_endpoint "Device Status" "$BASE_URL/devices/status"
test_endpoint "Device Metrics" "$BASE_URL/devices/metrics"
test_endpoint "Locations" "$BASE_URL/locations"
echo ""

echo -e "${BLUE}=== Filtering ===${NC}"
test_endpoint "Filter by Status (online)" "$BASE_URL/devices?status=online"
test_endpoint "Filter by Building" "$BASE_URL/devices?building=Main%20Building"
echo ""

echo -e "${BLUE}=== Authentication Tests ===${NC}"
echo -n "[$((test_count + 1))] Testing without API key... "
test_count=$((test_count + 1))
response=$(curl -k -s -w "\n%{http_code}" "$BASE_URL/health")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 401 ] || [ "$http_code" -eq 403 ]; then
    echo -e "${GREEN}✅ PASS${NC} (Properly rejected: HTTP $http_code)"
    pass_count=$((pass_count + 1))
else
    echo -e "${RED}❌ FAIL${NC} (Should reject, got HTTP $http_code)"
    fail_count=$((fail_count + 1))
fi

echo -n "[$((test_count + 1))] Testing with invalid API key... "
test_count=$((test_count + 1))
response=$(curl -k -s -w "\n%{http_code}" -H "Authorization: Bearer invalid_key_12345" "$BASE_URL/health")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 401 ] || [ "$http_code" -eq 403 ]; then
    echo -e "${GREEN}✅ PASS${NC} (Properly rejected: HTTP $http_code)"
    pass_count=$((pass_count + 1))
else
    echo -e "${RED}❌ FAIL${NC} (Should reject, got HTTP $http_code)"
    fail_count=$((fail_count + 1))
fi
echo ""

echo -e "${BLUE}=== Service Status ===${NC}"
if systemctl is-active --quiet attendance-dashboard.service; then
    echo -e "${GREEN}✅${NC} Dashboard service: active"
else
    echo -e "${RED}❌${NC} Dashboard service: inactive"
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅${NC} Nginx service: active"
else
    echo -e "${RED}❌${NC} Nginx service: inactive"
fi
echo ""

echo -e "${BLUE}=== Device Data ===${NC}"
device_data=$(curl -k -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/devices")
total=$(echo "$device_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo "0")
echo "Total devices: $total"

if [ "$total" -gt 0 ]; then
    echo "$device_data" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for device in data.get('devices', []):
    status = '🟢' if device['status'] == 'online' else '🔴'
    print(f\"  {status} {device['device_name']}: {device['status']}\")
" 2>/dev/null || echo "  (Could not parse device details)"
fi
echo ""

echo -e "${BLUE}=== Security Headers ===${NC}"
headers=$(curl -k -s -I -H "Authorization: Bearer $API_KEY" "$BASE_URL/health")
check_header() {
    if echo "$headers" | grep -qi "$1"; then
        echo -e "${GREEN}✅${NC} $1 present"
    else
        echo -e "${YELLOW}⚠️${NC}  $1 missing"
    fi
}
check_header "Strict-Transport-Security"
check_header "X-Frame-Options"
check_header "X-Content-Type-Options"
check_header "Content-Security-Policy"
echo ""

echo "======================================================================"
echo -e "${BLUE}Test Results${NC}"
echo "======================================================================"
echo "Total Tests:  $test_count"
echo -e "${GREEN}Passed:       $pass_count${NC}"
echo -e "${RED}Failed:       $fail_count${NC}"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Dashboard is production-ready.${NC}"
    echo ""
    echo "Access dashboard at:"
    echo "  ${BLUE}https://192.168.1.22?api_key=$API_KEY${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Please review the output above.${NC}"
    exit 1
fi
