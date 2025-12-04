# Production Deployment Guide

> **⚠️ Note:** This guide contains references to the removed admin dashboard features. For current production deployment, refer to the main `README.md`. Dashboard-specific commands and endpoints are no longer available.

## Quick Start

### 1. Deploy to Production

```bash
cd /home/iot/attendance-system
sudo bash scripts/deploy_production.sh
```

This automatically:
- ✅ Creates systemd services
- ✅ Configures log rotation
- ✅ Sets up automatic backups (2 AM daily)
- ✅ Sets secure file permissions
- ✅ Starts dashboard service

### 2. Start Main System

```bash
sudo systemctl start attendance-system
```

### 3. Monitor Status

```bash
# Check services
sudo systemctl status attendance-dashboard
sudo systemctl status attendance-system

# View logs
sudo journalctl -u attendance-system -f

# Quick health check
bash scripts/quick_check.sh
```

## Service Management

### Start/Stop Services

```bash
# Dashboard
sudo systemctl start attendance-dashboard
sudo systemctl stop attendance-dashboard
sudo systemctl restart attendance-dashboard

# Main system
sudo systemctl start attendance-system
sudo systemctl stop attendance-system
sudo systemctl restart attendance-system
```

### Enable/Disable Auto-start

```bash
# Enable (start on boot)
sudo systemctl enable attendance-dashboard
sudo systemctl enable attendance-system

# Disable
sudo systemctl disable attendance-dashboard
sudo systemctl disable attendance-system
```

### View Logs

```bash
# Live tail
sudo journalctl -u attendance-dashboard -f
sudo journalctl -u attendance-system -f

# Last 100 lines
sudo journalctl -u attendance-system -n 100

# Errors only
sudo journalctl -u attendance-system -p err

# Since specific time
sudo journalctl -u attendance-system --since "1 hour ago"
```

## Monitoring

### Automated Monitoring

```bash
# Run health check
python3 scripts/monitor.py

# View report
cat data/logs/monitoring_report.json
```

### Add to Cron (Optional)

```bash
# Check every hour
echo "0 * * * * cd /home/iot/attendance-system && python3 scripts/monitor.py >> data/logs/monitor.log 2>&1" | crontab -
```

### Dashboard Monitoring

```bash
# Health check
curl http://localhost:8080/health

# System status (requires API key)
curl -H "Authorization: Bearer $DASHBOARD_API_KEY" http://localhost:8080/status

# Recent scans
curl -H "Authorization: Bearer $DASHBOARD_API_KEY" http://localhost:8080/scans/recent

# Queue status
curl -H "Authorization: Bearer $DASHBOARD_API_KEY" http://localhost:8080/queue/status
```

## Backup & Recovery

### Manual Backup

```bash
# Backup database
cp data/attendance.db backups/attendance_$(date +%Y%m%d).db

# Backup photos
tar -czf backups/photos_$(date +%Y%m%d).tar.gz data/photos/

# Backup config
tar -czf backups/config_$(date +%Y%m%d).tar.gz config/ .env
```

### Automated Backups

Backups run automatically at 2:00 AM daily via cron:
```bash
# Check cron job
crontab -l | grep backup

# View backup logs
tail -f data/logs/backup.log

# List backups
ls -lh backups/
```

### Restore from Backup

```bash
# Stop services
sudo systemctl stop attendance-system

# Restore database
cp backups/attendance_20251130.db data/attendance.db

# Restart
sudo systemctl start attendance-system
```

## Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status attendance-system

# View full logs
sudo journalctl -u attendance-system -xe

# Check config
python3 -c "from src.utils.config_loader import ConfigLoader; ConfigLoader('config/config.json')"

# Check .env
cat .env | grep -E "^(SUPABASE|URL_SIGNING|DASHBOARD)"
```

### Dashboard Not Responding

```bash
# Check if port 8080 in use
sudo netstat -tulpn | grep 8080

# Restart dashboard
sudo systemctl restart attendance-dashboard

# Check logs
sudo journalctl -u attendance-dashboard -n 50
```

### Sync Queue Growing

```bash
# Check queue size
sqlite3 data/attendance.db "SELECT COUNT(*) FROM sync_queue WHERE synced=0;"

# Check connectivity
ping -c 3 ddblgwzylvwuucnpmtzi.supabase.co

# Force sync (requires system running)
# Will auto-sync when online
```

### High Disk Usage

```bash
# Check usage
df -h

# Find large files
du -h data/ | sort -hr | head -10

# Clean old photos (if cleanup enabled)
python3 -c "from src.utils.disk_monitor import DiskMonitor; dm = DiskMonitor({}); dm.auto_cleanup()"

# Manual cleanup
find data/photos -mtime +30 -delete  # Delete photos older than 30 days
find data/logs -name "*.log" -mtime +7 -delete  # Delete old logs
```

## Security Checklist

- [x] `.env` file permissions set to 600
- [x] Dashboard authentication enabled
- [x] API key configured and secure (32+ chars)
- [x] URL signing enabled
- [x] Secrets use environment variables (no hardcoding)
- [x] `.env` in `.gitignore`
- [x] IP whitelist configured
- [x] HTTPS recommended for remote access
- [ ] Rotate secrets every 90 days
- [ ] Monitor logs for unauthorized access
- [ ] Keep system updated

## Performance Optimization

### Reduce Photo Storage

Edit `config/config.json`:
```json
{
  "cloud": {
    "cleanup_photos_after_sync": true  // Delete after upload
  },
  "disk_monitor": {
    "photo_retention_days": 7  // Keep only 7 days
  }
}
```

### Optimize Database

```bash
# Vacuum database (reclaim space)
sqlite3 data/attendance.db "VACUUM;"

# Analyze for query optimization
sqlite3 data/attendance.db "ANALYZE;"
```

### Reduce Logging

Edit `config/config.json`:
```json
{
  "logging": {
    "level": "WARNING"  // Less verbose
  }
}
```

## Updates & Maintenance

### Update System

```bash
cd /home/iot/attendance-system

# Pull latest code
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart services
sudo systemctl restart attendance-dashboard
sudo systemctl restart attendance-system
```

### Verify After Update

```bash
# Run tests
python3 tests/test_signed_urls.py

# Check health
bash scripts/quick_check.sh

# Monitor logs
sudo journalctl -u attendance-system -f
```

## Production Metrics

### Key Performance Indicators

```bash
# Scans per day
sqlite3 data/attendance.db "SELECT DATE(timestamp), COUNT(*) FROM attendance GROUP BY DATE(timestamp) ORDER BY DATE(timestamp) DESC LIMIT 7;"

# Sync success rate
sqlite3 data/attendance.db "SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN synced=1 THEN 1 ELSE 0 END) as synced,
  ROUND(SUM(CASE WHEN synced=1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM attendance;"

# Average sync delay
sqlite3 data/attendance.db "SELECT AVG(CAST((JULIANDAY(synced_at) - JULIANDAY(timestamp)) * 24 * 60 AS INT)) as avg_delay_minutes FROM attendance WHERE synced=1 AND synced_at IS NOT NULL;"
```

### Prometheus Metrics (Optional)

Access at: `http://localhost:8080/metrics/prometheus`

## Support

### Get Help

1. Check logs: `sudo journalctl -u attendance-system -f`
2. Run health check: `bash scripts/quick_check.sh`
3. Review documentation: `docs/`
4. Check GitHub issues: https://github.com/Cerjho/IoT-Attendance-System/issues

### Report Issues

Include:
- Output of `bash scripts/quick_check.sh`
- Relevant logs from `sudo journalctl -u attendance-system -n 100`
- System info: `uname -a` and `python3 --version`
