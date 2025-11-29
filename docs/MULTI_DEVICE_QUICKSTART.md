# Multi-Device Quick Start Guide

## Enable Multi-Device Management in 5 Minutes

### Step 1: Enable on Central Dashboard (1 min)

Edit `config/config.json` on your central management server:

```json
{
  "device_id": "central-dashboard",
  "device_name": "Central Management Server",
  "admin_dashboard": {
    "enabled": true,
    "auth_enabled": true,
    "port": 8080,
    "multi_device_enabled": true  // ← Add this line
  }
}
```

### Step 2: Restart Dashboard (30 sec)

```bash
sudo systemctl restart attendance-dashboard
```

### Step 3: Verify Multi-Device Endpoints (30 sec)

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8080/devices

# Should return: {"devices": [], "count": 0}
```

### Step 4: Configure Other Devices (2 min per device)

On each attendance device, edit `config/config.json`:

```json
{
  "device_id": "device-building-a-floor-1",  // ← Unique ID
  "device_name": "Building A - Floor 1",     // ← Descriptive name
  "admin_dashboard": {
    "enabled": true,
    "auth_enabled": true,
    "port": 8080
  },
  "location": {                              // ← Location info
    "building": "Building A",
    "floor": "Floor 1",
    "room": "Main Entrance"
  }
}
```

**Important:** Each device MUST have:
- ✅ Unique `device_id`  
- ✅ Descriptive `device_name`
- ✅ Location info (building/floor/room)

### Step 5: Discover Devices (1 min)

From central dashboard:

```bash
# Auto-discover all devices on network
curl -H "Authorization: Bearer $API_KEY" \
  "http://192.168.1.22:8080/devices/discover?network=192.168.1.0/24"
```

**Response:**
```json
{
  "discovered": 5,
  "registered": 5,
  "devices": [...]
}
```

---

## Verify Setup

### Check Device List

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices | jq .
```

**Expected:**
```json
{
  "devices": [
    {
      "device_id": "device-building-a-floor-1",
      "device_name": "Building A - Floor 1",
      "ip_address": "192.168.1.100",
      "status": "online",
      "location": "Building A - Floor 1 Main Entrance"
    },
    ...
  ],
  "count": 5
}
```

### Check Fleet Status

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices/status | jq .summary
```

**Expected:**
```json
{
  "total": 5,
  "online": 5,
  "offline": 0,
  "error": 0
}
```

### Check Aggregated Metrics

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices/metrics | jq .
```

**Expected:**
```json
{
  "total_devices": 5,
  "online_devices": 5,
  "offline_devices": 0,
  "total_scans_today": 145,
  "total_queue_pending": 0
}
```

---

## Use React Dashboard

### Install Dependencies

```bash
npx create-react-app attendance-fleet-dashboard
cd attendance-fleet-dashboard
npm install axios
```

### Add Components

Copy `docs/react-components/MultiDeviceDashboard.jsx` to `src/`

### Configure

Edit `src/App.js`:

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

export default App;
```

### Run

```bash
npm start
# Open http://localhost:3000
```

---

## Common Issues

### "Multi-device management not enabled" Error

**Solution:** Add `multi_device_enabled: true` to config and restart:

```bash
sudo systemctl restart attendance-dashboard
```

### Devices Not Discovered

**Check:**
1. Devices are powered on
2. Devices are on same network (or accessible subnet)
3. Firewall allows port 8080

**Test connectivity:**
```bash
ping 192.168.1.100
curl http://192.168.1.100:8080/health
```

### Device Shows Offline

**Check heartbeat:**
```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices/device-id/status
```

Devices are marked offline after 5 minutes of no heartbeat.

---

## Next Steps

📖 **Full Documentation:** `docs/MULTI_DEVICE_MANAGEMENT.md`
- Network configuration
- Security setup
- Bulk operations
- Device groups
- Troubleshooting

🎨 **React Components:** `docs/react-components/MultiDeviceDashboard.jsx`
- Fleet overview
- Device cards
- Discovery UI
- Location tree

🔒 **Security Guide:** `docs/security/SECURITY_SETUP.md`
- API key management
- Firewall rules
- IP whitelisting

---

## Quick Commands Reference

```bash
# List all devices
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices

# Filter by status
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices?status=online

# Get fleet metrics
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices/metrics

# Get device status
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices/device-id/status

# Send command to device
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/devices/device-id/command/queue

# Get locations
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/locations
```

---

**Setup Time:** ~5 minutes for central + 2 minutes per device  
**Status:** Production Ready  
**Support:** See `docs/MULTI_DEVICE_MANAGEMENT.md`
