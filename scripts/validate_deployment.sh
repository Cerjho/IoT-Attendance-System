#!/bin/bash
# Deployment Validation Script

echo "=================================================================="
echo "🔍 IoT ATTENDANCE SYSTEM - DEPLOYMENT VALIDATION"
echo "=================================================================="
echo ""

ERRORS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# 1. Check virtual environment
echo "[1/12] Checking virtual environment..."
if [ -d ".venv" ] || [ -d "venv" ]; then
    echo -e "  ${GREEN}✅${NC} Virtual environment exists"
else
    echo -e "  ${RED}❌${NC} No virtual environment found"
    ((ERRORS++))
fi

# 2. Check .env file
echo "[2/12] Checking .env file..."
if [ -f ".env" ]; then
    if grep -q "SUPABASE_URL=\${" .env || grep -q "^SUPABASE_URL=$" .env; then
        echo -e "  ${RED}❌${NC} .env has placeholder values"
        ((ERRORS++))
    else
        echo -e "  ${GREEN}✅${NC} .env file configured"
    fi
else
    echo -e "  ${RED}❌${NC} .env file missing"
    ((ERRORS++))
fi

# 3. Check config.json
echo "[3/12] Checking config.json..."
if [ -f "config/config.json" ]; then
    if python3 -m json.tool config/config.json > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} config.json is valid"
    else
        echo -e "  ${RED}❌${NC} config.json is invalid JSON"
        ((ERRORS++))
    fi
else
    echo -e "  ${RED}❌${NC} config.json missing"
    ((ERRORS++))
fi

# 4. Check required directories
echo "[4/12] Checking required directories..."
MISSING_DIRS=""
for dir in data data/photos data/logs config; do
    if [ ! -d "$dir" ]; then
        MISSING_DIRS="$MISSING_DIRS $dir"
    fi
done

if [ -z "$MISSING_DIRS" ]; then
    echo -e "  ${GREEN}✅${NC} All directories exist"
else
    echo -e "  ${YELLOW}⚠️${NC}  Missing:$MISSING_DIRS (will auto-create)"
    ((WARNINGS++))
fi

# 5. Check systemd service
echo "[5/12] Checking systemd service..."
if [ -f "/etc/systemd/system/attendance-system.service" ]; then
    if grep -q "EnvironmentFile" /etc/systemd/system/attendance-system.service 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} Service file configured"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Service missing EnvironmentFile"
        ((WARNINGS++))
    fi
else
    echo -e "  ${YELLOW}⚠️${NC}  Service not installed"
    ((WARNINGS++))
fi

# 6. Check Python dependencies
echo "[6/12] Checking Python dependencies..."
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

MISSING_DEPS=""
# Check cv2 (opencv), numpy, pyzbar, dotenv, requests
if ! python3 -c "import cv2" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS opencv-python"
fi
if ! python3 -c "import numpy" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS numpy"
fi
if ! python3 -c "import pyzbar" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS pyzbar"
fi
if ! python3 -c "import dotenv" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS python-dotenv"
fi
if ! python3 -c "import requests" 2>/dev/null; then
    MISSING_DEPS="$MISSING_DEPS requests"
fi

if [ -z "$MISSING_DEPS" ]; then
    echo -e "  ${GREEN}✅${NC} All dependencies installed"
else
    echo -e "  ${RED}❌${NC} Missing:$MISSING_DEPS"
    ((ERRORS++))
fi

# 7. Check database
echo "[7/12] Checking database..."
if [ -f "data/attendance.db" ]; then
    TABLES=$(sqlite3 data/attendance.db "SELECT name FROM sqlite_master WHERE type='table';" 2>/dev/null)
    if echo "$TABLES" | grep -q "attendance"; then
        echo -e "  ${GREEN}✅${NC} Database configured"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Database missing tables"
        ((WARNINGS++))
    fi
else
    echo -e "  ${YELLOW}⚠️${NC}  No database (will be created)"
    ((WARNINGS++))
fi

# 8. Check Supabase connectivity
echo "[8/12] Checking Supabase connectivity..."
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_KEY" ]; then
        if curl -s --max-time 5 -H "apikey: $SUPABASE_KEY" "$SUPABASE_URL/rest/v1/students?limit=1" > /dev/null 2>&1; then
            echo -e "  ${GREEN}✅${NC} Supabase reachable"
        else
            echo -e "  ${YELLOW}⚠️${NC}  Supabase unreachable"
            ((WARNINGS++))
        fi
    else
        echo -e "  ${YELLOW}⚠️${NC}  Supabase not configured"
        ((WARNINGS++))
    fi
fi

# 9. Check main file syntax
echo "[9/12] Checking Python syntax..."
if python3 -m py_compile attendance_system.py 2>/dev/null; then
    echo -e "  ${GREEN}✅${NC} Main file compiles"
else
    echo -e "  ${RED}❌${NC} Syntax errors in main file"
    ((ERRORS++))
fi

# 10. Check imports
echo "[10/12] Checking imports..."
if python3 -c "import sys; sys.path.insert(0, '.'); from src.database import AttendanceDatabase; from src.cloud import CloudSyncManager" 2>/dev/null; then
    echo -e "  ${GREEN}✅${NC} Critical imports work"
else
    echo -e "  ${RED}❌${NC} Import errors"
    ((ERRORS++))
fi

# 11. Check for hardcoded paths
echo "[11/12] Checking for hardcoded paths..."
HARDCODED=$(grep -r "/home/iot" --include="*.py" src/ attendance_system.py 2>/dev/null | grep -v ".pyc" | wc -l)
if [ "$HARDCODED" -eq "0" ]; then
    echo -e "  ${GREEN}✅${NC} No hardcoded paths"
else
    echo -e "  ${YELLOW}⚠️${NC}  Found $HARDCODED hardcoded path(s)"
    ((WARNINGS++))
fi

# 12. Check file permissions
echo "[12/12] Checking file permissions..."
if [ -x "attendance_system.py" ] || [ -r "attendance_system.py" ]; then
    echo -e "  ${GREEN}✅${NC} File permissions OK"
else
    echo -e "  ${YELLOW}⚠️${NC}  Permission issues"
    ((WARNINGS++))
fi

# Summary
echo ""
echo "=================================================================="
echo "📊 VALIDATION SUMMARY"
echo "=================================================================="

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. sudo systemctl start attendance-system"
    echo "  2. sudo systemctl enable attendance-system"
    echo "  3. sudo systemctl status attendance-system"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS WARNING(S) - DEPLOYMENT POSSIBLE${NC}"
    echo ""
    echo "Review warnings above, then:"
    echo "  sudo systemctl start attendance-system"
    exit 0
else
    echo -e "${RED}❌ $ERRORS ERROR(S) FOUND - FIX BEFORE DEPLOYMENT${NC}"
    [ $WARNINGS -gt 0 ] && echo -e "${YELLOW}   Plus $WARNINGS warning(s)${NC}"
    echo ""
    echo "Fix errors above before deploying"
    exit 1
fi
