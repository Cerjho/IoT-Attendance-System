#!/bin/bash
# Health check script for monitoring systems

API_KEY=$(grep DASHBOARD_API_KEY /home/iot/attendance-system/.env | cut -d= -f2)
LOG_FILE="/var/log/attendance-health.log"

timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Check dashboard health
response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $API_KEY" http://localhost:8080/health)
status=$(echo "$response" | tail -1)
body=$(echo "$response" | head -n -1)

if [ "$status" = "200" ]; then
    echo "[$timestamp] ✅ Dashboard healthy" | tee -a "$LOG_FILE"
    exit 0
else
    echo "[$timestamp] ❌ Dashboard unhealthy (HTTP $status)" | tee -a "$LOG_FILE"
    
    # Optional: Send alert (email, SMS, webhook)
    # curl -X POST https://your-alert-webhook.com ...
    
    # Try to restart service
    sudo systemctl restart attendance-dashboard
    echo "[$timestamp] 🔄 Restarted attendance-dashboard service" | tee -a "$LOG_FILE"
    exit 1
fi
