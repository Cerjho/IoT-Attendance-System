#!/bin/bash
# Health check script for monitoring systems
# Note: Dashboard removed - this script is deprecated

LOG_FILE="/var/log/attendance-health.log"
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$timestamp] \u2139\ufe0f  Dashboard removed - health monitoring moved to separate project" | tee -a "$LOG_FILE"
echo "For attendance system health, check: sudo systemctl status attendance-system"
exit 0
