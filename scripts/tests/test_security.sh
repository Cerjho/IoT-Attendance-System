#!/bin/bash
API_KEY="$1"
BASE_URL="http://localhost:8080"

echo "======================================================================"
echo "SECURITY TEST SUITE"
echo "======================================================================"
echo ""

PASS=0
FAIL=0

# Test 1: No auth should fail
echo "[1] Testing: No Authentication (should return 401)"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
STATUS=$(echo "$RESPONSE" | tail -1)
if [ "$STATUS" = "401" ]; then
    echo "   ✅ Correctly rejected (401)"
    PASS=$((PASS+1))
else
    echo "   ❌ Expected 401, got $STATUS"
    FAIL=$((FAIL+1))
fi

# Test 2: Valid Bearer token should succeed
echo ""
echo "[2] Testing: Valid Bearer Token (should return 200)"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $API_KEY" "$BASE_URL/health")
STATUS=$(echo "$RESPONSE" | tail -1)
if [ "$STATUS" = "200" ]; then
    echo "   ✅ Authenticated successfully (200)"
    PASS=$((PASS+1))
else
    echo "   ❌ Expected 200, got $STATUS"
    FAIL=$((FAIL+1))
fi

# Test 3: Valid X-API-Key header should succeed
echo ""
echo "[3] Testing: Valid X-API-Key Header (should return 200)"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/status")
STATUS=$(echo "$RESPONSE" | tail -1)
if [ "$STATUS" = "200" ]; then
    echo "   ✅ Authenticated successfully (200)"
    PASS=$((PASS+1))
else
    echo "   ❌ Expected 200, got $STATUS"
    FAIL=$((FAIL+1))
fi

# Test 4: Invalid API key should fail
echo ""
echo "[4] Testing: Invalid API Key (should return 401)"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer invalid_key_123" "$BASE_URL/health")
STATUS=$(echo "$RESPONSE" | tail -1)
if [ "$STATUS" = "401" ]; then
    echo "   ✅ Correctly rejected (401)"
    PASS=$((PASS+1))
else
    echo "   ❌ Expected 401, got $STATUS"
    FAIL=$((FAIL+1))
fi

# Test 5: All protected endpoints
echo ""
echo "[5] Testing: All Endpoints with Valid Auth"
ENDPOINTS="health status system/info queue/status scans/recent metrics config"
for endpoint in $ENDPOINTS; do
    RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $API_KEY" "$BASE_URL/$endpoint")
    STATUS=$(echo "$RESPONSE" | tail -1)
    if [ "$STATUS" = "200" ]; then
        echo "   ✅ /$endpoint"
        PASS=$((PASS+1))
    else
        echo "   ❌ /$endpoint (got $STATUS)"
        FAIL=$((FAIL+1))
    fi
done

# Test 6: Security headers
echo ""
echo "[6] Testing: Security Headers"
HEADERS=$(curl -s -I -H "Authorization: Bearer $API_KEY" "$BASE_URL/health")
if echo "$HEADERS" | grep -q "X-Content-Type-Options"; then
    echo "   ✅ X-Content-Type-Options present"
    PASS=$((PASS+1))
else
    echo "   ❌ X-Content-Type-Options missing"
    FAIL=$((FAIL+1))
fi

if echo "$HEADERS" | grep -q "X-Frame-Options"; then
    echo "   ✅ X-Frame-Options present"
    PASS=$((PASS+1))
else
    echo "   ❌ X-Frame-Options missing"
    FAIL=$((FAIL+1))
fi

echo ""
echo "======================================================================"
echo "RESULTS: $PASS passed, $FAIL failed"
echo "======================================================================"
