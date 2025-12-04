#!/bin/bash
# Production Deployment Checklist
# Quick validation of critical production requirements

set -e
cd "$(dirname "$0")/.."

echo "=========================================="
echo "PRODUCTION READINESS CHECK"
echo "=========================================="

PASSED=0
FAILED=0

pass() { echo "✅ $1"; ((PASSED++)); }
fail() { echo "❌ $1"; ((FAILED++)); }

# 1. Secrets configured
echo -e "\n1. Environment Secrets:"
[ -f .env ] && pass ".env exists" || fail ".env missing"
grep -q "^URL_SIGNING_SECRET=" .env 2>/dev/null && pass "URL_SIGNING_SECRET set" || fail "URL_SIGNING_SECRET missing"
echo "\u2139\ufe0f  DASHBOARD_API_KEY removed (dashboard now separate project)"

# 2. Config security
echo -e "\n2. Configuration Security:"
grep -q '${SUPABASE_URL}' config/config.json 2>/dev/null && pass "Secrets use placeholders" || fail "Hardcoded secrets in config"
grep -q '"auth_enabled".*true' config/config.json 2>/dev/null && pass "Dashboard auth enabled" || fail "Dashboard auth DISABLED"
grep -q '"use_signed_urls".*true' config/config.json 2>/dev/null && pass "Signed URLs enabled" || fail "Signed URLs disabled"

# 3. Git security
echo -e "\n3. Git Security:"
git check-ignore .env >/dev/null 2>&1 && pass ".env ignored by Git" || fail ".env NOT in .gitignore"

# 4. Services
echo -e "\n4. Services:"
echo "ℹ️  Dashboard service removed (now separate project)"

# 6. Tests
echo -e "\n6. Tests:"
python3 tests/test_signed_urls.py >/dev/null 2>&1 && pass "Signed URL tests pass" || fail "Tests failed"

# Summary
echo -e "\n=========================================="
echo "SUMMARY: $PASSED passed, $FAILED failed"
echo "=========================================="

[ $FAILED -eq 0 ] && echo "🎉 PRODUCTION READY!" && exit 0
echo "❌ FIX ISSUES ABOVE" && exit 1
