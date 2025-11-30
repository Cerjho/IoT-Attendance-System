#!/bin/bash
#
# Production Deployment Script
# Sets up the attendance system for production use
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================================================"
echo "PRODUCTION DEPLOYMENT SETUP"
echo "========================================================================"
echo ""

# Note: Script uses sudo internally for privileged operations

# 1. Create systemd services
echo "1️⃣  Setting up systemd services..."

# Dashboard service
sudo tee /etc/systemd/system/attendance-dashboard.service > /dev/null <<EOF
[Unit]
Description=IoT Attendance System - Admin Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ROOT
ExecStart=/bin/bash $PROJECT_ROOT/scripts/start_dashboard.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Main attendance service
sudo tee /etc/systemd/system/attendance-system.service > /dev/null <<EOF
[Unit]
Description=IoT Attendance System - Main Service
After=network.target attendance-dashboard.service
Requires=attendance-dashboard.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ROOT
ExecStart=/bin/bash $PROJECT_ROOT/scripts/start_attendance.sh --headless
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd services created"

# 2. Enable and start services
echo ""
echo "2️⃣  Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable attendance-dashboard.service
sudo systemctl enable attendance-system.service
echo "✅ Services enabled"

# 3. Configure log rotation
echo ""
echo "3️⃣  Setting up log rotation..."
sudo tee /etc/logrotate.d/attendance-system > /dev/null <<EOF
$PROJECT_ROOT/data/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 $USER $USER
}
EOF
echo "✅ Log rotation configured"

# 4. Set up backup cron job
echo ""
echo "4️⃣  Setting up automatic backups..."
CRON_CMD="0 2 * * * cd $PROJECT_ROOT && python3 scripts/backup.py >> data/logs/backup.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "backup.py"; then
    echo "⚠️  Backup cron job already exists"
else
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ Daily backup scheduled (2:00 AM)"
fi

# 5. Set file permissions
echo ""
echo "5️⃣  Setting file permissions..."
chmod 600 .env
chmod 755 scripts/*.sh
chmod -R 755 src/
mkdir -p data/logs data/photos data/qr_codes
chmod -R 775 data/
echo "✅ Permissions set"

# 6. Create backup script if doesn't exist
if [ ! -f scripts/backup.py ]; then
    echo ""
    echo "6️⃣  Creating backup script..."
    cat > scripts/backup.py <<'PYEOF'
#!/usr/bin/env python3
"""Daily backup script for attendance system"""
import shutil
import os
from datetime import datetime
from pathlib import Path

backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = backup_dir / f"backup_{timestamp}"
backup_path.mkdir()

# Backup database
if Path("data/attendance.db").exists():
    shutil.copy2("data/attendance.db", backup_path / "attendance.db")
    print(f"✅ Database backed up to {backup_path}")

# Backup recent photos (last 7 days)
photos = Path("data/photos")
if photos.exists():
    recent = [p for p in photos.glob("*.jpg") if (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)).days < 7]
    if recent:
        photo_backup = backup_path / "photos"
        photo_backup.mkdir()
        for p in recent:
            shutil.copy2(p, photo_backup / p.name)
        print(f"✅ {len(recent)} recent photos backed up")

# Keep only last 30 backups
backups = sorted(backup_dir.glob("backup_*"))
if len(backups) > 30:
    for old in backups[:-30]:
        shutil.rmtree(old)
    print(f"✅ Cleaned up old backups, kept last 30")
PYEOF
    chmod +x scripts/backup.py
    echo "✅ Backup script created"
fi

# 7. Test configuration
echo ""
echo "7️⃣  Testing configuration..."
if python3 -c "from src.utils.config_loader import ConfigLoader; c = ConfigLoader('config/config.json'); print('Config OK')" 2>/dev/null; then
    echo "✅ Configuration valid"
else
    echo "❌ Configuration test failed"
    exit 1
fi

# 8. Start services
echo ""
echo "8️⃣  Starting services..."
sudo systemctl start attendance-dashboard.service
sleep 3

if systemctl is-active --quiet attendance-dashboard.service; then
    echo "✅ Dashboard service started"
else
    echo "❌ Dashboard service failed to start"
    sudo journalctl -u attendance-dashboard.service -n 20
    exit 1
fi

# 9. Verify API
echo ""
echo "9️⃣  Verifying API endpoints..."
sleep 2
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Dashboard API responding"
else
    echo "⚠️  Dashboard API not responding yet (may still be starting)"
fi

echo ""
echo "========================================================================"
echo "DEPLOYMENT COMPLETE"
echo "========================================================================"
echo ""
echo "Services installed:"
echo "  • attendance-dashboard.service"
echo "  • attendance-system.service"
echo ""
echo "Management commands:"
echo "  sudo systemctl status attendance-dashboard"
echo "  sudo systemctl status attendance-system"
echo "  sudo systemctl start attendance-system    # Start main system"
echo "  sudo systemctl stop attendance-system     # Stop main system"
echo "  sudo systemctl restart attendance-dashboard"
echo ""
echo "Logs:"
echo "  sudo journalctl -u attendance-dashboard -f"
echo "  sudo journalctl -u attendance-system -f"
echo "  tail -f data/logs/system.log"
echo ""
echo "Dashboard:"
echo "  http://localhost:8080"
echo "  http://192.168.1.22:8080 (LAN)"
echo ""
echo "Next steps:"
echo "  1. Start main system: sudo systemctl start attendance-system"
echo "  2. Monitor logs: sudo journalctl -u attendance-system -f"
echo "  3. Test QR code scan"
echo "  4. Verify SMS delivery"
echo ""
