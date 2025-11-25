#!/bin/bash
# Automated Cleanup Wrapper for IoT Attendance System
# Easy-to-use interface for local data cleanup after Supabase sync

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================================================"
echo "IoT ATTENDANCE SYSTEM - AUTOMATED CLEANUP"
echo "======================================================================"
echo ""

# Check virtual environment
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: cd $PROJECT_ROOT && python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"

# Change to project root
cd "$PROJECT_ROOT"

echo "📍 Starting automated cleanup process..."
echo ""

# Run the Python cleanup script
python3 scripts/auto_cleanup.py

echo ""
echo "======================================================================"
echo "For more details, check the cleanup report:"
echo "  ls -lrt data/cleanup_report_*.json | tail -1"
echo "======================================================================"
