# Production Dashboard Status

## Current State (Working ✅)

### What's Working
- ✅ **HTTPS Access**: Dashboard accessible via `https://192.168.1.22/multi-device-dashboard.html`
- ✅ **API Proxy**: Nginx proxies API requests to backend on port 8080
- ✅ **Authentication**: API key authentication working (`Authorization: Bearer` header)
- ✅ **Security**: IP whitelist configured (192.168.1.0/24, 127.0.0.1)
- ✅ **Static Files**: HTML/JS/CSS served via Nginx from `/home/iot/attendance-system/public/`
- ✅ **Graceful Degradation**: Dashboard shows single device when multi-device disabled
- ✅ **Status Endpoints**: `/health`, `/status`, `/queue/status` all working
- ✅ **Auto-restart**: systemd service configured with automatic restart
- ✅ **Health Monitoring**: Cron job checks health every 5 minutes

### Access Dashboard
```bash
# From browser on same network:
https://192.168.1.22/multi-device-dashboard.html

# Will prompt for API key, use:
hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8
```

## Development Mode (Current)

The dashboard currently uses CDN libraries for quick development:
- React 18 (via unpkg CDN)
- Tailwind CSS (via CDN)
- Babel standalone (browser JSX compilation)
- Axios (via CDN)

**Impact**: 
- ⚠️ Browser console shows warnings about CDN usage in production
- ⚠️ Slower initial load (downloads from CDN)
- ✅ Functionality is 100% working
- ✅ Banner warns users about dev mode

**User Action**: Dismiss the yellow banner at the top if warnings bother you.

## Production Build (Future Enhancement)

To remove CDN warnings and optimize performance:

### Option 1: Pre-compile React Components
```bash
# Install build tools
npm install --save-dev @babel/core @babel/cli @babel/preset-react

# Compile JSX to plain JavaScript
npx babel public/multi-device-dashboard.html --out-file public/dashboard.js --presets @babel/preset-react

# Update HTML to use compiled JS instead of inline JSX
```

### Option 2: Build with Tailwind CLI
```bash
# Install Tailwind
npm install -D tailwindcss

# Generate tailwind.config.js
npx tailwindcss init

# Build CSS
npx tailwindcss -i public/styles.css -o public/dist/styles.css --minify
```

### Option 3: Full Build System (Recommended for Scale)
```bash
# Use Vite or Create React App
npm create vite@latest dashboard -- --template react
cd dashboard
npm install axios
npm run build

# Copy dist/ to public/
```

## Testing

### Test API Endpoints
```bash
API_KEY="hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8"

# Health check
curl -k -H "Authorization: Bearer $API_KEY" https://192.168.1.22/health

# System status
curl -k -H "Authorization: Bearer $API_KEY" https://192.168.1.22/status

# Queue status
curl -k -H "Authorization: Bearer $API_KEY" https://192.168.1.22/queue/status

# Metrics
curl -k -H "Authorization: Bearer $API_KEY" https://192.168.1.22/metrics
```

### Test Dashboard Access
```bash
# From browser:
1. Navigate to: https://192.168.1.22/multi-device-dashboard.html
2. Accept self-signed certificate warning (expected)
3. Enter API key when prompted
4. Should see "Main Device" card with system status
```

## Configuration

### Current Settings (`config/config.json`)
```json
{
  "admin_dashboard": {
    "enabled": true,
    "port": 8080,
    "host": "127.0.0.1",
    "auth_enabled": true,
    "allowed_ips": ["192.168.1.0/24", "127.0.0.1"]
  },
  "multi_device_enabled": false
}
```

### Enable Multi-Device (After Cleanup)
```bash
# 1. Clean test devices
sqlite3 data/devices.db "DELETE FROM devices WHERE device_id LIKE 'test-%';"
sqlite3 data/devices.db "DELETE FROM device_heartbeats WHERE device_id LIKE 'test-%';"

# 2. Enable in config
# Edit config/config.json: "multi_device_enabled": true

# 3. Restart service
sudo systemctl restart attendance-dashboard.service
```

## Security Notes

### Current Setup
- **Protocol**: HTTPS only (TLS 1.2/1.3)
- **Certificate**: Self-signed (for local network)
- **Authentication**: API key required for all endpoints
- **IP Whitelist**: Only 192.168.1.0/24 network allowed
- **Headers**: HSTS, CSP, X-Frame-Options, X-XSS-Protection configured
- **Rate Limiting**: 100 requests/minute per IP

### For Internet Exposure (Future)
```bash
# Get Let's Encrypt certificate
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# Update Nginx config to use real cert
# Update IP whitelist to allow specific public IPs
# Consider VPN instead of exposing directly
```

## Troubleshooting

### Dashboard Shows 503 Errors
```bash
# Check if multi-device is disabled (expected)
grep multi_device_enabled config/config.json

# Verify service running
systemctl status attendance-dashboard.service

# Check Nginx proxy
sudo tail -20 /var/log/nginx/dashboard_error.log
```

### Authentication Fails
```bash
# Verify API key in .env
grep DASHBOARD_API_KEY .env

# Check IP whitelist
curl -k -H "Authorization: Bearer $API_KEY" https://192.168.1.22/health
# Should return 200 from whitelisted IPs
```

### Static Files Not Loading
```bash
# Verify permissions
ls -la /home/iot/attendance-system/public/

# Should show +x on directories for www-data access
# Check Nginx error log
sudo tail -50 /var/log/nginx/dashboard_error.log
```

## Next Steps

1. ✅ **Dashboard working** - Can test now
2. ⏳ **Multi-device cleanup** - Remove test devices, re-enable
3. ⏳ **Production build** - Replace CDN with compiled assets (optional)
4. ⏳ **Real certificate** - Replace self-signed with Let's Encrypt (if exposing to internet)

## Quick Commands

```bash
# Restart dashboard
sudo systemctl restart attendance-dashboard.service

# View logs
sudo journalctl -u attendance-dashboard.service -f

# Check health
curl -k -H "Authorization: Bearer hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8" https://192.168.1.22/health

# Force sync queued records
python scripts/force_sync.py

# Check system status
python scripts/status.py
```
