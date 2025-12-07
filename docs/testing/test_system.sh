#!/bin/bash
# Comprehensive system test script
# Tests all major features of the IoT Attendance System

set -e

echo "======================================================================"
echo "IoT ATTENDANCE SYSTEM - COMPREHENSIVE FEATURE TEST"
echo "======================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASS=0
FAIL=0
SKIP=0

# Helper functions
test_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((PASS++))
}

test_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((FAIL++))
}

test_skip() {
    echo -e "${YELLOW}⊘ SKIP${NC}: $1"
    ((SKIP++))
}

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs) 2>/dev/null
fi

echo "======================================================================"
echo "TEST 1: Environment & Configuration"
echo "======================================================================"

# Test virtual environment
if [ -d ".venv" ] || [ -d "venv" ]; then
    test_pass "Virtual environment exists"
else
    test_fail "Virtual environment not found"
fi

# Test config file
if [ -f "config/config.json" ]; then
    if python3 -c "import json; json.load(open('config/config.json'))" 2>/dev/null; then
        test_pass "config.json is valid JSON"
    else
        test_fail "config.json has invalid JSON"
    fi
else
    test_fail "config/config.json not found"
fi

# Test .env file
if [ -f ".env" ]; then
    if grep -q "SUPABASE_URL" .env && grep -q "SUPABASE_KEY" .env; then
        test_pass ".env has required variables"
    else
        test_fail ".env missing required variables"
    fi
else
    test_fail ".env file not found"
fi

echo ""
echo "======================================================================"
echo "TEST 2: Dependencies"
echo "======================================================================"

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate 2>/dev/null || true
elif [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || true
fi

# Test Python version
if python3 --version &>/dev/null; then
    test_pass "Python 3 available: $(python3 --version)"
else
    test_fail "Python 3 not found"
fi

# Test critical Python packages
for pkg in opencv-python picamera2 pyzbar requests; do
    if python3 -c "import ${pkg//-/_}" 2>/dev/null; then
        test_pass "Package $pkg installed"
    else
        test_fail "Package $pkg missing"
    fi
done

echo ""
echo "======================================================================"
echo "TEST 3: File Structure"
echo "======================================================================"

# Test critical directories
for dir in data/photos data/logs data/qr_codes src scripts config; do
    if [ -d "$dir" ]; then
        test_pass "Directory $dir exists"
    else
        test_fail "Directory $dir missing"
    fi
done

# Test critical files
for file in attendance_system.py src/camera/camera_handler.py src/cloud/cloud_sync.py; do
    if [ -f "$file" ]; then
        test_pass "File $file exists"
    else
        test_fail "File $file missing"
    fi
done

echo ""
echo "======================================================================"
echo "TEST 4: Database"
echo "======================================================================"

# Test database exists
if [ -f "data/attendance.db" ]; then
    test_pass "Database file exists"
    
    # Test database tables
    if sqlite3 data/attendance.db "SELECT name FROM sqlite_master WHERE type='table';" | grep -q "attendance"; then
        test_pass "Attendance table exists"
    else
        test_fail "Attendance table missing"
    fi
    
    # Test database can be queried
    if sqlite3 data/attendance.db "SELECT COUNT(*) FROM attendance;" &>/dev/null; then
        RECORD_COUNT=$(sqlite3 data/attendance.db "SELECT COUNT(*) FROM attendance;")
        test_pass "Database readable: $RECORD_COUNT records"
    else
        test_fail "Database query failed"
    fi
else
    test_fail "Database file not found"
fi

echo ""
echo "======================================================================"
echo "TEST 5: Camera Detection"
echo "======================================================================"

# Test camera devices
if ls /dev/video* &>/dev/null; then
    test_pass "Video devices found: $(ls /dev/video* | wc -l) devices"
    
    # Check permissions
    if [ -r "/dev/video0" ]; then
        test_pass "Video device readable"
    else
        test_fail "No read permission on video devices"
    fi
else
    test_skip "No video devices detected (okay if no camera)"
fi

# Test camera detection script
if [ -f "scripts/maintenance/detect_cameras.sh" ]; then
    test_pass "Camera detection script exists"
else
    test_fail "Camera detection script missing"
fi

echo ""
echo "======================================================================"
echo "TEST 6: Cloud Connectivity"
echo "======================================================================"

# Test Supabase reachability
if [ -n "$SUPABASE_URL" ]; then
    if curl -s --max-time 5 "$SUPABASE_URL" &>/dev/null; then
        test_pass "Supabase URL reachable"
    else
        test_fail "Cannot reach Supabase URL"
    fi
    
    # Test API key configured
    if [ -n "$SUPABASE_KEY" ] && [ "$SUPABASE_KEY" != '${SUPABASE_KEY}' ]; then
        test_pass "Supabase API key configured"
        
        # Test API connection
        RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null \
            -H "apikey: $SUPABASE_KEY" \
            -H "Authorization: Bearer $SUPABASE_KEY" \
            "$SUPABASE_URL/rest/v1/students?limit=1")
        
        if [ "$RESPONSE" = "200" ]; then
            test_pass "Supabase API connection successful"
        else
            test_fail "Supabase API returned $RESPONSE"
        fi
    else
        test_fail "Supabase API key not configured"
    fi
else
    test_fail "SUPABASE_URL not set"
fi

echo ""
echo "======================================================================"
echo "TEST 7: Scripts"
echo "======================================================================"

# Test critical scripts are executable
for script in scripts/start_attendance.sh scripts/force_sync.py scripts/status.py; do
    if [ -f "$script" ]; then
        if [ -x "$script" ] || [[ "$script" == *.py ]]; then
            test_pass "Script $script exists and runnable"
        else
            test_fail "Script $script not executable"
        fi
    else
        test_fail "Script $script missing"
    fi
done

echo ""
echo "======================================================================"
echo "TEST 8: Python Module Imports"
echo "======================================================================"

# Test critical imports
python3 << 'PYEOF'
import sys
import traceback

modules = [
    ('cv2', 'OpenCV'),
    ('src.camera.camera_handler', 'Camera Handler'),
    ('src.cloud.cloud_sync', 'Cloud Sync'),
    ('src.database.sync_queue', 'Sync Queue'),
    ('src.face_quality', 'Face Quality'),
]

failed = []
for module, name in modules:
    try:
        __import__(module)
        print(f"✓ PASS: Import {name}")
    except Exception as e:
        print(f"✗ FAIL: Import {name} - {str(e)}")
        failed.append(name)

sys.exit(len(failed))
PYEOF

if [ $? -eq 0 ]; then
    test_pass "All critical modules import successfully"
else
    test_fail "Some modules failed to import"
fi

echo ""
echo "======================================================================"
echo "TEST 9: Systemd Service"
echo "======================================================================"

# Test systemd service file
if [ -f "/etc/systemd/system/attendance-system.service" ]; then
    test_pass "Systemd service file exists"
    
    # Check if service is enabled
    if systemctl is-enabled attendance-system &>/dev/null; then
        test_pass "Service is enabled"
    else
        test_skip "Service not enabled (optional)"
    fi
    
    # Check service status
    if systemctl is-active attendance-system &>/dev/null; then
        test_pass "Service is running"
    else
        test_skip "Service not running (okay for manual testing)"
    fi
else
    test_skip "Systemd service not installed (optional)"
fi

echo ""
echo "======================================================================"
echo "TEST 10: Supabase Trigger & Permissions"
echo "======================================================================"

# Test if migration exists
if [ -f "supabase/migrations/20251206120000_fix_iot_devices_permissions.sql" ]; then
    test_pass "Permission fix migration exists"
else
    test_fail "Permission fix migration missing"
fi

# Test enrichment trigger by checking a recent record
if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_KEY" ]; then
    RECENT=$(curl -s \
        -H "apikey: $SUPABASE_KEY" \
        -H "Authorization: Bearer $SUPABASE_KEY" \
        "$SUPABASE_URL/rest/v1/attendance?select=section_id&order=created_at.desc&limit=1")
    
    if echo "$RECENT" | grep -q '"section_id"'; then
        if echo "$RECENT" | grep -q '"section_id":null'; then
            test_skip "Enrichment trigger not populating (device may not be assigned to section)"
        else
            test_pass "Enrichment trigger working (section_id populated)"
        fi
    else
        test_skip "Cannot verify enrichment trigger"
    fi
fi

echo ""
echo "======================================================================"
echo "SUMMARY"
echo "======================================================================"
echo ""
echo -e "${GREEN}PASSED: $PASS${NC}"
echo -e "${RED}FAILED: $FAIL${NC}"
echo -e "${YELLOW}SKIPPED: $SKIP${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo "System is ready for operation."
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo "Please review failed tests above."
    exit 1
fi
