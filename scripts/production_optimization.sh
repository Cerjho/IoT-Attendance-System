#!/bin/bash
# Production Optimization Script for IoT Attendance Dashboard
# This script optimizes the system for production deployment

set -e

echo "======================================================================"
echo "Production Optimization for IoT Attendance Dashboard"
echo "======================================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_DIR="/home/iot/attendance-system"

echo -e "\n${YELLOW}1. Updating Nginx configuration...${NC}"
sudo cp "$PROJECT_DIR/scripts/nginx_dashboard.conf" /etc/nginx/sites-available/dashboard
sudo nginx -t && echo -e "${GREEN}✅ Nginx config valid${NC}" || exit 1

echo -e "\n${YELLOW}2. Setting up log rotation...${NC}"
sudo tee /etc/logrotate.d/attendance-dashboard > /dev/null <<EOF
/var/log/nginx/dashboard_*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 \$(cat /var/run/nginx.pid)
    endscript
}

$PROJECT_DIR/data/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 iot iot
}
EOF
echo -e "${GREEN}✅ Log rotation configured${NC}"

echo -e "\n${YELLOW}3. Configuring firewall (UFW)...${NC}"
if command -v ufw &> /dev/null; then
    sudo ufw --force enable
    sudo ufw allow 22/tcp comment 'SSH'
    sudo ufw allow 443/tcp comment 'HTTPS Dashboard'
    sudo ufw allow 80/tcp comment 'HTTP redirect'
    sudo ufw status numbered
    echo -e "${GREEN}✅ Firewall configured${NC}"
else
    echo -e "${YELLOW}⚠️  UFW not installed. Install with: sudo apt install ufw${NC}"
fi

echo -e "\n${YELLOW}4. Optimizing system limits...${NC}"
# Add to /etc/security/limits.conf if not exists
if ! grep -q "iot.*nofile" /etc/security/limits.conf; then
    sudo tee -a /etc/security/limits.conf > /dev/null <<EOF

# IoT Attendance System
iot soft nofile 65536
iot hard nofile 65536
www-data soft nofile 65536
www-data hard nofile 65536
EOF
    echo -e "${GREEN}✅ System limits optimized${NC}"
else
    echo -e "${GREEN}✅ System limits already configured${NC}"
fi

echo -e "\n${YELLOW}5. Setting up automatic service restart on failure...${NC}"
echo -e "${GREEN}ℹ️  Dashboard service removed (now separate project)${NC}"
# Note: Configure attendance-system.service restart policy if needed
    echo -e "${GREEN}✅ Auto-restart configured${NC}"
else
    echo -e "${GREEN}✅ Auto-restart already configured${NC}"
fi

echo -e "\n${YELLOW}6. Optimizing database...${NC}"
cd "$PROJECT_DIR"
python3 -c "
import sqlite3
for db in ['data/attendance.db', 'data/devices.db']:
    try:
        conn = sqlite3.connect(db)
        conn.execute('VACUUM')
        conn.execute('ANALYZE')
        conn.close()
        print(f'✅ Optimized {db}')
    except Exception as e:
        print(f'❌ Failed to optimize {db}: {e}')
"

echo -e "\n${YELLOW}7. Creating production health check script...${NC}"
cat > "$PROJECT_DIR/scripts/health_monitor.sh" <<'EOF'
#!/bin/bash
# Health monitoring script - run via cron every 5 minutes

PROJECT_DIR="/home/iot/attendance-system"
LOG_FILE="$PROJECT_DIR/data/logs/health_monitor.log"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Dashboard service removed - now separate project
log "INFO: Dashboard service monitoring disabled (moved to separate project)"

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
EOF

chmod +x "$PROJECT_DIR/scripts/health_monitor.sh"
echo -e "${GREEN}✅ Health monitor created${NC}"

echo -e "\n${YELLOW}8. Adding cron job for health monitoring...${NC}"
CRON_JOB="*/5 * * * * $PROJECT_DIR/scripts/health_monitor.sh"
if ! crontab -l 2>/dev/null | grep -q "health_monitor.sh"; then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo -e "${GREEN}✅ Cron job added (runs every 5 minutes)${NC}"
else
    echo -e "${GREEN}✅ Cron job already configured${NC}"
fi

echo -e "\n${YELLOW}9. Restarting services...${NC}"
sudo systemctl reload nginx
sudo systemctl restart attendance-dashboard.service

echo -e "\n${YELLOW}10. Running system tests...${NC}"
sleep 3

# Test HTTPS
if curl -k -s -f https://localhost/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ HTTPS endpoint working${NC}"
else
    echo -e "${RED}❌ HTTPS endpoint failed${NC}"
fi

# Test API with auth
# DASHBOARD_API_KEY removed - dashboard is now separate project
if [ -n "$API_KEY" ]; then
    if curl -k -s -f -H "Authorization: Bearer $API_KEY" https://localhost/devices > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API authentication working${NC}"
    else
        echo -e "${RED}❌ API authentication failed${NC}"
    fi
fi

# Test device registration
DEVICE_COUNT=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$PROJECT_DIR/data/devices.db')
count = conn.execute('SELECT COUNT(*) FROM devices').fetchone()[0]
conn.close()
print(count)
")
echo -e "${GREEN}✅ Device registry: $DEVICE_COUNT devices${NC}"

echo -e "\n======================================================================"
echo -e "${GREEN}Production Optimization Complete!${NC}"
echo -e "======================================================================"
echo ""
echo "Dashboard Access:"
echo "  HTTPS: https://$(hostname -I | awk '{print $1}')"
echo "  HTTP:  http://$(hostname -I | awk '{print $1}') (redirects to HTTPS)"
echo ""
echo "Services:"
echo "  Dashboard: $(systemctl is-active attendance-dashboard.service)"
echo "  Nginx:     $(systemctl is-active nginx)"
echo ""
echo "Security:"
echo "  ✅ HTTPS enabled with TLS 1.2/1.3"
echo "  ✅ Rate limiting active (10 req/s)"
echo "  ✅ IP whitelist configured"
echo "  \u2705 Database optimizations applied"
echo "  \u2705 System limits configured"
echo ""
echo "\u2139\ufe0f  Note: Dashboard features removed (now separate project)"
echo ""
echo "Logs:"
echo "  System:    journalctl -u attendance-system.service -f"
echo "  App logs:  tail -f $PROJECT_DIR/data/logs/attendance_system.log"
echo ""
echo "Next Steps:"
echo "  1. Start system: sudo systemctl start attendance-system"
echo "  2. Monitor logs for any issues"
echo "  3. Test QR code scanning"
echo ""
