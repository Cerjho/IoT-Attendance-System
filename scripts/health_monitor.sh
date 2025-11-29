#!/bin/bash
# Health monitoring script - run via cron every 5 minutes

PROJECT_DIR="/home/iot/attendance-system"
LOG_FILE="$PROJECT_DIR/data/logs/health_monitor.log"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check dashboard service
if ! systemctl is-active --quiet attendance-dashboard.service; then
    log "ERROR: Dashboard service is down, attempting restart..."
    sudo systemctl restart attendance-dashboard.service
    sleep 5
    if systemctl is-active --quiet attendance-dashboard.service; then
        log "SUCCESS: Dashboard service restarted"
    else
        log "CRITICAL: Failed to restart dashboard service"
    fi
fi

# Check Nginx
if ! systemctl is-active --quiet nginx; then
    log "ERROR: Nginx is down, attempting restart..."
    sudo systemctl restart nginx
fi

# Check HTTPS endpoint
if ! curl -k -s -f https://localhost/health > /dev/null 2>&1; then
    log "WARNING: HTTPS health check failed"
fi

# Check disk space (warn if < 1GB free)
FREE_SPACE=$(df /home | awk 'NR==2 {print $4}')
if [ "$FREE_SPACE" -lt 1048576 ]; then
    log "WARNING: Low disk space: ${FREE_SPACE}KB free"
fi

# Cleanup old heartbeats (keep last 7 days)
python3 -c "
import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('$PROJECT_DIR/data/devices.db')
cutoff = (datetime.now() - timedelta(days=7)).isoformat()
deleted = conn.execute('DELETE FROM device_heartbeats WHERE timestamp < ?', (cutoff,)).rowcount
conn.commit()
conn.close()
if deleted > 0:
    print(f'Cleaned up {deleted} old heartbeat records')
" >> "$LOG_FILE" 2>&1
