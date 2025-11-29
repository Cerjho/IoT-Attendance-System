# IP Whitelisting Configuration

## ✅ Status: ACTIVE

IP whitelisting has been successfully configured for the Admin Dashboard.

## Current Configuration

**File:** `config/config.json`

```json
"admin_dashboard": {
  "enabled": true,
  "host": "0.0.0.0",
  "port": 8080,
  "auth_enabled": true,
  "allowed_ips": [
    "192.168.1.0/24",
    "127.0.0.1"
  ]
}
```

## What This Does

- **Localhost access (127.0.0.1):** ✅ Allowed - For local testing
- **Local network (192.168.1.0/24):** ✅ Allowed - All devices on your home/office network
- **External IPs:** ❌ Blocked - Any IP outside the whitelist is rejected with HTTP 403

## How to Modify Allowed IPs

### 1. Allow Specific Individual IPs

```json
"allowed_ips": [
  "192.168.1.100",      // Specific device
  "192.168.1.101",      // Another device
  "10.0.0.50",          // Device on different subnet
  "127.0.0.1"           // Localhost
]
```

### 2. Allow IP Ranges (CIDR Notation)

```json
"allowed_ips": [
  "192.168.1.0/24",     // Entire 192.168.1.x network (254 IPs)
  "10.0.0.0/16",        // Entire 10.0.x.x network (65534 IPs)
  "172.16.0.0/12",      // Private range 172.16-31.x.x
  "127.0.0.1"           // Localhost
]
```

### 3. Allow From Anywhere (NOT RECOMMENDED)

```json
"allowed_ips": []       // Empty array = allow all IPs (requires API key only)
```

## Testing Your Configuration

### Test from Allowed Device

```bash
# Get API key
API_KEY=$(grep DASHBOARD_API_KEY /home/iot/attendance-system/.env | cut -d= -f2)

# Test access (should return HTTP 200)
curl -H "Authorization: Bearer $API_KEY" http://192.168.1.22:8080/health
```

### Test from Blocked Device

Try accessing from a device outside your allowed IP ranges. Should return:

```json
{
  "error": "Access denied",
  "message": "Your IP address is not allowed"
}
```

## Apply Changes

After editing `config/config.json`:

```bash
# Restart dashboard service
sudo systemctl restart attendance-dashboard

# Verify it's running
sudo systemctl status attendance-dashboard

# Check logs for IP rejection messages
sudo journalctl -u attendance-dashboard -f
```

## Security Layers

Your dashboard now has **3 layers of security**:

1. **API Key Authentication** ✅
   - Requires valid Bearer token or X-API-Key header
   - Constant-time comparison prevents timing attacks

2. **IP Whitelisting** ✅
   - Only specified IPs can access endpoints
   - CIDR range support for network segments

3. **Security Headers** ✅
   - HSTS, X-Frame-Options, X-XSS-Protection
   - Prevents common web attacks

## Common IP Ranges

- **Home/Office LAN:** `192.168.1.0/24` or `192.168.0.0/24`
- **Corporate Network:** `10.0.0.0/8`
- **VPN Range:** Check your VPN provider (e.g., `172.16.0.0/12`)
- **Cloud Provider:** Get static IP from your cloud provider

## Find Your Current IP

```bash
# On the device you want to allow:
curl ifconfig.me

# Or
curl https://api.ipify.org
```

Then add that IP to the `allowed_ips` array.

## Troubleshooting

### "Access denied" Error

1. Check your current IP:
   ```bash
   curl https://api.ipify.org
   ```

2. Verify it's in the whitelist:
   ```bash
   grep -A5 '"allowed_ips"' config/config.json
   ```

3. Add your IP and restart:
   ```bash
   nano config/config.json  # Add your IP
   sudo systemctl restart attendance-dashboard
   ```

### Behind NAT/Router

If accessing from outside your network, you need to:
1. Get your public IP: `curl ifconfig.me`
2. Add it to whitelist
3. Configure port forwarding on your router (port 8080 → 192.168.1.22:8080)

### Dynamic IP Changes

If your ISP changes your IP frequently, consider:
- Using a DDNS service (DuckDNS, No-IP)
- Using a VPN with static IP
- Using wider CIDR ranges (less secure)
- Relying on API key only (set `allowed_ips: []`)

## Logs

Monitor IP rejections in real-time:

```bash
sudo journalctl -u attendance-dashboard -f | grep "IP"
```

Example log entry:
```
Nov 29 19:42:51 pi-iot attendance-dashboard[7275]: Rejected request from unauthorized IP: 203.0.113.45
```

## Recommendation

**Current Setup (✅ RECOMMENDED):**
- Local network access: `192.168.1.0/24`
- Localhost testing: `127.0.0.1`
- API key required
- HTTPS via Nginx (next step)

This provides strong security while allowing convenient access from your local network.

## Next Steps

1. **Setup HTTPS** - Use Nginx reverse proxy with SSL
2. **Configure Firewall** - Use ufw to block direct port 8080 access
3. **Monitor Logs** - Watch for unauthorized access attempts
4. **Backup Config** - Keep `config.json` and `.env` backed up securely

---

**Status:** IP whitelisting active and protecting your dashboard.
