#!/bin/bash
# IoT Attendance System - Production Deployment Script
# Run this script on a fresh Raspberry Pi to set up the attendance system

set -e  # Exit on error

echo "=========================================="
echo "IoT Attendance System - Deployment"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo "⚠️  Please do not run as root. Run as regular user with sudo access."
   exit 1
fi

# Configuration
INSTALL_DIR="/home/$USER/attendance-system"
SERVICE_USER="$USER"
VENV_DIR="$INSTALL_DIR/.venv"

echo "📋 Deployment Configuration:"
echo "   Install Directory: $INSTALL_DIR"
echo "   Service User: $SERVICE_USER"
echo "   Virtual Environment: $VENV_DIR"
echo ""

# Step 1: System Updates
echo "🔄 Step 1: Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Step 2: Install System Dependencies
echo "📦 Step 2: Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libatlas-base-dev \
    libopencv-dev \
    python3-opencv \
    git \
    sqlite3 \
    libgpiod2 \
    gpiod \
    nginx \
    supervisor \
    curl \
    wget

# Step 3: Clone Repository (if not already present)
if [ ! -d "$INSTALL_DIR" ]; then
    echo "📥 Step 3: Cloning repository..."
    git clone https://github.com/Cerjho/IoT-Attendance-System.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
else
    echo "📂 Step 3: Repository already exists, pulling latest changes..."
    cd "$INSTALL_DIR"
    git pull origin main
fi

# Step 4: Create Virtual Environment
echo "🐍 Step 4: Creating Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Step 5: Install Python Dependencies
echo "📚 Step 5: Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Step 6: Create Data Directories
echo "📁 Step 6: Creating data directories..."
mkdir -p data/logs
mkdir -p data/photos
mkdir -p data/qr_codes
chmod 755 data
chmod 755 data/logs
chmod 755 data/photos
chmod 755 data/qr_codes

# Step 7: Environment Configuration
echo "🔧 Step 7: Setting up environment configuration..."
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
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
    echo "⚠️  Please edit .env file with your actual credentials!"
    echo "   Run: nano .env"
fi

# Step 8: Configure Camera (Raspberry Pi Camera Module)
echo "📷 Step 8: Configuring camera..."
if ! grep -q "start_x=1" /boot/config.txt 2>/dev/null; then
    echo "Enabling camera in /boot/config.txt..."
    echo "start_x=1" | sudo tee -a /boot/config.txt
    echo "gpu_mem=128" | sudo tee -a /boot/config.txt
    REBOOT_REQUIRED=1
fi

# Step 9: Configure GPIO Permissions
echo "🔌 Step 9: Setting up GPIO permissions..."
sudo usermod -a -G gpio "$SERVICE_USER"
sudo usermod -a -G video "$SERVICE_USER"

# Create udev rule for GPIO access
sudo tee /etc/udev/rules.d/99-gpio.rules > /dev/null << EOF
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger

# Step 10: Create Systemd Service
echo "⚙️  Step 10: Creating systemd service..."
sudo tee /etc/systemd/system/attendance-system.service > /dev/null << EOF
[Unit]
Description=IoT Attendance System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$VENV_DIR/bin/python $INSTALL_DIR/attendance_system.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=attendance-system

# Security
NoNewPrivileges=true
PrivateTmp=true

# Graceful shutdown
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
EOF

# Step 11: Nginx configuration removed (dashboard is separate project)
echo "ℹ️  Step 11: Nginx reverse proxy skipped (dashboard removed)"

# Step 12: Enable Services
echo "🚀 Step 12: Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable attendance-system.service
sudo systemctl enable nginx

# Step 13: Create Maintenance Scripts
echo "🛠️  Step 13: Creating maintenance scripts..."

# Health check script
cat > "$INSTALL_DIR/scripts/healthcheck.sh" << 'EOF'
#!/bin/bash
# Health check for monitoring systems

# Dashboard health check removed (dashboard is now separate project)
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")

if [ "$RESPONSE" -eq 200 ]; then
    echo "OK: System is healthy"
    exit 0
else
    echo "CRITICAL: System health check failed (HTTP $RESPONSE)"
    exit 2
fi
EOF

chmod +x "$INSTALL_DIR/scripts/healthcheck.sh"

# Backup script
cat > "$INSTALL_DIR/scripts/backup.sh" << 'EOF'
#!/bin/bash
# Backup attendance database and photos

BACKUP_DIR="/home/$USER/backups/attendance-system"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"

mkdir -p "$BACKUP_PATH"

# Backup database
echo "Backing up database..."
cp data/attendance.db "$BACKUP_PATH/"

# Backup recent photos (last 7 days)
echo "Backing up recent photos..."
find data/photos -type f -mtime -7 -exec cp {} "$BACKUP_PATH/" \;

# Compress backup
echo "Compressing backup..."
cd "$BACKUP_DIR"
tar -czf "backup_$TIMESTAMP.tar.gz" "backup_$TIMESTAMP"
rm -rf "backup_$TIMESTAMP"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +30 -delete

echo "Backup complete: $BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
EOF

chmod +x "$INSTALL_DIR/scripts/backup.sh"

# Log rotation script
cat > "$INSTALL_DIR/scripts/rotate-logs.sh" << 'EOF'
#!/bin/bash
# Rotate and compress old logs

cd /home/$USER/attendance-system/data/logs

# Compress logs older than 1 day
find . -name "*.log" -type f -mtime +1 -exec gzip {} \;

# Delete compressed logs older than 30 days
find . -name "*.log.gz" -type f -mtime +30 -delete

echo "Log rotation complete"
EOF

chmod +x "$INSTALL_DIR/scripts/rotate-logs.sh"

# Step 14: Setup Cron Jobs
echo "⏰ Step 14: Setting up cron jobs..."
(crontab -l 2>/dev/null | grep -v "attendance-system"; cat << 'EOF'
# IoT Attendance System Maintenance

# Daily backup at 2 AM
0 2 * * * /home/$USER/attendance-system/scripts/backup.sh >> /home/$USER/attendance-system/data/logs/backup.log 2>&1

# Log rotation daily at 3 AM
0 3 * * * /home/$USER/attendance-system/scripts/rotate-logs.sh >> /home/$USER/attendance-system/data/logs/rotation.log 2>&1

# Health check every 5 minutes
*/5 * * * * /home/$USER/attendance-system/scripts/healthcheck.sh >> /home/$USER/attendance-system/data/logs/health.log 2>&1

# Disk cleanup weekly (Sundays at 4 AM)
0 4 * * 0 cd /home/$USER/attendance-system && /home/$USER/attendance-system/.venv/bin/python -c "from src.utils.disk_monitor import DiskMonitor; dm = DiskMonitor({}); dm.auto_cleanup()" >> /home/$USER/attendance-system/data/logs/cleanup.log 2>&1
EOF
) | crontab -

# Step 15: Setup Logrotate
echo "📋 Step 15: Configuring logrotate..."
sudo tee /etc/logrotate.d/attendance-system > /dev/null << EOF
$INSTALL_DIR/data/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 644 $SERVICE_USER $SERVICE_USER
}
EOF

# Step 16: Firewall Configuration (if ufw is installed)
if command -v ufw &> /dev/null; then
    echo "🔥 Step 16: Configuring firewall..."
    sudo ufw allow 22/tcp    # SSH
    # Dashboard ports removed (dashboard is now separate project)
    echo "Firewall rules added. Enable with: sudo ufw enable"
fi

# Step 17: Run Tests
echo "🧪 Step 17: Running tests..."
source "$VENV_DIR/bin/activate"
python -m pytest tests/ -q -m "not hardware" || echo "⚠️  Some tests failed. Review before starting service."

# Step 18: Final Instructions
echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Edit environment variables:"
echo "   nano $INSTALL_DIR/.env"
echo ""
echo "2. Update configuration:"
echo "   nano $INSTALL_DIR/config/config.json"
echo ""
echo "3. Test camera (optional):"
echo "   python $INSTALL_DIR/scripts/camera_smoke_test.py"
echo ""
echo "4. Start the service:"
echo "   sudo systemctl start attendance-system"
echo ""
echo "5. Check service status:"
echo "   sudo systemctl status attendance-system"
echo ""
echo "6. View logs:"
echo "   sudo journalctl -u attendance-system -f"
echo "   tail -f data/logs/attendance_system.log"
echo ""
echo "ℹ️  Note: Admin dashboard removed (now separate project)"
echo ""

if [ -n "$REBOOT_REQUIRED" ]; then
    echo "⚠️  REBOOT REQUIRED to enable camera!"
    echo "   Run: sudo reboot"
    echo ""
fi

echo "📚 Documentation:"
echo "   README: $INSTALL_DIR/README.md"
echo "   Phase 1: $INSTALL_DIR/docs/implementation/PHASE1_ROBUSTNESS_SUMMARY.md"
echo "   Phase 2: $INSTALL_DIR/docs/implementation/PHASE2_IMPROVEMENTS_SUMMARY.md"
echo "   Phase 3: $INSTALL_DIR/docs/implementation/PHASE3_MONITORING_SUMMARY.md"
echo ""
echo "🎉 Deployment successful!"
