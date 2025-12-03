# Real-time Monitoring System

Complete real-time monitoring solution with live dashboard, event streaming, and metrics tracking.

## Features

### 📊 Live Dashboard
- **Real-time updates** via Server-Sent Events (SSE)
- **System status** monitoring (camera, cloud, SMS)
- **Today's metrics** (scans, success rate, queue size)
- **Activity chart** (last 10 minutes)
- **Event stream** with color-coded types
- **Alert system** with priority levels
- **Responsive design** works on all devices

### 📈 Metrics Tracking
- Scans today and last hour
- Cloud sync success rate
- Queue size and failed syncs
- System uptime
- Component health status

### 🔔 Alert System
- Automatic alert generation for:
  - High queue size (>50 records)
  - Multiple sync failures (>10 records)
  - Low success rate (<80% with >10 scans)
- Alert deduplication (5-minute window)
- Priority levels: error, warning, info

### 📋 Event Streaming
- Real-time event broadcast to all clients
- Event types: scan, sync, sms, photo, error, warning
- Detailed event context and timestamps
- Automatic reconnection on disconnect

## Quick Start

### 1. Start Monitoring Dashboard Only

```bash
# Start on default port 8888
bash scripts/start_monitor.sh

# Start on custom port
bash scripts/start_monitor.sh 9000
```

Access at: **http://localhost:8888/dashboard**

### 2. Start with Attendance System

The monitoring system starts automatically when you run the attendance system:

```bash
bash scripts/start_attendance.sh
```

Then access dashboard at: **http://localhost:8888/dashboard** (in separate terminal, run start_monitor.sh)

### 3. Integration with Existing Code

The monitoring is already integrated into `attendance_system.py`:

```python
from src.utils.realtime_monitor import get_monitor

# Get monitor instance
monitor = get_monitor()
monitor.start()

# Log events
monitor.log_event("scan", "Attendance recorded", {
    "student_id": "2021001",
    "record_id": 123
})

# Update system state
monitor.update_system_state("camera", "online", "640x480")

# Get metrics
metrics = monitor.get_metrics()
```

## Dashboard Interface

### System Status Card
- Overall system health (Healthy/Degraded/Error/Partial)
- Component status (Camera, Cloud, SMS)
- System uptime

### Metrics Card
- Scans today: Total attendance records
- Last hour: Recent activity
- Success rate: Cloud sync success percentage
- Queue size: Pending sync records
- Failed syncs: Records with retry errors

### Activity Chart
- Visual representation of activity over last 10 minutes
- Updates in real-time as events occur

### Alerts Section
- ⚠️ Warnings (yellow): Non-critical issues
- ❌ Errors (red): Critical problems
- ℹ️ Info (blue): Informational messages

### Events Section
- 🟢 Scan events (green border)
- 🔵 Sync events (blue border)
- 🔴 Error events (red border)
- 🟡 Warning events (yellow border)

## API Endpoints

### GET /api/status
Complete dashboard data including metrics, system state, events, and alerts.

```bash
curl http://localhost:8888/api/status
```

Response:
```json
{
  "timestamp": "2025-12-03T10:30:00",
  "metrics": {
    "scans_today": 45,
    "scans_last_hour": 12,
    "success_rate": 95.5,
    "queue_size": 2,
    "failed_syncs": 0,
    "uptime_seconds": 3600
  },
  "system_state": {
    "status": "healthy",
    "camera_status": "online",
    "cloud_status": "online",
    "sms_status": "online"
  },
  "recent_events": [...],
  "recent_alerts": [...],
  "uptime": "1h 0m"
}
```

### GET /api/metrics
Current metrics only.

```bash
curl http://localhost:8888/api/metrics
```

### GET /api/events
Recent events (last 50).

```bash
curl http://localhost:8888/api/events
```

### GET /api/alerts
Recent alerts (last 20).

```bash
curl http://localhost:8888/api/alerts
```

### GET /api/stream
Server-Sent Events stream for real-time updates.

```bash
curl -N http://localhost:8888/api/stream
```

## Monitoring Integration Points

### 1. Attendance Recording
```python
# In attendance_system.py
record_id = self.database.record_attendance(student_id, photo_path, qr_data)
self.monitor.log_event("scan", f"Attendance recorded: {student_id}", {
    "student_id": student_id,
    "record_id": record_id,
    "scan_type": scan_type,
    "status": status
})
```

### 2. Photo Capture
```python
# After saving photo
self.monitor.log_event("photo", f"Photo saved for {student_id}", {
    "student_id": student_id,
    "filepath": filepath,
    "size_kb": os.path.getsize(filepath) // 1024
})
```

### 3. Cloud Sync
```python
# After sync attempt
if success:
    self.monitor.log_event("sync", f"Cloud sync successful: {student_id}", {
        "record_id": record_id,
        "student_id": student_id
    })
else:
    self.monitor.log_event("warning", f"Cloud sync queued: {student_id}", {
        "record_id": record_id,
        "student_id": student_id
    })
```

### 4. SMS Notifications
```python
# After SMS attempt
if sms_sent:
    self.monitor.log_event("sms", f"SMS sent: {student_id}", {
        "student_id": student_id,
        "phone": parent_phone
    })
else:
    self.monitor.log_event("warning", f"SMS failed: {student_id}", {
        "student_id": student_id,
        "phone": parent_phone
    })
```

### 5. System Status Updates
```python
# Camera status
self.monitor.update_system_state("camera", "online", "640x480")
self.monitor.update_system_state("camera", "error", "Failed to start")

# Cloud status
self.monitor.update_system_state("cloud", "online", "Connected")
self.monitor.update_system_state("cloud", "offline", "No connectivity")

# SMS status
self.monitor.update_system_state("sms", "online", "Ready")
```

## Data Export

Export metrics and events to JSON:

```python
from src.utils.realtime_monitor import get_monitor

monitor = get_monitor()
filepath = monitor.export_metrics()
print(f"Metrics exported to {filepath}")
```

Default export location: `data/metrics_export_YYYYMMDD_HHMMSS.json`

## Monitoring Architecture

### Components

1. **RealtimeMonitor** (`src/utils/realtime_monitor.py`)
   - Core monitoring engine
   - Metrics calculation
   - Event tracking
   - Alert generation
   - Background monitoring loop

2. **Web Dashboard** (`scripts/realtime_dashboard.py`)
   - HTTP server with SSE support
   - HTML/CSS/JavaScript dashboard
   - API endpoints
   - Client connection management

3. **Integration Layer** (`attendance_system.py`)
   - Event logging throughout system flow
   - Status updates for components
   - Automatic monitoring startup

### Data Flow

```
Attendance System → RealtimeMonitor → Web Dashboard → Browser
                         ↓
                    SQLite Metrics
```

### Thread Safety

- All monitor operations are thread-safe with `threading.Lock()`
- Background monitoring runs in daemon thread
- Multiple web clients supported concurrently

## Configuration

No additional configuration required. The monitor uses:
- Database path from attendance system
- Port configurable via command line
- Max events/alerts in memory (100/50)

## Performance

- **Minimal overhead**: Background updates every 5 seconds
- **Memory efficient**: Circular buffers (max 100 events, 50 alerts)
- **Network efficient**: SSE with keepalive every 30 seconds
- **Automatic cleanup**: Old events/alerts removed automatically

## Troubleshooting

### Dashboard not loading
```bash
# Check if port is available
lsof -i :8888

# Check logs
tail -f data/logs/attendance_YYYYMMDD.log | grep -i monitor
```

### No real-time updates
- Check browser console for SSE connection errors
- Verify `/api/stream` endpoint is accessible
- Check firewall allows connections to port

### High memory usage
- Reduce max_events in RealtimeMonitor initialization
- Export and clear old data regularly

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/attendance-monitor.service`:

```ini
[Unit]
Description=IoT Attendance Monitoring Dashboard
After=network.target

[Service]
Type=simple
User=iot
WorkingDirectory=/home/iot/attendance-system
ExecStart=/home/iot/attendance-system/scripts/start_monitor.sh 8888
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable attendance-monitor
sudo systemctl start attendance-monitor
```

### Nginx Reverse Proxy

Add to Nginx config for HTTPS and remote access:

```nginx
location /monitor/ {
    proxy_pass http://localhost:8888/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    proxy_buffering off;
}
```

Access at: `https://your-domain.com/monitor/dashboard`

## Security Considerations

- **Local network only** by default (0.0.0.0 binding)
- **No authentication** (use reverse proxy for auth)
- **Read-only access** (no write operations via API)
- **CORS disabled** (enable if needed for remote access)

For production:
- Add API key authentication
- Use HTTPS (via Nginx/Apache)
- Configure IP whitelist
- Enable rate limiting

## Examples

### Python Integration
```python
from src.utils.realtime_monitor import get_monitor

monitor = get_monitor()

# Log custom event
monitor.log_event("custom", "Custom operation completed", {
    "operation": "backup",
    "duration": 5.2,
    "status": "success"
})

# Get current metrics
metrics = monitor.get_metrics()
print(f"Scans today: {metrics['scans_today']}")
print(f"Success rate: {metrics['success_rate']:.1f}%")

# Subscribe to updates
def my_callback(event_type, data):
    print(f"Event: {event_type} - {data}")

monitor.subscribe(my_callback)
```

### CLI Monitoring
```bash
# Watch metrics in terminal
watch -n 5 'curl -s http://localhost:8888/api/metrics | jq'

# Follow event stream
curl -N http://localhost:8888/api/stream

# Export current metrics
curl -s http://localhost:8888/api/status > dashboard_snapshot.json
```

## Support

For issues or questions:
1. Check logs: `data/logs/attendance_YYYYMMDD.log`
2. Verify monitor is running: `curl http://localhost:8888/api/status`
3. Check system status: `python scripts/status.py`
4. Review documentation: `docs/REALTIME_MONITORING.md`
