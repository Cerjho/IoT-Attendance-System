#!/bin/bash
echo "======================================================================"
echo "COMPREHENSIVE ENDPOINT TESTING"
echo "======================================================================"

BASE_URL="http://localhost:8080"
PASS=0
FAIL=0

test_endpoint() {
    local name="$1"
    local endpoint="$2"
    local expected_status="${3:-200}"
    
    echo -e "\n[$((PASS+FAIL+1))] Testing: $name"
    echo "   Endpoint: $endpoint"
    
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    status=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$status" = "$expected_status" ]; then
        echo "   ✅ Status: $status (expected $expected_status)"
        
        # Check if valid JSON (except for prometheus which is text)
        if [[ ! "$endpoint" =~ "prometheus" ]]; then
            if echo "$body" | python -m json.tool >/dev/null 2>&1; then
                echo "   ✅ Valid JSON response"
                PASS=$((PASS+1))
            else
                echo "   ❌ Invalid JSON response"
                FAIL=$((FAIL+1))
            fi
        else
            echo "   ✅ Text response (Prometheus format)"
            PASS=$((PASS+1))
        fi
    else
        echo "   ❌ Status: $status (expected $expected_status)"
        echo "   Response: $body"
        FAIL=$((FAIL+1))
    fi
}

# Run tests
test_endpoint "Health Check" "/health"
test_endpoint "System Status" "/status"
test_endpoint "System Info" "/system/info"
test_endpoint "Queue Status" "/queue/status"
test_endpoint "Recent Scans (default)" "/scans/recent"
test_endpoint "Recent Scans (limit 3)" "/scans/recent?limit=3"
test_endpoint "Config (sanitized)" "/config"
test_endpoint "Metrics JSON" "/metrics"
test_endpoint "Metrics Prometheus" "/metrics/prometheus"
test_endpoint "Not Found" "/nonexistent" 404

echo ""
echo "======================================================================"
echo "RESULTS: $PASS passed, $FAIL failed"
echo "======================================================================"

exit $FAIL
