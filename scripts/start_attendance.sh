#!/bin/bash
# Quick start script for IoT Attendance System

echo "======================================================================"
echo "IoT ATTENDANCE SYSTEM - STARTUP"
echo "======================================================================"
echo ""

# Navigate to directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: ./setup_v2.sh"
    exit 1
fi

source venv/bin/activate

# Load environment variables from .env file
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded from .env"
else
    echo "⚠️  Warning: .env file not found"
fi

# Check mode (default to empty for GUI mode)
MODE=${1:-""}

if [ -n "$MODE" ]; then
    echo "Starting attendance system in mode: $MODE"
else
    echo "Starting attendance system (GUI mode)"
fi
echo ""
echo "Workflow:"
echo "  1. Student scans QR code"
echo "  2. Face detected (2 second window)"
echo "  3. Photo captured"
echo "  4. Data uploaded to database"
echo "  5. Return to standby"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "======================================================================"
echo ""

# Run system
if [ -n "$MODE" ]; then
    python attendance_system.py $MODE
else
    python attendance_system.py
fi
