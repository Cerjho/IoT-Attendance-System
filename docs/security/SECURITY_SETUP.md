# 🔒 Secure Remote Access - Admin Dashboard

## ✅ Security Features Enabled

The admin dashboard is now **secured for remote access** with:

✅ **API Key Authentication** - All endpoints require valid API key  
✅ **Security Headers** - HSTS, X-Frame-Options, X-XSS-Protection, etc.  
✅ **CORS Protection** - Configurable origin restrictions  
✅ **IP Whitelisting** - Optional IP-based access control  
✅ **Rate Limiting** - Via Nginx reverse proxy  
✅ **HTTPS Ready** - SSL/TLS configuration included  

---

## 🔑 API Key

Your API key has been generated and saved in `.env`:

```bash
# View your API key
grep DASHBOARD_API_KEY /home/iot/attendance-system/.env
```

**Your API Key:**
```
hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8
```

⚠️ **Keep this key secret!** It grants full access to your dashboard.

---

## 📡 Remote Access Methods

### Method 1: Direct HTTP Access (Development)

**⚠️ Not recommended for production - unencrypted**

```bash
# From remote machine
curl -H "Authorization: Bearer hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8" \
  http://192.168.1.22:8080/health

# Or use X-API-Key header
curl -H "X-API-Key: hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8" \
  http://192.168.1.22:8080/status
```

### Method 2: HTTPS via Nginx (Recommended for Production)

#### Step 1: Generate SSL Certificate

```bash
# Generate self-signed certificate (valid for 1 year)
bash scripts/generate_ssl_cert.sh

# Or use Let's Encrypt (recommended for internet-facing)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

#### Step 2: Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

#### Step 3: Configure Nginx

```bash
# Copy provided config
sudo cp scripts/nginx_dashboard.conf /etc/nginx/sites-available/dashboard

# Enable site
sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

#### Step 4: Access via HTTPS

```bash
# From remote machine
curl -k -H "Authorization: Bearer hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8" \
  https://192.168.1.22/health

# In browser (accept self-signed cert warning)
https://192.168.1.22/status
```

---

## 🌐 Using from Browser/JavaScript

### Fetch API Example

```javascript
const API_KEY = 'hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8';
const BASE_URL = 'https://192.168.1.22';

// Fetch health status
fetch(`${BASE_URL}/health`, {
  headers: {
    'Authorization': `Bearer ${API_KEY}`
  }
})
.then(res => res.json())
.then(data => console.log(data))
.catch(err => console.error(err));

// Fetch recent scans
fetch(`${BASE_URL}/scans/recent?limit=10`, {
  headers: {
    'X-API-Key': API_KEY
  }
})
.then(res => res.json())
.then(data => console.log(data.scans))
.catch(err => console.error(err));
```

### Axios Example

```javascript
const axios = require('axios');

const api = axios.create({
  baseURL: 'https://192.168.1.22',
  headers: {
    'Authorization': 'Bearer hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8'
  }
});

// Get system status
api.get('/status')
  .then(res => console.log(res.data))
  .catch(err => console.error(err));
```

---

## 🛡️ Additional Security Options

### IP Whitelisting

Edit `config/config.json`:

```json
{
  "admin_dashboard": {
    "enabled": true,
    "auth_enabled": true,
    "allowed_ips": [
      "192.168.1.100",
      "192.168.1.101"
    ]
  }
}
```

Only requests from listed IPs will be allowed (in addition to API key check).

### Firewall Rules

```bash
# Allow only specific IP
sudo ufw allow from 203.0.113.5 to any port 8080

# Allow from local network only
sudo ufw allow from 192.168.1.0/24 to any port 8080

# Allow HTTPS from anywhere
sudo ufw allow 443/tcp
```

### API Key Rotation

```bash
# Generate new API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env file
nano /home/iot/attendance-system/.env
# Change DASHBOARD_API_KEY=<new_key>

# Restart dashboard
sudo systemctl restart attendance-dashboard
```

---

## 🧪 Testing Authentication

### Test Suite

```bash
# Save your API key
API_KEY="hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8"

# Test 1: No auth (should fail with 401)
curl -w "\nStatus: %{http_code}\n" http://localhost:8080/health

# Test 2: Valid Bearer token (should succeed)
curl -w "\nStatus: %{http_code}\n" \
  -H "Authorization: Bearer $API_KEY" \
  http://localhost:8080/health

# Test 3: Valid X-API-Key header (should succeed)
curl -w "\nStatus: %{http_code}\n" \
  -H "X-API-Key: $API_KEY" \
  http://localhost:8080/status

# Test 4: Invalid key (should fail with 401)
curl -w "\nStatus: %{http_code}\n" \
  -H "Authorization: Bearer invalid_key_123" \
  http://localhost:8080/health

# Test 5: All endpoints with auth
for endpoint in health status system/info queue/status scans/recent metrics config; do
  echo "Testing /$endpoint"
  curl -s -H "Authorization: Bearer $API_KEY" \
    "http://localhost:8080/$endpoint" | head -5
  echo ""
done
```

---

## 📊 Monitoring Integration

### Prometheus with Authentication

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'attendance_dashboard'
    scheme: https
    tls_config:
      insecure_skip_verify: true  # For self-signed certs
    authorization:
      type: Bearer
      credentials: hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8
    static_configs:
      - targets: ['192.168.1.22:443']
    metrics_path: '/metrics/prometheus'
    scrape_interval: 30s
```

### Grafana Data Source

```yaml
name: Attendance Dashboard
type: prometheus
url: https://192.168.1.22:443/metrics/prometheus
jsonData:
  httpHeaderName1: Authorization
secureJsonData:
  httpHeaderValue1: Bearer hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8
```

---

## 🔒 Security Best Practices

### ✅ DO:
- ✅ Use HTTPS for remote access
- ✅ Keep API key in `.env` file only
- ✅ Rotate API keys regularly
- ✅ Use firewall rules to limit access
- ✅ Monitor access logs
- ✅ Use IP whitelisting when possible
- ✅ Use strong, random API keys

### ❌ DON'T:
- ❌ Commit API keys to Git
- ❌ Share API keys in plain text
- ❌ Use HTTP for remote access
- ❌ Expose port 8080 directly to internet
- ❌ Use simple/guessable API keys
- ❌ Disable authentication for convenience

---

## 📝 Configuration Reference

### config/config.json

```json
{
  "admin_dashboard": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8080,
    "auth_enabled": true,
    "allowed_ips": []  // Optional IP whitelist
  }
}
```

### .env

```bash
# Dashboard API Key (required when auth_enabled=true)
DASHBOARD_API_KEY=hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8
```

---

## 🚨 Troubleshooting

### 401 Unauthorized Error

```bash
# Check if API key is correct
grep DASHBOARD_API_KEY .env

# Check if auth is enabled
grep -A 5 "admin_dashboard" config/config.json

# Test with correct key
curl -H "Authorization: Bearer $(grep DASHBOARD_API_KEY .env | cut -d= -f2)" \
  http://localhost:8080/health
```

### Connection Refused

```bash
# Check if dashboard is running
sudo systemctl status attendance-dashboard

# Check if port is open
sudo lsof -i :8080

# Check firewall
sudo ufw status
```

### Certificate Errors

```bash
# For self-signed certs, use -k flag
curl -k -H "Authorization: Bearer $API_KEY" https://192.168.1.22/health

# Or import certificate to trust store
sudo cp certs/dashboard.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

---

## 📖 Quick Reference

### Current Setup

```
Dashboard URL: http://192.168.1.22:8080
HTTPS URL (after Nginx): https://192.168.1.22
Authentication: API Key Required
API Key: hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8
Status: ✅ Active and Secured
```

### Quick Commands

```bash
# View service status
sudo systemctl status attendance-dashboard

# Restart dashboard
sudo systemctl restart attendance-dashboard

# View logs
sudo journalctl -u attendance-dashboard -f

# Test access
API_KEY=$(grep DASHBOARD_API_KEY .env | cut -d= -f2)
curl -H "Authorization: Bearer $API_KEY" http://localhost:8080/health

# Generate new API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

**Last Updated:** 2025-11-29  
**Security Status:** 🔒 **SECURED FOR REMOTE ACCESS**
