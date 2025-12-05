# IoT Attendance System - Deployment Guide

> **⚠️ Note:** This guide contains references to the removed admin dashboard and multi-device management features. For current deployment instructions, see the main `README.md`. Dashboard-specific sections are now obsolete.

Complete guide for deploying the IoT Attendance System to production.

## Table of Contents
1. [Hardware Requirements](#hardware-requirements)
2. [Quick Deployment](#quick-deployment)
3. [Manual Deployment](#manual-deployment)
4. [Configuration](#configuration)
5. [Service Management](#service-management)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

---

## Hardware Requirements

### Minimum Requirements
- **Raspberry Pi:** 4 Model B (4GB RAM recommended)
- **Camera:** Raspberry Pi Camera Module v2 or v3, or USB webcam
- **Storage:** 32GB microSD card (Class 10 or better)
- **Power:** Official Raspberry Pi 5V 3A USB-C power supply
- **Network:** Ethernet or WiFi connection

### Optional Hardware
- **GPIO Components:**
  - Buzzer (GPIO 23)
  - RGB LED (GPIOs: 22-Red, 27-Green, 17-Blue)
  - Power button (GPIO 17 + GPIO 3, both connected to same button)
- **QR Code Reader:** For faster scanning (optional)

### Recommended Setup
- Raspberry Pi 4B (8GB) for better performance
- Active cooling (fan or heatsink)
- UPS/battery backup for power stability
- Ethernet connection for reliability

---

## Quick Deployment

### Automated Installation

The fastest way to deploy on a fresh Raspberry Pi:

```bash
# 1. Download deployment script
wget https://raw.githubusercontent.com/Cerjho/IoT-Attendance-System/main/scripts/deployment/deploy.sh

# 2. Make it executable
chmod +x deploy.sh

# 3. Run deployment (will prompt for sudo password)
./deploy.sh

# 4. Edit environment variables
nano ~/attendance-system/.env

# 5. Configure settings
nano ~/attendance-system/config/config.json

# 6. Start the service
sudo systemctl start attendance-system

# 7. Access dashboard
# Open browser: http://<raspberry-pi-ip>
```

### What the Script Does
1. Updates system packages
2. Installs dependencies (Python, OpenCV, GPIO libraries)
3. Clones repository to `~/attendance-system`
4. Creates virtual environment
5. Installs Python packages
6. Sets up data directories
7. Creates systemd service
8. Configures Nginx reverse proxy
9. Sets up cron jobs for maintenance
10. Configures log rotation

---

## Manual Deployment

If you prefer step-by-step manual deployment:

### Step 1: System Preparation

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
sudo apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    libatlas-base-dev libopencv-dev python3-opencv \
    git sqlite3 libgpiod2 gpiod \
    nginx supervisor curl wget
```

### Step 2: Clone Repository

```bash
# Clone to home directory
cd ~
git clone https://github.com/Cerjho/IoT-Attendance-System.git attendance-system
cd attendance-system
```

### Step 3: Python Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step 4: Create Data Directories

```bash
mkdir -p data/logs data/photos data/qr_codes
chmod 755 data data/logs data/photos data/qr_codes
```

### Step 5: Environment Configuration

```bash
# Create .env file
cat > .env << 'EOF'
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Device Configuration
DEVICE_ID=pi-lab-01

# SMS Configuration (if enabled)
SMS_USERNAME=your-sms-username
SMS_PASSWORD=your-sms-password
SMS_DEVICE_ID=your-sms-device-id
SMS_API_URL=https://your-sms-api.com/send
EOF

# Edit with your credentials
nano .env
```

### Step 6: Camera Configuration

```bash
# Enable camera (Raspberry Pi Camera Module)
sudo raspi-config
# Navigate to: Interface Options > Camera > Enable

# Or manually edit config
echo "start_x=1" | sudo tee -a /boot/config.txt
echo "gpu_mem=128" | sudo tee -a /boot/config.txt

# Reboot required
sudo reboot
```

### Step 7: GPIO Permissions

```bash
# Add user to GPIO and video groups
sudo usermod -a -G gpio $USER
sudo usermod -a -G video $USER

# Create udev rule
sudo tee /etc/udev/rules.d/99-gpio.rules > /dev/null << EOF
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger

# Logout and login for group changes to take effect
```

### Step 8: Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/attendance-system.service
```

```ini
[Unit]
Description=IoT Attendance System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=YOUR_USERNAME
Group=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/attendance-system
Environment="PATH=/home/YOUR_USERNAME/attendance-system/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/YOUR_USERNAME/attendance-system/.env
ExecStart=/home/YOUR_USERNAME/attendance-system/.venv/bin/python /home/YOUR_USERNAME/attendance-system/attendance_system.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=attendance-system

NoNewPrivileges=true
PrivateTmp=true
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable attendance-system
sudo systemctl start attendance-system
```

### Step 9: Nginx Configuration

```bash
# Create nginx config
sudo nano /etc/nginx/sites-available/attendance-dashboard
```

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /health {
        proxy_pass http://127.0.0.1:8080/health;
        access_log off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/attendance-dashboard /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

---

## Configuration

### Required Settings

Edit `config/config.json`:

1. **Device ID:**
```json
{
  "cloud": {
    "device_id": "pi-lab-01"
  }
}
```

2. **Camera Index:**
```json
{
  "camera": {
    "index": 0  // 0 for /dev/video0, 1 for /dev/video1
  }
}
```

3. **School Schedule:**
```json
{
  "school_schedule": {
    "morning_class": {
      "start_time": "07:00",
      "login_window_start": "06:30",
      "login_window_end": "07:30"
    }
  }
}
```

### Environment Variables

Edit `.env` file:

```bash
# Required
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_anon_key_here
DEVICE_ID=pi-lab-01

# Optional SMS
SMS_USERNAME=your_username
SMS_PASSWORD=your_password
SMS_DEVICE_ID=device_123
SMS_API_URL=https://api.sms-provider.com/send
```

### Enable/Disable Features

```json
{
  "cloud": {
    "enabled": true,
    "sync_on_capture": true
  },
  "metrics": {
    "enabled": true
  },
  "admin_dashboard": {
    "enabled": true,
    "port": 8080
  },
  "alerts": {
    "enabled": true,
    "sms": {
      "enabled": false  // Enable for SMS alerts
    }
  },
  "buzzer": {
    "enabled": true  // Disable if no buzzer connected
  },
  "rgb_led": {
    "enabled": true  // Disable if no LED connected
  }
}
```

---

## Service Management

### Basic Commands

```bash
# Start service
sudo systemctl start attendance-system

# Stop service
sudo systemctl stop attendance-system

# Restart service
sudo systemctl restart attendance-system

# Check status
sudo systemctl status attendance-system

# Enable auto-start on boot
sudo systemctl enable attendance-system

# Disable auto-start
sudo systemctl disable attendance-system

# View logs (real-time)
sudo journalctl -u attendance-system -f

# View logs (last 100 lines)
sudo journalctl -u attendance-system -n 100

# View logs (since boot)
sudo journalctl -u attendance-system -b
```

### Application Logs

```bash
# All logs
tail -f ~/attendance-system/data/logs/*.log

# Specific log
tail -f ~/attendance-system/data/logs/attendance_system.log

# Error logs only
grep ERROR ~/attendance-system/data/logs/*.log

# Alert logs
tail -f ~/attendance-system/data/logs/alerts.log
```

---

## Monitoring

### Admin Dashboard

Access at: `http://<raspberry-pi-ip>`

**Endpoints:**
- `/health` - Health check
- `/status` - System status
- `/metrics` - Metrics (JSON)
- `/metrics/prometheus` - Prometheus format
- `/scans/recent` - Recent scans
- `/queue/status` - Sync queue status
- `/config` - Configuration (sanitized)

### Health Checks

```bash
# Manual health check
curl http://localhost:8080/health

# Automated (cron runs every 5 minutes)
~/attendance-system/scripts/healthcheck.sh

# Check health log
tail -f ~/attendance-system/data/logs/health.log
```

### Prometheus Integration

If using Prometheus for monitoring:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'attendance_system'
    static_configs:
      - targets: ['raspberry-pi-ip:8080']
    metrics_path: '/metrics/prometheus'
    scrape_interval: 30s
```

### System Metrics

```bash
# Check disk usage
df -h ~/attendance-system/data

# Check memory usage
free -h

# Check CPU temperature
vcgencmd measure_temp

# Check system load
uptime

# Check network connectivity
ping -c 3 google.com
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u attendance-system -n 50

# Check configuration
python3 -c "import json; json.load(open('config/config.json'))"

# Check environment
source .venv/bin/activate
python -c "import sys; print(sys.version)"

# Check dependencies
pip list

# Test manually
cd ~/attendance-system
source .venv/bin/activate
python attendance_system.py
```

### Camera Issues

```bash
# List cameras
v4l2-ctl --list-devices

# Test camera
python ~/attendance-system/scripts/camera_smoke_test.py

# Check permissions
groups | grep video

# Check camera config
vcgencmd get_camera

# Expected output: supported=1 detected=1
```

### GPIO Issues

```bash
# Check GPIO groups
groups | grep gpio

# Test GPIO (if power button enabled)
gpioinfo

# Check udev rules
cat /etc/udev/rules.d/99-gpio.rules
```

### Network/Cloud Sync Issues

```bash
# Check connectivity
python -c "from src.network.connectivity import ConnectivityMonitor; print(ConnectivityMonitor({}).is_online())"

# Check sync queue
sqlite3 ~/attendance-system/data/attendance.db "SELECT COUNT(*) FROM sync_queue;"

# Force sync
cd ~/attendance-system
source .venv/bin/activate
python -c "from src.cloud.cloud_sync import CloudSyncManager; from src.utils.config_loader import load_config; CloudSyncManager(load_config(), None, None).force_sync_all()"

# Check circuit breaker status
curl http://localhost:8080/status | python -m json.tool
```

### Database Issues

```bash
# Check database
sqlite3 ~/attendance-system/data/attendance.db ".schema"

# Check recent records
sqlite3 ~/attendance-system/data/attendance.db "SELECT * FROM attendance ORDER BY timestamp DESC LIMIT 10;"

# Check queue
sqlite3 ~/attendance-system/data/attendance.db "SELECT * FROM sync_queue;"

# Backup database
cp ~/attendance-system/data/attendance.db ~/attendance.db.backup
```

### Disk Space Issues

```bash
# Check disk usage
df -h

# Manual cleanup
cd ~/attendance-system
source .venv/bin/activate
python -c "from src.utils.disk_monitor import DiskMonitor; dm = DiskMonitor({}); print(dm.auto_cleanup())"

# Check photo storage
du -sh ~/attendance-system/data/photos

# Check log storage
du -sh ~/attendance-system/data/logs
```

---

## Maintenance

### Daily Maintenance

**Automated (via cron):**
- Health checks every 5 minutes
- Daily backup at 2 AM
- Log rotation at 3 AM
- Weekly disk cleanup on Sundays

### Manual Backup

```bash
# Run backup script
~/attendance-system/scripts/backup.sh

# Check backups
ls -lh ~/backups/attendance-system/

# Restore from backup
tar -xzf ~/backups/attendance-system/backup_YYYYMMDD_HHMMSS.tar.gz
cp backup_*/attendance.db ~/attendance-system/data/
```

### Updates

```bash
# Pull latest changes
cd ~/attendance-system
git pull origin main

# Update dependencies
source .venv/bin/activate
pip install --upgrade -r requirements.txt

# Run tests
pytest tests/ -q -m "not hardware"

# Restart service
sudo systemctl restart attendance-system
```

### Log Rotation

```bash
# Manual rotation
~/attendance-system/scripts/rotate-logs.sh

# Check rotated logs
ls -lh ~/attendance-system/data/logs/*.gz

# View compressed log
zcat ~/attendance-system/data/logs/attendance_system.log.gz | tail -100
```

### Database Maintenance

```bash
# Vacuum database (reclaim space)
sqlite3 ~/attendance-system/data/attendance.db "VACUUM;"

# Analyze database (optimize queries)
sqlite3 ~/attendance-system/data/attendance.db "ANALYZE;"

# Check database integrity
sqlite3 ~/attendance-system/data/attendance.db "PRAGMA integrity_check;"
```

### Security Updates

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Update Python packages
cd ~/attendance-system
source .venv/bin/activate
pip list --outdated
pip install --upgrade <package-name>

# Reboot if kernel updated
sudo reboot
```

---

## Production Checklist

Before going live:

- [ ] Hardware properly connected and tested
- [ ] Camera working and focused
- [ ] GPIO components (buzzer, LED) tested
- [ ] `.env` file configured with production credentials
- [ ] `config.json` customized for your school
- [ ] Database initialized and accessible
- [ ] Supabase project configured and accessible
- [ ] Roster synced from cloud
- [ ] Network connectivity stable
- [ ] Service starts automatically on boot
- [ ] Logs rotating properly
- [ ] Backups scheduled and tested
- [ ] Admin dashboard accessible
- [ ] Health checks passing
- [ ] Metrics being collected
- [ ] Alerts configured (if desired)
- [ ] Monitoring set up (Prometheus/Grafana)
- [ ] Firewall configured
- [ ] SSH access secured
- [ ] System updated to latest packages
- [ ] Documentation accessible to operators

---

## Support

- **Documentation:** See `docs/` directory
- **GitHub Issues:** https://github.com/Cerjho/IoT-Attendance-System/issues
- **Phase Guides:**
  - Phase 1: Robustness features
  - Phase 2: Operational improvements
  - Phase 3: Monitoring and alerting

---

## Quick Reference

```bash
# Service
sudo systemctl {start|stop|restart|status} attendance-system

# Logs
sudo journalctl -u attendance-system -f
tail -f ~/attendance-system/data/logs/*.log

# Dashboard
http://<pi-ip>/

# Health
curl http://localhost:8080/health

# Backup
~/attendance-system/scripts/backup.sh

# Update
cd ~/attendance-system && git pull && sudo systemctl restart attendance-system
```
