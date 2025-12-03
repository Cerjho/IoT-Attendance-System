# Real-time Monitoring - Quick Reference

## 🚀 Start Dashboard

```bash
# Default port (8888)
bash scripts/start_monitor.sh

# Custom port
bash scripts/start_monitor.sh 9000
```

**Access:** http://localhost:8888/dashboard

## 📡 API Endpoints

```bash
# Complete dashboard data
curl http://localhost:8888/api/status | jq

# Current metrics only
curl http://localhost:8888/api/metrics | jq

# Recent events
curl http://localhost:8888/api/events | jq

# Recent alerts
curl http://localhost:8888/api/alerts | jq

# Live event stream (Server-Sent Events)
curl -N http://localhost:8888/api/stream
```

## 🔍 Terminal Monitoring

```bash
# Watch metrics update every 5 seconds
watch -n 5 'curl -s http://localhost:8888/api/metrics | jq'

# Follow live events
curl -N http://localhost:8888/api/stream | grep --line-buffered "data:" | cut -d' ' -f2-

# Save dashboard snapshot
curl -s http://localhost:8888/api/status > dashboard_$(date +%Y%m%d_%H%M%S).json
```

## 🐍 Python Integration

```python
from src.utils.realtime_monitor import get_monitor

# Get monitor instance
monitor = get_monitor()

# Log events
monitor.log_event("scan", "Attendance recorded", {
    "student_id": "2021001",
    "record_id": 123
})

# Update system status
monitor.update_system_state("camera", "online", "640x480")

# Get metrics
metrics = monitor.get_metrics()
print(f"Scans today: {metrics['scans_today']}")

# Export data
filepath = monitor.export_metrics()
```

## 📊 Dashboard Features

### System Status
- **Overall:** Healthy, Degraded, Error, Partial
- **Camera:** Online, Offline, Error
- **Cloud:** Online, Offline
- **SMS:** Online, Offline

### Metrics
- **Scans Today:** Total attendance records
- **Last Hour:** Recent activity
- **Success Rate:** Cloud sync percentage
- **Queue Size:** Pending syncs
- **Failed Syncs:** Retry errors

### Events
- 🟢 **Scan** - Attendance recorded
- 🔵 **Sync** - Cloud sync
- 📧 **SMS** - Notification sent
- 📸 **Photo** - Photo captured
- ⚠️ **Warning** - Non-critical issue
- ❌ **Error** - Critical problem

### Alerts
- ⚠️ **Warning** - Queue high, low success rate
- ❌ **Error** - Multiple failures
- ℹ️ **Info** - System notices

## 🎯 Key Files

```
src/utils/realtime_monitor.py       # Core engine
scripts/realtime_dashboard.py       # Web server
scripts/start_monitor.sh            # Startup script
docs/REALTIME_MONITORING.md         # Full docs
REALTIME_MONITORING_SUMMARY.md      # Implementation summary
```

## 🔧 Production Setup

### Systemd Service

```ini
# /etc/systemd/system/attendance-monitor.service
[Unit]
Description=IoT Attendance Monitoring Dashboard
After=network.target

[Service]
Type=simple
User=iot
WorkingDirectory=/home/iot/attendance-system
ExecStart=/home/iot/attendance-system/scripts/start_monitor.sh 8888
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable attendance-monitor
sudo systemctl start attendance-monitor
```

### Nginx Reverse Proxy

```nginx
location /monitor/ {
    proxy_pass http://localhost:8888/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## 📈 Alert Thresholds

| Condition | Threshold | Level |
|-----------|-----------|-------|
| Queue Size | > 50 records | Warning |
| Failed Syncs | > 10 records | Error |
| Success Rate | < 80% (with >10 scans) | Warning |

## 🛠️ Troubleshooting

```bash
# Check if dashboard is running
lsof -i :8888

# View logs
tail -f data/logs/attendance_*.log | grep -i monitor

# Test monitor import
python -c "from src.utils.realtime_monitor import get_monitor; print('OK')"

# Quick metrics check
curl -s http://localhost:8888/api/metrics | jq '.scans_today'
```

## 📱 Mobile Access

Dashboard is responsive and works on mobile devices. Access from your phone:

```
http://<raspberry-pi-ip>:8888/dashboard
```

Find Pi IP: `hostname -I`

---

**Need help?** See `docs/REALTIME_MONITORING.md` for complete documentation.
