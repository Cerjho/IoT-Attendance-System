# Admin Dashboard Configuration Management - Quick Reference

## Current State (v1.0)

### What Works ✅
- **GET /config** - View configuration (sanitized, read-only)
- **Authentication** - API key required
- **IP Whitelisting** - 192.168.1.0/24, 127.0.0.1
- **10 Monitoring Endpoints** - Health, status, metrics, scans, queue, system info

### What Doesn't Work ❌
- **Configuration Updates via API** - Not implemented
- **POST/PUT/PATCH /config** - Endpoints don't exist
- **Admin Key System** - Not implemented
- **Config Backup/Rollback** - Manual only

---

## How to Change Configuration Today

### Method 1: Direct File Edit (SSH Required)

```bash
# 1. Connect to device
ssh pi@192.168.1.22

# 2. Backup current config
cp config/config.json config/config.json.backup

# 3. Edit configuration
nano config/config.json

# 4. Validate JSON syntax
python3 -m json.tool config/config.json

# 5. Restart service
sudo systemctl restart attendance-dashboard

# 6. Verify changes applied
curl -H "Authorization: Bearer $API_KEY" http://localhost:8080/config | jq .
```

### Method 2: SCP + Edit Locally

```bash
# 1. Download config
scp pi@192.168.1.22:~/attendance-system/config/config.json ./

# 2. Edit locally (VS Code, notepad, etc.)
code config.json

# 3. Upload back
scp config.json pi@192.168.1.22:~/attendance-system/config/

# 4. SSH and restart
ssh pi@192.168.1.22 "sudo systemctl restart attendance-dashboard"
```

---

## Adding Config Update Feature (Future v2.0)

### What Needs to be Built

**Backend (`src/utils/admin_dashboard.py`):**
- [ ] `do_PUT()` method - Replace config sections
- [ ] `do_PATCH()` method - Partial updates
- [ ] `_validate_config_updates()` - Input validation
- [ ] `_backup_config()` - Auto-backup before changes
- [ ] `_log_config_change()` - Audit logging
- [ ] `_check_admin_permission()` - Two-key auth (API key + Admin key)
- [ ] Rollback endpoint - Restore from backup

**Frontend (React/Vue/etc.):**
- [ ] ConfigurationManager component
- [ ] ConfigBackups component
- [ ] Admin key input
- [ ] Change preview
- [ ] Confirmation dialogs
- [ ] Restart notification

**Infrastructure:**
- [ ] `DASHBOARD_ADMIN_KEY` in `.env`
- [ ] `config/backups/` directory
- [ ] `data/logs/config_audit.log` for changes
- [ ] Systemd service reload without full restart (optional)

**Security:**
- [ ] Two-key authentication (regular API key + admin key)
- [ ] Input validation (types, ranges, injection protection)
- [ ] Sensitive field protection (block API updates to credentials)
- [ ] Rate limiting on config changes
- [ ] Audit logging with IP/timestamp

**Testing:**
- [ ] Unit tests for validation logic
- [ ] Integration tests for update flow
- [ ] Rollback procedure tests
- [ ] Security tests (unauthorized attempts)
- [ ] Load tests (concurrent update attempts)

---

## Implementation Estimate

**Development Time:**
- Backend endpoints: 8-12 hours
- Frontend UI: 6-8 hours
- Security implementation: 4-6 hours
- Testing: 4-6 hours
- Documentation: 2-3 hours
- **Total: 24-35 hours**

**Complexity:** Medium
- Similar to existing endpoint patterns
- Clear security requirements
- Good documentation available

---

## Complete Documentation Available

📖 **Full Implementation Guide:**
- [docs/ADMIN_CONFIG_MANAGEMENT.md](./ADMIN_CONFIG_MANAGEMENT.md) - Complete implementation with code samples

📖 **API Integration Guide:**
- [docs/API_INTEGRATION_GUIDE.md](./API_INTEGRATION_GUIDE.md) - Section 7 updated with current limitations

📖 **Security Setup:**
- [docs/security/SECURITY_SETUP.md](./security/SECURITY_SETUP.md) - Authentication patterns

---

## Common Configuration Changes

### Change Camera Index
```json
{
  "camera": {
    "index": 1
  }
}
```

### Toggle Cloud Sync
```json
{
  "cloud": {
    "enabled": false
  }
}
```

### Change Dashboard Port
```json
{
  "admin_dashboard": {
    "port": 9090
  }
}
```
⚠️ **Requires service restart**

### Update IP Whitelist
```json
{
  "admin_dashboard": {
    "allowed_ips": [
      "192.168.1.0/24",
      "10.0.0.0/8",
      "127.0.0.1"
    ]
  }
}
```
⚠️ **Requires service restart**

### Disable Authentication (Development Only)
```json
{
  "admin_dashboard": {
    "auth_enabled": false
  }
}
```
⚠️ **NEVER do this in production**

---

## Quick Commands

```bash
# View current config
curl -H "Authorization: Bearer $API_KEY" \
  http://192.168.1.22:8080/config | jq .

# Backup config
sudo cp config/config.json config/config.json.$(date +%Y%m%d_%H%M%S)

# Validate config JSON
python3 -m json.tool config/config.json > /dev/null && echo "Valid JSON"

# Restart dashboard
sudo systemctl restart attendance-dashboard

# Check service status
sudo systemctl status attendance-dashboard

# View recent logs
sudo journalctl -u attendance-dashboard -n 50 --no-pager

# Check who changed config (if audit log exists)
cat data/logs/config_audit.log | jq .
```

---

## Decision Matrix: Should You Implement Config API?

| Factor | Implement API | Keep Manual |
|--------|--------------|-------------|
| **Users** | Multiple admins, non-technical users | Single admin, technical |
| **Frequency** | Daily/weekly changes | Rare changes |
| **Remote Access** | Critical | SSH access available |
| **Security Posture** | High (two-key auth, audit) | Medium (SSH keys) |
| **Complexity** | Can handle development time | Need quick deployment |
| **Budget** | 24-35 dev hours available | Limited resources |

**Recommendation:**
- ✅ **Implement API** if: Multiple admins OR frequent changes OR limited SSH access
- ⏸️ **Keep Manual** if: Single admin AND rare changes AND SSH comfortable

---

## Support

**Questions about current system:**
- Check `/config` endpoint for current settings
- SSH to device for manual changes
- See `docs/API_INTEGRATION_GUIDE.md` for API usage

**Want to implement config updates:**
- See `docs/ADMIN_CONFIG_MANAGEMENT.md` for complete implementation guide
- Backend code samples provided
- Frontend React components included
- Security patterns documented

---

**Last Updated:** 2025-11-29  
**Dashboard Version:** 1.0 (Read-Only Config)  
**Status:** Documentation Complete, Implementation Optional
