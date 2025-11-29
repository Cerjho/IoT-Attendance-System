#!/bin/bash
# Test IP Whitelisting Configuration

API_KEY="$1"

if [ -z "$API_KEY" ]; then
    echo "Usage: $0 <api_key>"
    exit 1
fi

echo "========================================="
echo "Testing IP Whitelisting"
echo "========================================="
echo ""

# Test 1: Local access (should work - 127.0.0.1 is whitelisted)
echo "Test 1: Access from localhost (127.0.0.1) - Should ALLOW"
response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $API_KEY" http://127.0.0.1:8080/health)
status=$(echo "$response" | tail -1)
if [ "$status" = "200" ]; then
    echo "✅ PASS: Localhost access allowed (HTTP $status)"
else
    echo "❌ FAIL: Localhost access blocked (HTTP $status)"
fi
echo ""

# Test 2: Local IP access (should work - 192.168.1.0/24 is whitelisted)
echo "Test 2: Access from local IP (192.168.1.22) - Should ALLOW"
response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $API_KEY" http://192.168.1.22:8080/health)
status=$(echo "$response" | tail -1)
if [ "$status" = "200" ]; then
    echo "✅ PASS: Local IP access allowed (HTTP $status)"
else
    echo "❌ FAIL: Local IP access blocked (HTTP $status)"
fi
echo ""

# Test 3: Check if IP validation is working (simulate external IP)
echo "Test 3: Verify IP whitelist is active"
config_ips=$(grep -A2 '"allowed_ips"' /home/iot/attendance-system/config/config.json | grep -E '"[0-9]' | wc -l)
if [ "$config_ips" -gt 0 ]; then
    echo "✅ PASS: IP whitelist configured with $config_ips entries"
    grep -A3 '"allowed_ips"' /home/iot/attendance-system/config/config.json
else
    echo "❌ FAIL: IP whitelist empty"
fi
echo ""

# Test 4: Verify authentication still works
echo "Test 4: Authentication required (no API key) - Should REJECT"
response=$(curl -s -w "\n%{http_code}" http://127.0.0.1:8080/health)
status=$(echo "$response" | tail -1)
if [ "$status" = "401" ]; then
    echo "✅ PASS: Rejected without API key (HTTP $status)"
else
    echo "❌ FAIL: Should reject without API key (HTTP $status)"
fi
echo ""

echo "========================================="
echo "Summary"
echo "========================================="
echo "Current IP Whitelist Configuration:"
grep -A5 '"admin_dashboard"' /home/iot/attendance-system/config/config.json | grep -A3 '"allowed_ips"'
echo ""
echo "Note: To test blocking external IPs, try accessing from"
echo "a device outside your 192.168.1.0/24 network."
echo ""
echo "To add specific IPs, edit config/config.json:"
echo '  "allowed_ips": ["192.168.1.0/24", "10.0.0.5", "127.0.0.1"]'
