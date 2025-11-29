# Multi-Device Management Guide

## Overview

The IoT Attendance System now supports centralized management of multiple devices across your school. One super admin can monitor, configure, and control all attendance devices from a single dashboard.

## Architecture

```
┌─────────────────────────────────────────┐
│   Super Admin Dashboard                 │
│   (Central Management Server)           │
│   - Device Registry                     │
│   - Fleet Monitoring                    │
│   - Bulk Operations                     │
└──────────────┬──────────────────────────┘
               │
      ┌────────┴────────┬─────────────┐
      │                 │             │
┌─────▼─────┐    ┌─────▼─────┐  ┌───▼──────┐
│ Device 1  │    │ Device 2  │  │ Device N │
│ Building A│    │ Building B│  │ Lab 301  │
│ Floor 1   │    │ Floor 2   │  │          │
└───────────┘    └───────────┘  └──────────┘
```

### Key Features

- **Centralized Monitoring**: View status of all devices from one dashboard
- **Auto-Discovery**: Scan network to find devices automatically  
- **Location Hierarchy**: Organize devices by building/floor/room
- **Bulk Operations**: Send commands to multiple devices simultaneously
- **Aggregated Metrics**: Total scans, queue size, issues across fleet
- **Real-time Status**: Heartbeat monitoring with auto-offline detection
- **Device Groups**: Logical grouping for management purposes

---

## Quick Start

### 1. Enable Multi-Device Management

Edit `config/config.json`:

```json
{
  "device_id": "central-dashboard",
  "device_name": "Central Management Server",
  "admin_dashboard": {
    "enabled": true,
    "auth_enabled": true,
    "port": 8080,
    "multi_device_enabled": true  // ← Enable this
  },
  "location": {
    "building": "Admin Building",
    "floor": "IT Office",
    "room": "Server Room"
  }
}
```

### 2. Start Dashboard with Multi-Device Support

```bash
# Start central dashboard
bash scripts/start_dashboard.sh

# Verify multi-device endpoints available
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8080/devices
```

### 3. Configure Other Devices

On each attendance device, edit `config/config.json`:

```json
{
  "device_id": "device-building-a-floor-1",
  "device_name": "Building A - Floor 1 Entrance",
  "admin_dashboard": {
    "enabled": true,
    "auth_enabled": true,
    "port": 8080
  },
  "location": {
    "building": "Building A",
    "floor": "Floor 1",
    "room": "Main Entrance",
    "description": "Building A - Floor 1 Main Entrance"
  }
}
```

**Important**: Each device MUST have:
- Unique `device_id`
- Descriptive `device_name`
- Location information (building/floor/room)

---

## Device Discovery

### Automatic Network Discovery

Scan your school network to find all devices:

```bash
# Discover devices on network
curl -H "Authorization: Bearer $API_KEY" \
  "http://192.168.1.22:8080/devices/discover?network=192.168.1.0/24"
```

**Response:**
```json
{
  "discovered": 5,
  "registered": 5,
  "devices": [
    {
      "device_id": "device-building-a-floor-1",
      "device_name": "pi-lab-01",
      "ip_address": "192.168.1.100",
      "port": 8080,
      "status": "online"
    },
    ...
  ],
  "timestamp": "2025-11-29T20:30:00"
}
```

### Manual Device Registration

Register a device manually:

```bash
curl -X POST http://192.168.1.22:8080/devices/register \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device-building-b-floor-2",
    "device_name": "Building B - Floor 2 Lab",
    "ip_address": "192.168.1.150",
    "building": "Building B",
    "floor": "Floor 2",
    "room": "Computer Lab",
    "location": "Building B - Floor 2 Computer Lab"
  }'
```

---

## API Endpoints

### Device Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/devices` | List all registered devices |
| GET | `/devices?status=online` | Filter devices by status |
| GET | `/devices?building=Building A` | Filter by building |
| GET | `/devices/discover?network=192.168.1.0/24` | Auto-discover devices |
| POST | `/devices/register` | Register new device |
| POST | `/devices/heartbeat` | Device heartbeat report |

### Device Status & Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/devices/status` | Status of all devices |
| GET | `/devices/metrics` | Aggregated fleet metrics |
| GET | `/devices/{id}/status` | Specific device status |
| GET | `/devices/{id}/command/{cmd}` | Send command to device |
| GET | `/locations` | Device location hierarchy |

### Available Commands

- `status` - Get device status
- `health` - Health check
- `config` - View configuration  
- `metrics` - Get metrics
- `scans` - Recent scans
- `queue` - Queue status

---

## Fleet Monitoring Dashboard

### React Component

Use the provided React components:

```jsx
import { MultiDeviceDashboard } from './MultiDeviceDashboard';

function App() {
  return (
    <MultiDeviceDashboard
      baseURL="http://192.168.1.22:8080"
      apiKey="your-api-key-here"
    />
  );
}
```

Components included:
- **FleetOverview** - Summary cards (total, online, offline, issues)
- **DeviceList** - Grid of device cards with filtering
- **DeviceCard** - Individual device status and actions
- **DeviceDiscovery** - Network scanning UI
- **DeviceLocationTree** - Building/floor/room hierarchy

### Example Screens

**Fleet Overview:**
```
┌────────────┬────────────┬────────────┬────────────┐
│🖥️ Total   │✅ Online   │❌ Offline  │⚠️ Issues   │
│    12      │     10     │      2     │      1     │
└────────────┴────────────┴────────────┴────────────┘
```

**Device Grid:**
```
┌──────────────────────┬──────────────────────┐
│ Building A - Floor 1 │ Building A - Floor 2 │
│ 📍 Main Entrance     │ 📍 Library           │
│ 🌐 192.168.1.100     │ 🌐 192.168.1.101     │
│ ✅ Online            │ ✅ Online            │
│ 💓 2m ago            │ 💓 1m ago            │
│ 📊 45 scans          │ 📊 32 scans          │
└──────────────────────┴──────────────────────┘
```

---

## Device Configuration

### Location Hierarchy

Organize devices using 3-level hierarchy:

```
Building
  └── Floor
       └── Room
```

**Example:**
```
Building A
  ├── Floor 1
  │   ├── Main Entrance (2 devices)
  │   └── Hallway (1 device)
  └── Floor 2
      ├── Computer Lab (1 device)
      └── Library (1 device)
```

### Configuration Best Practices

1. **Device IDs**: Use descriptive pattern
   - Format: `device-{building}-{floor}-{room}`
   - Example: `device-building-a-floor-1-entrance`

2. **Device Names**: Human-readable
   - Format: `{Building} - {Floor} {Room}`
   - Example: `Building A - Floor 1 Main Entrance`

3. **IP Addresses**: Use static IPs or DHCP reservations
   - Reserve IPs in router for each device
   - Document IP assignments

4. **API Keys**: Each device should have its own API key
   - Generate unique key per device
   - Store securely in `.env` file

---

## Heartbeat & Monitoring

### How Heartbeats Work

1. Each device reports heartbeat every 60 seconds
2. Central dashboard tracks last heartbeat time
3. Devices with no heartbeat for 5 minutes marked offline
4. Auto-recovery when device comes back online

### Heartbeat Payload

Devices send heartbeat with metrics:

```json
{
  "device_id": "device-building-a-floor-1",
  "metrics": {
    "cpu_usage": 45.2,
    "memory_usage": 512000000,
    "disk_usage": 75.5,
    "queue_count": 3,
    "camera_ok": true,
    "total_scans": 145,
    "last_scan": "2025-11-29T20:15:30"
  }
}
```

### Manual Heartbeat Check

```bash
# Check which devices need attention
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices?status=offline
```

---

## Bulk Operations

### Send Command to Multiple Devices

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "http://192.168.1.22:8080"

headers = {"Authorization": f"Bearer {API_KEY}"}

# Get all online devices
response = requests.get(f"{BASE_URL}/devices?status=online", headers=headers)
devices = response.json()['devices']

# Send command to each
for device in devices:
    device_id = device['device_id']
    result = requests.get(
        f"{BASE_URL}/devices/{device_id}/command/queue",
        headers=headers
    )
    print(f"{device['device_name']}: {result.json()}")
```

### Example: Force Sync All Devices

```bash
#!/bin/bash

API_KEY="your-api-key"
BASE_URL="http://192.168.1.22:8080"

# Get all devices
DEVICES=$(curl -s -H "Authorization: Bearer $API_KEY" \
  "$BASE_URL/devices" | jq -r '.devices[].device_id')

# Send sync command to each
for DEVICE_ID in $DEVICES; do
  echo "Syncing $DEVICE_ID..."
  curl -s -H "Authorization: Bearer $API_KEY" \
    "$BASE_URL/devices/$DEVICE_ID/command/sync"
done
```

---

## Device Groups

### Create Device Group

```bash
curl -X POST http://192.168.1.22:8080/groups \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "group_name": "Building A Devices",
    "description": "All devices in Building A"
  }'
```

### Add Devices to Group

```bash
curl -X POST http://192.168.1.22:8080/groups/1/add \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "device_ids": [
      "device-building-a-floor-1",
      "device-building-a-floor-2"
    ]
  }'
```

### Bulk Operations on Group

```bash
# Send command to all devices in group
curl -X POST http://192.168.1.22:8080/groups/1/command \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "command": "status"
  }'
```

---

## Deployment Scenarios

### Scenario 1: Small School (Single Building)

**Setup:**
- 1 central dashboard in IT office
- 5 devices (1 per floor entrance)
- Single network (192.168.1.0/24)

**Configuration:**
```
Central: 192.168.1.22 (dashboard only)
Device 1: 192.168.1.100 (Floor 1)
Device 2: 192.168.1.101 (Floor 2)
Device 3: 192.168.1.102 (Floor 3)
Device 4: 192.168.1.103 (Floor 4)
Device 5: 192.168.1.104 (Floor 5)
```

### Scenario 2: Large School (Multiple Buildings)

**Setup:**
- 1 central dashboard in admin building
- 20 devices across 3 buildings
- Multiple subnets per building

**Network Design:**
```
Admin Building: 192.168.1.0/24 (Central Dashboard)
Building A:     192.168.10.0/24 (Devices 101-107)
Building B:     192.168.20.0/24 (Devices 201-208)
Building C:     192.168.30.0/24 (Devices 301-305)
```

**VPN/Routing:**
- Central dashboard accessible from all subnets
- Use VPN or inter-VLAN routing for device communication
- Firewall rules allow port 8080 from device subnets to dashboard

---

## Networking Requirements

### Port Configuration

| Service | Port | Protocol | Direction |
|---------|------|----------|-----------|
| Admin Dashboard API | 8080 | TCP | Inbound |
| Device Heartbeat | 8080 | TCP | Outbound |
| SSH Management | 22 | TCP | Inbound |

### Firewall Rules

**Central Dashboard (192.168.1.22):**
```bash
# Allow API access from device subnets
sudo ufw allow from 192.168.10.0/24 to any port 8080
sudo ufw allow from 192.168.20.0/24 to any port 8080
sudo ufw allow from 192.168.30.0/24 to any port 8080

# Allow admin access
sudo ufw allow from 192.168.1.0/24 to any port 8080
sudo ufw allow from 192.168.1.0/24 to any port 22
```

**Individual Devices:**
```bash
# Allow central dashboard to access device API
sudo ufw allow from 192.168.1.22 to any port 8080

# Allow local admin access
sudo ufw allow from 192.168.X.0/24 to any port 8080
```

---

## Troubleshooting

### Device Not Discovered

**Check:**
1. Device is powered on and running
2. Device is on same network (or accessible subnet)
3. Dashboard port 8080 accessible from central server
4. Device firewall allows connections from central server

```bash
# Test connectivity
ping 192.168.1.100

# Test API endpoint
curl http://192.168.1.100:8080/health
```

### Device Shows Offline

**Check:**
1. Last heartbeat time: `/devices/{id}/status`
2. Network connectivity from device to dashboard
3. Dashboard heartbeat checker running (auto-starts)

```bash
# Manually update heartbeat
curl -X POST http://192.168.1.22:8080/devices/heartbeat \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "device_id": "device-building-a-floor-1",
    "metrics": {"cpu_usage": 50}
  }'
```

### Cannot Send Commands

**Check:**
1. Device API key configured correctly
2. Device firewall allows incoming connections
3. Network routing between dashboard and device

```bash
# Test direct device access
curl -H "Authorization: Bearer $DEVICE_API_KEY" \
  http://192.168.1.100:8080/status
```

---

## Security Considerations

### API Key Management

- **Central Dashboard**: Main API key for admin access
- **Device API Keys**: Unique key per device for device-to-device communication

```bash
# Generate secure API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Network Security

1. **Isolate Device Network**: Use VLAN for device subnet
2. **Firewall Rules**: Only allow necessary ports
3. **VPN Access**: Use VPN for remote admin access
4. **IP Whitelisting**: Restrict dashboard access to known IPs

### Device Authentication

Enable auth on all devices:

```json
{
  "admin_dashboard": {
    "auth_enabled": true,
    "allowed_ips": ["192.168.1.22"]  // Central dashboard only
  }
}
```

---

## Monitoring & Alerts

### Fleet Health Checks

```bash
# Check fleet health every 5 minutes
*/5 * * * * /home/iot/scripts/check_fleet_health.sh
```

**check_fleet_health.sh:**
```bash
#!/bin/bash

API_KEY="your-api-key"
DASHBOARD="http://192.168.1.22:8080"

# Get device summary
SUMMARY=$(curl -s -H "Authorization: Bearer $API_KEY" \
  "$DASHBOARD/devices/status" | jq '.summary')

OFFLINE=$(echo "$SUMMARY" | jq '.offline')

if [ "$OFFLINE" -gt 0 ]; then
  echo "ALERT: $OFFLINE devices offline" | mail -s "Device Alert" admin@school.edu
fi
```

### Aggregated Metrics

```bash
# Get daily report
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices/metrics | jq .
```

**Response:**
```json
{
  "total_devices": 12,
  "online_devices": 10,
  "offline_devices": 2,
  "devices_with_issues": 1,
  "total_scans_today": 1450,
  "total_queue_pending": 23
}
```

---

## Maintenance

### Adding New Device

1. **Install** attendance system on new Raspberry Pi
2. **Configure** device ID and location in `config/config.json`
3. **Start** attendance service
4. **Discover** from central dashboard or register manually
5. **Verify** device appears in device list

### Removing Device

```bash
# Remove device from registry
curl -X DELETE http://192.168.1.22:8080/devices/device-id \
  -H "Authorization: Bearer $API_KEY"
```

### Updating Device Configuration

1. SSH to device
2. Edit `config/config.json`
3. Restart service: `sudo systemctl restart attendance.service`
4. Refresh dashboard to see updated config

---

## Performance Considerations

### Network Bandwidth

- **Heartbeat**: ~1 KB per device per minute
- **Status Check**: ~5 KB per device per request
- **Discovery Scan**: Variable (depends on network size)

**For 20 devices:**
- Heartbeat traffic: ~20 KB/min = ~30 MB/day
- Minimal impact on network

### Database Size

- **Devices table**: ~1 KB per device
- **Heartbeats**: ~100 bytes per heartbeat (kept 24 hours)
- **Events**: ~200 bytes per event

**For 20 devices (24 hours):**
- Device records: 20 KB
- Heartbeat logs: ~2.9 MB (20 devices × 60/min × 1440 min × 100 bytes)
- Total: ~3 MB per day

---

## Future Enhancements

### Planned Features

- [ ] Real-time WebSocket updates for device status
- [ ] Advanced alerting (email, SMS, Slack)
- [ ] Device health scoring
- [ ] Automatic firmware updates
- [ ] Custom dashboards per building/department
- [ ] Historical performance analytics
- [ ] Device templates for quick provisioning
- [ ] Role-based access control (RBAC)

---

## Support

**Documentation:**
- API Integration Guide: `docs/API_INTEGRATION_GUIDE.md`
- Dashboard Deployment: `docs/DASHBOARD_DEPLOYMENT.md`
- Security Setup: `docs/security/SECURITY_SETUP.md`

**Components:**
- Device Registry: `src/database/device_registry.py`
- Multi-Device Manager: `src/utils/multi_device_manager.py`
- Admin Dashboard: `src/utils/admin_dashboard.py`
- React UI: `docs/react-components/MultiDeviceDashboard.jsx`

---

**Status:** Production Ready  
**Version:** 1.0  
**Last Updated:** 2025-11-29
