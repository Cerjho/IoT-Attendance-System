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

## Note

This security documentation pertains to the removed admin dashboard and multi-device management features, which have been moved to a separate monitoring system project. For current system security, refer to:

- [../DEPLOYMENT.md](../DEPLOYMENT.md) - General deployment instructions
- Environment variable security (`.env` file management)
- Supabase RLS (Row Level Security) policies

## Support

For security issues or questions:
1. Review Supabase security policies
2. Check application logs: `data/logs/attendance_system.log`
3. Verify configuration: `cat config/config.json`
