# Security Documentation

This directory contains security setup and configuration guides for the IoT Attendance System.

## Documents

### 1. [SECURITY_SETUP.md](SECURITY_SETUP.md)
Complete guide for implementing API key authentication and security headers.

**Contents:**
- API key generation and configuration
- Environment variable setup
- Security headers implementation
- Systemd service configuration

### 2. [IP_WHITELIST_CONFIG.md](IP_WHITELIST_CONFIG.md)
Guide for configuring IP-based access control.

**Contents:**
- IP whitelist configuration
- CIDR notation examples
- Testing procedures
- Troubleshooting common issues

### 3. [SECURE_DEPLOYMENT_SUMMARY.md](SECURE_DEPLOYMENT_SUMMARY.md)
Quick reference for secure deployment status and next steps.

**Contents:**
- Current security status
- Test results summary
- Production checklist
- Next steps guidance

## Security Layers

The system implements three layers of security:

1. **API Key Authentication** - Bearer token validation with constant-time comparison
2. **IP Whitelisting** - Network-level access control with CIDR support
3. **Security Headers** - HSTS, X-Frame-Options, XSS protection, content-type options

## Quick Start

### Enable Security Features

```bash
# 1. Configure API key in .env
echo "DASHBOARD_API_KEY=$(openssl rand -base64 32)" >> .env

# 2. Enable authentication in config.json
nano config/config.json
# Set: "auth_enabled": true

# 3. Configure IP whitelist
# Add allowed IPs to "allowed_ips" array

# 4. Restart service
sudo systemctl restart attendance-dashboard
```

### Test Security

```bash
# Run security tests
bash scripts/tests/test_security.sh "your-api-key"

# Run IP whitelist tests
bash scripts/tests/test_ip_whitelist.sh "your-api-key"

# Test all endpoints
bash scripts/tests/test_endpoints.sh "your-api-key"
```

### Monitor Access

```bash
# Watch for unauthorized attempts
sudo journalctl -u attendance-dashboard -f | grep -E "(Rejected|unauthorized|denied)"

# View recent security events
sudo journalctl -u attendance-dashboard -n 50 | grep -E "(IP|Authentication)"
```

## Configuration Files

- **API Keys:** `.env` file (never commit to git)
- **IP Whitelist:** `config/config.json` → `admin_dashboard.allowed_ips`
- **Auth Toggle:** `config/config.json` → `admin_dashboard.auth_enabled`

## Related Documentation

- [../DASHBOARD_DEPLOYMENT.md](../DASHBOARD_DEPLOYMENT.md) - Dashboard deployment guide
- [../DEPLOYMENT.md](../DEPLOYMENT.md) - General deployment instructions
- [../../scripts/tests/README.md](../../scripts/tests/README.md) - Test scripts documentation

## Support

For security issues or questions:
1. Check troubleshooting sections in respective guides
2. Review system logs: `sudo journalctl -u attendance-dashboard`
3. Verify configuration: `grep -A5 admin_dashboard config/config.json`
