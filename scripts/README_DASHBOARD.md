# Admin Dashboard - Standalone Mode

This dashboard provides REST API endpoints for monitoring the attendance system without requiring the camera or full attendance system to be running.

## Quick Start

```bash
# Start dashboard (loads .env automatically)
bash scripts/start_dashboard.sh

# Start in background
nohup bash scripts/start_dashboard.sh > /tmp/dashboard.log 2>&1 &

# View logs
tail -f /tmp/dashboard.log

# Stop dashboard
kill $(pgrep -f 'start_dashboard_only.py')
```

## Endpoints

All endpoints are accessible at `http://localhost:8080` or `http://<raspberry-pi-ip>:8080`

### Core Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/health` | GET | Health check | `{"status": "healthy", "timestamp": "..."}` |
| `/status` | GET | System status (online, disk, queue) | JSON |
| `/system/info` | GET | System information (Python, platform) | JSON |

### Data Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/scans/recent` | GET | Recent attendance scans | JSON array |
| `/scans/recent?limit=N` | GET | Recent scans (limited) | JSON array |
| `/queue/status` | GET | Sync queue status | JSON |
| `/config` | GET | Configuration (sanitized) | JSON |

### Metrics Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/metrics` | GET | Metrics in JSON format | JSON |
| `/metrics/prometheus` | GET | Metrics in Prometheus format | Text |

## Example Usage

```bash
# Health check
curl http://localhost:8080/health

# System status
curl http://localhost:8080/status | jq .

# Recent scans (last 10)
curl "http://localhost:8080/scans/recent?limit=10" | jq .

# Queue status
curl http://localhost:8080/queue/status | jq .

# From browser (any device on network)
http://192.168.1.22:8080/health
http://192.168.1.22:8080/status
```

## Deployment Options

### Option 1: Manual Start (Development)

```bash
# Terminal 1: Start dashboard
bash scripts/start_dashboard.sh

# Terminal 2: Test endpoints
curl http://localhost:8080/health
```

### Option 2: Background Process

```bash
# Start in background
nohup bash scripts/start_dashboard.sh > /tmp/dashboard.log 2>&1 &

# Get PID
pgrep -f 'start_dashboard_only.py'

# Stop
kill $(pgrep -f 'start_dashboard_only.py')
```

### Option 3: Systemd Service (Production)

Create `/etc/systemd/system/attendance-dashboard.service`:

```ini
[Unit]
Description=IoT Attendance System - Admin Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=iot
WorkingDirectory=/home/iot/attendance-system
ExecStart=/bin/bash /home/iot/attendance-system/scripts/start_dashboard.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable attendance-dashboard
sudo systemctl start attendance-dashboard
sudo systemctl status attendance-dashboard
```

## Features

✅ **No Camera Required** - Runs without camera/attendance system  
✅ **Lightweight** - Minimal resource usage  
✅ **Environment Variables** - Automatically loads from `.env`  
✅ **CORS Enabled** - Accessible from web applications  
✅ **JSON + Prometheus** - Multiple metric formats  
✅ **Sanitized Config** - Sensitive data redacted  

## Monitoring Integration

### Prometheus

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'attendance_dashboard'
    static_configs:
      - targets: ['192.168.1.22:8080']
    metrics_path: '/metrics/prometheus'
    scrape_interval: 30s
```

### Grafana

Import the metrics from Prometheus and create dashboards for:
- System health
- Sync queue size
- Disk usage
- Scan activity

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8080
sudo lsof -i :8080
# or
sudo netstat -tlnp | grep :8080

# Kill the process
kill <PID>
```

### Environment Variables Not Loaded

Make sure you're using `scripts/start_dashboard.sh` (not direct Python execution) as it loads the `.env` file.

### Database Not Found

The dashboard will still run but `/scans/recent` and `/queue/status` will return empty or error responses. Ensure `data/attendance.db` exists.

## Configuration

Dashboard settings in `config/config.json`:

```json
{
  "admin_dashboard": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8080,
    "auth_enabled": false
  }
}
```

- `host: "0.0.0.0"` - Listen on all interfaces (network accessible)
- `host: "127.0.0.1"` - Local only
- `port: 8080` - Change if port conflict
- `auth_enabled: false` - Future feature for authentication

## Security Notes

⚠️ **No Authentication** - Current version has no auth. Use firewall rules to restrict access.

Recommended firewall setup:

```bash
# Allow from local network only
sudo ufw allow from 192.168.1.0/24 to any port 8080

# Or specific IPs
sudo ufw allow from 192.168.1.100 to any port 8080
```

## Testing

Run comprehensive endpoint tests:

```bash
# Manual test all endpoints
bash /tmp/test_endpoints.sh

# Quick health check
curl -f http://localhost:8080/health && echo "✅ Dashboard OK"
```

All 10 endpoints should return proper responses with correct status codes.
