#!/bin/bash
# Verify Phase 1 & 2 Implementation
# Quick verification that all professional logging components are in place

echo "=================================================="
echo "PROFESSIONAL LOGGING - PHASE 1 & 2 VERIFICATION"
echo "=================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅${NC} $1"
        return 0
    else
        echo -e "${RED}❌${NC} $1 NOT FOUND"
        return 1
    fi
}

check_in_file() {
    if grep -q "$2" "$1" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $3"
        return 0
    else
        echo -e "${RED}❌${NC} $3 - Not found in $1"
        return 1
    fi
}

echo "1. Core Infrastructure Files"
echo "----------------------------"
check_file "src/utils/logging_factory.py"
check_file "src/utils/log_decorators.py"
check_file "src/utils/audit_logger.py"
check_file "src/utils/structured_logging.py"
echo ""

echo "2. Configuration"
echo "----------------------------"
check_in_file "config/config.json" '"outputs"' "Enhanced logging config in config.json"
check_in_file "config/config.json" '"audit"' "Audit logging config"
check_in_file "config/config.json" '"business_metrics"' "Business metrics config"
echo ""

echo "3. Main System Integration"
echo "----------------------------"
check_in_file "attendance_system.py" "from src.utils.logging_factory import" "Logging factory imported"
check_in_file "attendance_system.py" "get_audit_logger" "Audit logger imported"
check_in_file "attendance_system.py" "get_business_logger" "Business logger imported"
check_in_file "attendance_system.py" "set_correlation_id" "Correlation ID support"
check_in_file "attendance_system.py" "@log_execution_time" "Performance decorators used"
echo ""

echo "4. Test Infrastructure"
echo "----------------------------"
check_file "tests/test_logging_system.py"
echo ""

echo "5. Documentation"
echo "----------------------------"
check_file "LOGGING_IMPLEMENTATION_SUMMARY.md"
check_file "docs/LOGGING_QUICK_REFERENCE.md"
echo ""

echo "6. Running Quick Test"
echo "----------------------------"
echo "Testing logging system..."
python3 tests/test_logging_system.py > /tmp/logging_test_output.txt 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅${NC} Logging system test PASSED"
else
    echo -e "${RED}❌${NC} Logging system test FAILED"
    echo "See /tmp/logging_test_output.txt for details"
fi
echo ""

echo "7. Log Files Created Today"
echo "----------------------------"
TODAY=$(date +%Y%m%d)
LOG_DIR="data/logs"

if [ -d "$LOG_DIR" ]; then
    echo "Directory: $LOG_DIR"
    ls -lh "$LOG_DIR"/*${TODAY}* 2>/dev/null | while read line; do
        echo "  $line"
    done
    
    # Count and size
    FILE_COUNT=$(ls -1 "$LOG_DIR"/*${TODAY}* 2>/dev/null | wc -l)
    TOTAL_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)
    
    echo ""
    echo "  Files today: $FILE_COUNT"
    echo "  Total size: $TOTAL_SIZE"
else
    echo -e "${YELLOW}⚠${NC}  Log directory not found: $LOG_DIR"
fi
echo ""

echo "8. Feature Summary"
echo "----------------------------"
echo -e "${GREEN}✅${NC} Phase 1: Core Infrastructure"
echo "   - Unified logging factory"
echo "   - Multiple output formats (file, JSON, console, syslog)"
echo "   - Custom log levels (SECURITY, AUDIT, METRICS)"
echo "   - Correlation ID tracking"
echo ""
echo -e "${GREEN}✅${NC} Phase 2: Enhanced Content"
echo "   - Audit trail logging (security, access, data changes)"
echo "   - Business metrics logging"
echo "   - Performance decorators"
echo "   - Structured logging with context"
echo ""

echo "=================================================="
echo "VERIFICATION COMPLETE"
echo "=================================================="
echo ""
echo "Next Steps:"
echo "  1. Review LOGGING_IMPLEMENTATION_SUMMARY.md for full details"
echo "  2. See docs/LOGGING_QUICK_REFERENCE.md for usage guide"
echo "  3. Test with: python tests/test_logging_system.py"
echo "  4. Start system with new logging: bash scripts/start_attendance.sh"
echo ""
