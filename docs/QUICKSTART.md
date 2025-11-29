# IoT Attendance System - Quick Start

Get your attendance system running in production in 15 minutes!

## Prerequisites

- Raspberry Pi 4 (4GB+ RAM recommended)
- Raspberry Pi Camera Module or USB webcam
- MicroSD card (32GB+, Class 10+)
- Network connection (Ethernet or WiFi)
- Monitor and keyboard (for initial setup)

## Option 1: Automated Deployment (Recommended)

### Step 1: Fresh Raspberry Pi OS Installation

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Flash Raspberry Pi OS (64-bit) to SD card
3. Enable SSH during imaging (Raspberry Pi Imager settings)
4. Boot Raspberry Pi and complete initial setup

### Step 2: Run Deployment Script

```bash
# SSH into your Raspberry Pi
ssh pi@<raspberry-pi-ip>

# Download and run deployment script
wget https://raw.githubusercontent.com/Cerjho/IoT-Attendance-System/main/scripts/deployment/deploy.sh
chmod +x deploy.sh
./deploy.sh
```

The script will:
- Install all dependencies ✓
- Set up the application ✓
- Configure services ✓
- Create maintenance jobs ✓

**Time:** ~10-15 minutes

### Step 3: Configure Credentials

```bash
# Edit environment file
nano ~/attendance-system/.env
```

Add your credentials:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DEVICE_ID=pi-lab-01
```

Save with `Ctrl+X`, then `Y`, then `Enter`

### Step 4: Customize Settings (Optional)

```bash
nano ~/attendance-system/config/config.json
```

Update:
- School schedule times
- Camera settings
- Device ID
- Feature toggles

### Step 5: Start the System

```bash
sudo systemctl start attendance-system
sudo systemctl status attendance-system
```

### Step 6: Access Dashboard

Open browser: `http://<raspberry-pi-ip>`

Check health: `http://<raspberry-pi-ip>/health`

**Done!** 🎉

---

## Option 2: Manual Setup

Follow the complete [Deployment Guide](DEPLOYMENT.md) for step-by-step instructions.

---

## First Time Setup Checklist

After deployment:

### 1. Verify Camera
```bash
cd ~/attendance-system
source .venv/bin/activate
python scripts/camera_smoke_test.py
```

### 2. Check Database
```bash
ls -lh ~/attendance-system/data/attendance.db
sqlite3 ~/attendance-system/data/attendance.db "SELECT COUNT(*) FROM attendance;"
```

### 3. Test Cloud Connection
```bash
cd ~/attendance-system
source .venv/bin/activate
python -c "from src.network.connectivity import ConnectivityMonitor; print('Online' if ConnectivityMonitor({}).is_online() else 'Offline')"
```

### 4. Sync Roster (if using Supabase)
```bash
cd ~/attendance-system
source .venv/bin/activate
python utils/test-scripts/test_roster_sync.py
```

### 5. View Logs
```bash
# Real-time logs
sudo journalctl -u attendance-system -f

# Or application logs
tail -f ~/attendance-system/data/logs/attendance_system.log
```

---

## Common Tasks

### Start/Stop Service
```bash
sudo systemctl start attendance-system
sudo systemctl stop attendance-system
sudo systemctl restart attendance-system
```

### View Dashboard
- Open browser: `http://<raspberry-pi-ip>`
- Health: `http://<raspberry-pi-ip>/health`
- Status: `http://<raspberry-pi-ip>/status`
- Metrics: `http://<raspberry-pi-ip>/metrics`

### Check Status
```bash
# Service status
sudo systemctl status attendance-system

# Health check
curl http://localhost:8080/health

# View recent scans
curl http://localhost:8080/scans/recent?limit=10 | python -m json.tool
```

### Backup Data
```bash
~/attendance-system/scripts/backup.sh
```

### Update System
```bash
cd ~/attendance-system
git pull origin main
source .venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart attendance-system
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u attendance-system -n 50

# Test manually
cd ~/attendance-system
source .venv/bin/activate
python attendance_system.py
```

### Camera Not Working
```bash
# Check camera detection
vcgencmd get_camera

# List video devices
ls -l /dev/video*

# Test camera
python ~/attendance-system/scripts/camera_smoke_test.py
```

### Can't Access Dashboard
```bash
# Check nginx
sudo systemctl status nginx

# Check dashboard is running
curl http://localhost:8080/health

# Check firewall
sudo ufw status
```

### Sync Not Working
```bash
# Check queue
sqlite3 ~/attendance-system/data/attendance.db "SELECT COUNT(*) FROM sync_queue;"

# Check connectivity
ping -c 3 google.com

# Check environment
cat ~/attendance-system/.env | grep SUPABASE
```

---

## Network Configuration

### WiFi Setup
```bash
sudo raspi-config
# Navigate to: System Options > Wireless LAN
```

### Static IP (Optional)
```bash
sudo nano /etc/dhcpcd.conf
```

Add:
```
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

### Port Forwarding

To access dashboard remotely, configure your router:
- External Port: 80 or 8080
- Internal IP: `<raspberry-pi-ip>`
- Internal Port: 80

**Security Warning:** Use VPN or reverse proxy (cloudflare tunnel) for secure remote access!

---

## Security Hardening

### Change Default Password
```bash
passwd
```

### Disable Password SSH (Use Keys)
```bash
sudo nano /etc/ssh/sshd_config
```
Set: `PasswordAuthentication no`

### Enable Firewall
```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # Dashboard
sudo ufw enable
sudo ufw status
```

### Auto Security Updates
```bash
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## Production Best Practices

1. **Regular Backups**
   - Automated daily backups (already configured)
   - Test restore procedure
   - Store backups off-device

2. **Monitoring**
   - Set up Prometheus + Grafana
   - Configure alert notifications
   - Monitor disk space

3. **Updates**
   - Schedule monthly update windows
   - Test updates in staging first
   - Keep documentation current

4. **Documentation**
   - Document custom configurations
   - Create runbook for operators
   - Keep contact list updated

5. **Disaster Recovery**
   - Document recovery procedures
   - Keep spare SD card with image
   - Have spare hardware available

---

## Next Steps

After deployment:

1. ✅ **Test All Features**
   - Scan QR codes
   - Verify face detection
   - Check photo capture
   - Test notifications (if enabled)

2. ✅ **Train Operators**
   - How to check system status
   - How to view recent scans
   - How to troubleshoot common issues

3. ✅ **Set Up Monitoring**
   - Configure Prometheus (optional)
   - Set up alert notifications
   - Create dashboards

4. ✅ **Document Custom Settings**
   - School-specific configurations
   - Network details
   - Contact information

---

## Support

- **Full Documentation:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **Troubleshooting:** See deployment guide
- **Updates:** `git pull origin main`
- **Issues:** [GitHub Issues](https://github.com/Cerjho/IoT-Attendance-System/issues)

---

## Quick Reference Card

```
┌─────────────────────────────────────────────┐
│  IoT Attendance System Quick Reference      │
├─────────────────────────────────────────────┤
│ Start:   sudo systemctl start attendance-system
│ Stop:    sudo systemctl stop attendance-system
│ Restart: sudo systemctl restart attendance-system
│ Status:  sudo systemctl status attendance-system
│                                             │
│ Logs:    sudo journalctl -u attendance-system -f
│ Health:  curl http://localhost:8080/health │
│ Dashboard: http://<pi-ip>                   │
│                                             │
│ Backup:  ~/attendance-system/scripts/backup.sh
│ Update:  cd ~/attendance-system && git pull
└─────────────────────────────────────────────┘
```

Print this and keep near your Raspberry Pi! 📋
