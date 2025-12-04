#!/bin/bash
#
# Production Deployment Health Check
# Validates all critical components before going live
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================================================"
echo "PRODUCTION READINESS CHECK"
echo "========================================================================"
echo "Started: $(date)"
echo ""

PASSED=0
FAILED=0
WARNINGS=0

check_pass() {
    echo "✅ $1"
    ((PASSED++))
}

check_fail() {
    echo "❌ $1"
    ((FAILED++))
}

check_warn() {
    echo "⚠️  $1"
    ((WARNINGS++))
}

# 1. Environment Variables
echo "1️⃣  Checking Environment Variables..."
if [ ! -f .env ]; then
    check_fail ".env file not found"
else
    check_pass ".env file exists"
    
    # Check required secrets
    if grep -q "^URL_SIGNING_SECRET=" .env && ! grep -q "^URL_SIGNING_SECRET=your-" .env; then
        check_pass "URL_SIGNING_SECRET configured"
    else
        check_fail "URL_SIGNING_SECRET not set or using example value"
    fi
    
    echo "ℹ️  DASHBOARD_API_KEY removed (dashboard now separate project)"
    
    if grep -q "^SUPABASE_URL=" .env && ! grep -q "^SUPABASE_URL=.*example" .env; then
        check_pass "SUPABASE_URL configured"
    else
        check_fail "SUPABASE_URL not configured"
    fi
    
    if grep -q "^SUPABASE_KEY=" .env && ! grep -q "^SUPABASE_KEY=your-" .env; then
        check_pass "SUPABASE_KEY configured"
    else
        check_fail "SUPABASE_KEY not configured"
    fi
fi

# 2. Configuration Files
echo ""
echo "2️⃣  Checking Configuration Files..."
if [ -f config/config.json ]; then
    check_pass "config.json exists"
    
    # Check for placeholders (should be present)
    if grep -q '${SUPABASE_URL}' config/config.json; then
        check_pass "config.json uses environment placeholders (secure)"
    else
        check_warn "config.json may contain hardcoded secrets"
    fi
    
    # Check signed URLs enabled
    if grep -q '"use_signed_urls".*true' config/config.json; then
        check_pass "Signed URLs enabled"
    else
        check_warn "Signed URLs disabled (consider enabling for production)"
    fi
    
    # Check authentication enabled
    if grep -q '"auth_enabled".*true' config/config.json; then
        check_pass "Dashboard authentication enabled"
    else
        check_fail "Dashboard authentication DISABLED (SECURITY RISK)"
    fi
else
    check_fail "config/config.json not found"
fi

if [ -f config/defaults.json ]; then
    check_pass "defaults.json exists"
else
    check_warn "defaults.json not found (optional)"
fi

# 3. Security: Git Status
echo ""
echo "3️⃣  Checking Git Security..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    # Check if .env is ignored
    if git check-ignore .env > /dev/null 2>&1; then
        check_pass ".env is in .gitignore"
    else
        check_fail ".env NOT ignored by Git (SECURITY RISK)"
    fi
    
    # Check for uncommitted changes
    if [ -z "$(git status --porcelain)" ]; then
        check_pass "No uncommitted changes"
    else
        check_warn "Uncommitted changes detected"
    fi
    
    # Check if on main branch
    BRANCH=$(git branch --show-current)
    if [ "$BRANCH" = "main" ]; then
        check_pass "On main branch"
    else
        check_warn "Not on main branch (current: $BRANCH)"
    fi
else
    check_warn "Not a Git repository"
fi

# 4. Database
echo ""
echo "4️⃣  Checking Database..."
if [ -f data/attendance.db ]; then
    check_pass "attendance.db exists"
    
    # Check database size
    DB_SIZE=$(du -h data/attendance.db | cut -f1)
    echo "   Database size: $DB_SIZE"
    
    # Check tables exist
    if sqlite3 data/attendance.db "SELECT name FROM sqlite_master WHERE type='table';" | grep -q "attendance"; then
        check_pass "attendance table exists"
    else
        check_fail "attendance table missing"
    fi
    
    if sqlite3 data/attendance.db "SELECT name FROM sqlite_master WHERE type='table';" | grep -q "sync_queue"; then
        check_pass "sync_queue table exists"
    else
        check_fail "sync_queue table missing"
    fi
else
    check_warn "attendance.db not found (will be created on first run)"
fi

# 5. Directories
echo ""
echo "5️⃣  Checking Required Directories..."
for dir in data data/logs data/photos data/qr_codes; do
    if [ -d "$dir" ]; then
        check_pass "$dir exists"
    else
        check_warn "$dir missing (will be created)"
        mkdir -p "$dir"
    fi
done

# 6. Disk Space
echo ""
echo "6️⃣  Checking Disk Space..."
DISK_AVAIL=$(df -h . | awk 'NR==2 {print $4}')
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | tr -d '%')

echo "   Available: $DISK_AVAIL (Usage: $DISK_USAGE%)"

if [ "$DISK_USAGE" -lt 80 ]; then
    check_pass "Sufficient disk space"
elif [ "$DISK_USAGE" -lt 90 ]; then
    check_warn "Disk usage high ($DISK_USAGE%)"
else
    check_fail "Disk space critical ($DISK_USAGE%)"
fi

# 7. Network Connectivity
echo ""
echo "7️⃣  Checking Network Connectivity..."
if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
    check_pass "Internet connectivity"
else
    check_warn "No internet connectivity"
fi

# Check Supabase reachable
if [ -f .env ]; then
    SUPABASE_URL=$(grep "^SUPABASE_URL=" .env | cut -d= -f2)
    if [ -n "$SUPABASE_URL" ]; then
        if curl -s --max-time 5 "$SUPABASE_URL" > /dev/null 2>&1; then
            check_pass "Supabase reachable"
        else
            check_warn "Supabase unreachable (offline mode will be used)"
        fi
    fi
fi

# 8. Services
echo ""
echo "8️⃣  Checking System Services..."
echo "ℹ️  Dashboard service removed (now separate project)"

# 9. Python Dependencies
echo ""
echo "9️⃣  Checking Python Dependencies..."
if [ -f requirements.txt ]; then
    check_pass "requirements.txt exists"
    
    # Check if virtual environment exists
    if [ -d venv ] || [ -d .venv ]; then
        check_pass "Virtual environment found"
    else
        check_warn "No virtual environment detected"
    fi
    
    # Try to import critical modules
    if python3 -c "import cv2" 2>/dev/null; then
        check_pass "OpenCV installed"
    else
        check_warn "OpenCV not installed or not accessible"
    fi
    
    if python3 -c "import requests" 2>/dev/null; then
        check_pass "requests library installed"
    else
        check_fail "requests library not installed"
    fi
else
    check_fail "requirements.txt not found"
fi

# 10. API Endpoints
echo ""
echo "🔟 Checking API Endpoints..."
# Dashboard removed - skipping API health check
echo "ℹ️  Dashboard health check removed (now separate project)"

# 11. Test Suite
echo ""
echo "1️⃣1️⃣  Running Critical Tests..."
if [ -f tests/test_signed_urls.py ]; then
    if python3 tests/test_signed_urls.py > /dev/null 2>&1; then
        check_pass "Signed URL tests passed"
    else
        check_fail "Signed URL tests failed"
    fi
else
    check_warn "Signed URL tests not found"
fi

# Summary
echo ""
echo "========================================================================"
echo "SUMMARY"
echo "========================================================================"
echo "✅ Passed:   $PASSED"
echo "⚠️  Warnings: $WARNINGS"
echo "❌ Failed:   $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo "🎉 PRODUCTION READY - All checks passed!"
        exit 0
    else
        echo "⚠️  PRODUCTION READY WITH WARNINGS - Review warnings above"
        exit 0
    fi
else
    echo "❌ NOT PRODUCTION READY - Fix critical issues above"
    exit 1
fi
