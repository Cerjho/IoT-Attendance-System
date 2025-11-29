# Test Scripts

This directory contains test scripts for validating system functionality and security.

## Available Tests

### 1. test_endpoints.sh
Tests all admin dashboard API endpoints for functionality.

**Usage:**
```bash
bash scripts/tests/test_endpoints.sh "your-api-key"
```

**Tests:**
- `/health` - System health check
- `/status` - Service status
- `/api/system/info` - System information
- `/api/queue/status` - Sync queue status
- `/api/scans/recent` - Recent attendance scans
- `/api/metrics` - System metrics
- `/api/config` - Configuration view
- `/metrics` - Prometheus metrics

### 2. test_security.sh
Validates authentication and security headers.

**Usage:**
```bash
bash scripts/tests/test_security.sh "your-api-key"
```

**Tests:**
- ✓ 401 rejection without API key
- ✓ 200 success with Bearer token
- ✓ 200 success with X-API-Key header
- ✓ 401 rejection with invalid key
- ✓ Security headers present (HSTS, X-Frame, X-XSS, nosniff)
- ✓ All endpoints protected

### 3. test_ip_whitelist.sh
Validates IP whitelisting configuration.

**Usage:**
```bash
bash scripts/tests/test_ip_whitelist.sh "your-api-key"
```

**Tests:**
- ✓ Localhost access allowed (127.0.0.1)
- ✓ Local network access based on whitelist
- ✓ IP whitelist configuration active
- ✓ Authentication still required

## Quick Commands

### Get API Key
```bash
grep DASHBOARD_API_KEY /home/iot/attendance-system/.env | cut -d= -f2
```

### Run All Tests
```bash
API_KEY=$(grep DASHBOARD_API_KEY /home/iot/attendance-system/.env | cut -d= -f2)
cd /home/iot/attendance-system
bash scripts/tests/test_endpoints.sh "$API_KEY"
bash scripts/tests/test_security.sh "$API_KEY"
bash scripts/tests/test_ip_whitelist.sh "$API_KEY"
```

### Run Specific Test
```bash
# Health check only
curl -H "Authorization: Bearer $(grep DASHBOARD_API_KEY .env | cut -d= -f2)" \
  http://localhost:8080/health

# Metrics only
curl -H "Authorization: Bearer $(grep DASHBOARD_API_KEY .env | cut -d= -f2)" \
  http://localhost:8080/metrics
```

## Test Results Interpretation

### Success Indicators
- ✅ HTTP 200 - Request successful
- ✅ HTTP 401 - Unauthorized (expected for tests without API key)
- ✅ HTTP 403 - Forbidden (expected for blocked IPs)
- ✅ JSON response - Valid data returned
- ✅ Security headers present

### Failure Indicators
- ❌ HTTP 500 - Server error (check logs)
- ❌ Connection refused - Service not running
- ❌ Empty response - Service crashed
- ❌ Missing security headers - Configuration issue

## Troubleshooting

### Service Not Running
```bash
sudo systemctl status attendance-dashboard
sudo systemctl start attendance-dashboard
```

### Authentication Failures
```bash
# Verify API key exists
grep DASHBOARD_API_KEY /home/iot/attendance-system/.env

# Check auth is enabled
grep auth_enabled /home/iot/attendance-system/config/config.json

# View auth logs
sudo journalctl -u attendance-dashboard | grep -i auth
```

### IP Whitelist Issues
```bash
# View current whitelist
grep -A5 '"allowed_ips"' /home/iot/attendance-system/config/config.json

# Check IP rejection logs
sudo journalctl -u attendance-dashboard | grep "Rejected request"
```

## Related Documentation

- [../../docs/security/](../../docs/security/) - Security configuration guides
- [../../docs/DASHBOARD_DEPLOYMENT.md](../../docs/DASHBOARD_DEPLOYMENT.md) - Dashboard setup
- [../../README.md](../../README.md) - Project overview

## Adding New Tests

When creating new test scripts:

1. Place in `scripts/tests/` directory
2. Make executable: `chmod +x script-name.sh`
3. Accept API key as first argument: `API_KEY="$1"`
4. Use consistent output format (✅/❌)
5. Document in this README
6. Test with and without authentication
