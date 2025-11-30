#!/bin/bash
#
# Production Readiness Final Check
# Run this before deploying to production
#

cd "$(dirname "$0")/.."

echo "========================================================================"
echo "PRODUCTION READINESS - FINAL CHECK"
echo "========================================================================"
echo ""

ISSUES=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

fail() {
    echo -e "${RED}❌ $1${NC}"
    ((ISSUES++))
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

# 1. Secrets Check
echo "🔐 Security Configuration:"
if [ ! -f .env ]; then
    fail ".env file missing"
else
    pass ".env file exists"
    
    if [ $(stat -c %a .env) != "600" ]; then
        warn ".env permissions not 600 (run: chmod 600 .env)"
    else
        pass ".env permissions secure (600)"
    fi
    
    if grep -q "^URL_SIGNING_SECRET=" .env && [ $(grep "^URL_SIGNING_SECRET=" .env | wc -c) -gt 50 ]; then
        pass "URL_SIGNING_SECRET configured"
    else
        fail "URL_SIGNING_SECRET missing or too short"
    fi
    
    if grep -q "^DASHBOARD_API_KEY=" .env && [ $(grep "^DASHBOARD_API_KEY=" .env | wc -c) -gt 40 ]; then
        pass "DASHBOARD_API_KEY configured"
    else
        fail "DASHBOARD_API_KEY missing or too short"
    fi
fi

# 2. Configuration
echo ""
echo "⚙️  Configuration Files:"
if [ -f config/config.json ]; then
    pass "config.json exists"
    
    if grep -q '"auth_enabled".*:.*true' config/config.json; then
        pass "Dashboard authentication enabled"
    else
        fail "Dashboard authentication DISABLED (security risk)"
    fi
    
    if grep -q '"use_signed_urls".*:.*true' config/config.json; then
        pass "Signed URLs enabled"
    else
        warn "Signed URLs disabled (consider enabling)"
    fi
    
    if grep -q '${SUPABASE_URL}' config/config.json; then
        pass "Config uses environment placeholders"
    else
        warn "Config may have hardcoded secrets"
    fi
else
    fail "config.json missing"
fi

# 3. Git Security
echo ""
echo "🔒 Git Security:"
if git check-ignore .env >/dev/null 2>&1; then
    pass ".env in .gitignore"
else
    fail ".env NOT in .gitignore (will be committed!)"
fi

if git check-ignore config/config.backup.*.json >/dev/null 2>&1; then
    pass "Backup files ignored"
else
    warn "Backup files may not be ignored"
fi

# 4. Services
echo ""
echo "🖥️  System Services:"
if systemctl is-active --quiet attendance-dashboard 2>/dev/null; then
    pass "Dashboard service running"
else
    warn "Dashboard service not running (may need: sudo systemctl start attendance-dashboard)"
fi

if systemctl is-enabled --quiet attendance-dashboard 2>/dev/null; then
    pass "Dashboard auto-start enabled"
else
    warn "Dashboard won't start on boot (may need: sudo systemctl enable attendance-dashboard)"
fi

# 5. API
echo ""
echo "🌐 API Endpoints:"
if timeout 3 curl -s http://localhost:8080/health >/dev/null 2>&1; then
    pass "Dashboard API responding"
    
    if [ -f .env ]; then
        API_KEY=$(grep "^DASHBOARD_API_KEY=" .env | cut -d= -f2)
        if [ -n "$API_KEY" ]; then
            STATUS=$(timeout 3 curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $API_KEY" http://localhost:8080/status 2>/dev/null || echo "000")
            if [ "$STATUS" = "200" ]; then
                pass "Dashboard authentication working"
            else
                warn "Dashboard auth test failed (HTTP $STATUS)"
            fi
        fi
    fi
else
    warn "Dashboard API not responding (service may not be running)"
fi

# 6. Database
echo ""
echo "💾 Database:"
if [ -f data/attendance.db ]; then
    pass "Database file exists"
    
    SIZE=$(du -h data/attendance.db | cut -f1)
    echo "   Database size: $SIZE"
else
    warn "Database not initialized (will be created on first run)"
fi

# 7. Directories
echo ""
echo "📁 Directory Structure:"
for dir in data data/logs data/photos data/qr_codes; do
    if [ -d "$dir" ]; then
        pass "$dir exists"
    else
        warn "$dir missing (will be created)"
        mkdir -p "$dir"
    fi
done

# 8. Tests
echo ""
echo "🧪 Test Suite:"
if python3 tests/test_signed_urls.py >/dev/null 2>&1; then
    pass "Signed URL tests pass"
else
    fail "Signed URL tests failed"
fi

# 9. Monitoring
echo ""
echo "📊 Monitoring:"
if python3 scripts/monitor.py >/dev/null 2>&1; then
    pass "Monitoring script works"
    
    if [ -f data/logs/monitoring_report.json ]; then
        STATUS=$(cat data/logs/monitoring_report.json | grep -o '"status".*' | cut -d'"' -f4)
        if [ "$STATUS" = "healthy" ]; then
            pass "System health: $STATUS"
        else
            warn "System health: $STATUS (check report)"
        fi
    fi
else
    warn "Monitoring script has issues"
fi

# 10. Network
echo ""
echo "🌍 Network Connectivity:"
if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
    pass "Internet connectivity"
else
    warn "No internet (offline mode will be used)"
fi

# Summary
echo ""
echo "========================================================================"
echo "SUMMARY"
echo "========================================================================"

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}🎉 PRODUCTION READY - All critical checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review warnings above (if any)"
    echo "  2. Start main system: sudo systemctl start attendance-system"
    echo "  3. Monitor logs: sudo journalctl -u attendance-system -f"
    echo "  4. Test QR scan and verify SMS delivery"
    echo ""
    exit 0
else
    echo -e "${RED}❌ NOT PRODUCTION READY - $ISSUES critical issue(s) found${NC}"
    echo ""
    echo "Fix the issues marked with ❌ above before deploying."
    echo ""
    exit 1
fi
