#!/bin/bash
# Quick SMS test after device comes online

echo "=========================================="
echo "QUICK SMS TEST"
echo "=========================================="
echo ""
echo "Make sure your SMS Gateway device is:"
echo "  1. Connected to internet"
echo "  2. SMS-Gate app is running"
echo "  3. Device ID: zmmfTkL3NacdGAfNqwD7q"
echo ""
echo "Press Enter when ready..."
read

source venv/bin/activate
python3 test_simple_flow.py

echo ""
echo "Check logs for SMS status:"
tail -20 logs/attendance_system_20251125.log | grep -i "sms\|notification"
