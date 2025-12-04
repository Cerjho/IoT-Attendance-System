# Production Deployment - Quick Reference

> **Note:** Admin dashboard and multi-device management features have been removed. For monitoring, refer to separate monitoring system project. This guide covers the core attendance system only.

## 🚀 Initial Deployment

```bash
cd /home/iot/attendance-system
sudo bash scripts/deploy_production.sh
```

## 📊 System Status

```bash
# Quick health check
bash scripts/production_check.sh

# Detailed monitoring
python3 scripts/monitor.py

# Service status
sudo systemctl status attendance-system
```

## 🔄 Service Management

### Start/Stop
```bash
sudo systemctl start attendance-system
sudo systemctl stop attendance-system
sudo systemctl restart attendance-system
```

### View Logs
```bash
# Live tail
sudo journalctl -u attendance-system -f

# Last 50 lines
sudo journalctl -u attendance-system -n 50

# Errors only
sudo journalctl -u attendance-system -p err
```

## 🔐 Security

### Required Secrets (.env)
```bash
URL_SIGNING_SECRET=<64-char-hex>
SUPABASE_URL=<your-supabase-url>
SUPABASE_KEY=<your-supabase-key>
```

### Permissions
```bash
chmod 600 .env                    # Secure env file
chmod 755 scripts/*.sh            # Make scripts executable
```

## 🔧 Common Commands

### Database Operations
```bash
# Check records
sqlite3 data/attendance.db "SELECT COUNT(*) FROM attendance;"

# Recent scans
sqlite3 data/attendance.db \
  "SELECT * FROM attendance ORDER BY timestamp DESC LIMIT 10;"

# Vacuum database
sqlite3 data/attendance.db "VACUUM;"
```

### Backup
```bash
# Manual backup
cp data/attendance.db backups/attendance_$(date +%Y%m%d).db

# View automatic backups
ls -lh backups/

# Restore
sudo systemctl stop attendance-system
cp backups/attendance_20251130.db data/attendance.db
sudo systemctl start attendance-system
```

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u attendance-system -xe

# Verify config
python3 -c "from src.utils.config_loader import ConfigLoader; ConfigLoader('config/config.json')"

# Check dependencies
source venv/bin/activate
pip list | grep -E "(opencv|requests|pyzbar)"
```

### High Sync Queue
```bash
# Check queue
sqlite3 data/attendance.db \
  "SELECT COUNT(*) FROM sync_queue;"

# Verify connectivity
ping -c 3 ddblgwzylvwuucnpmtzi.supabase.co

# Check cloud config
grep -A 5 '"cloud"' config/config.json
```

## ⚡ Performance

### Reduce Photo Storage
```json
{
  "cloud": {
    "cleanup_photos_after_sync": true
  },
  "disk_monitor": {
    "photo_retention_days": 7
  }
}
```

### Less Verbose Logging
```json
{
  "logging": {
    "level": "WARNING"
  }
}
```

## 🔄 Updates

```bash
cd /home/iot/attendance-system
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart attendance-system
```

## 📞 Emergency Contacts

- **Logs**: `tail -f data/logs/system.log`
- **Health**: `bash scripts/production_check.sh`
- **Stop All**: `sudo systemctl stop attendance-system`
- **GitHub**: https://github.com/Cerjho/IoT-Attendance-System

---

**Last Updated**: 2025-11-30  
**Version**: 1.0.0 (Production Ready)
