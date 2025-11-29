# Admin Dashboard Configuration Management

## Overview

The admin dashboard currently provides **read-only** configuration viewing via `GET /config`. This document explains how to extend it with configuration update capabilities for admins.

## Current State (Read-Only)

### Existing Endpoint

**GET /config**
- Returns sanitized configuration (sensitive data redacted)
- Read-only view
- No modification capabilities

```json
{
  "camera": { "index": 0, "resolution": { "width": 1280, "height": 720 } },
  "admin_dashboard": { "enabled": true, "auth_enabled": true },
  "cloud": { "enabled": true, "url": "***REDACTED***" }
}
```

---

## Adding Configuration Update Capabilities

### Security Considerations

⚠️ **CRITICAL**: Configuration changes can affect system behavior. Implement these safeguards:

1. **Separate Admin Role** - Require higher privilege level than viewing
2. **Audit Logging** - Log all configuration changes with user/IP/timestamp
3. **Validation** - Validate all inputs before applying
4. **Backup** - Auto-backup config before changes
5. **Restart Required** - Some changes need service restart
6. **Rollback** - Ability to revert to previous config

---

## Implementation Guide

### Step 1: Add Configuration Update Endpoint

Add to `src/utils/admin_dashboard.py`:

```python
def do_PUT(self):
    """Handle PUT requests for configuration updates."""
    # Check authentication first
    if not self._check_authentication():
        self._send_json_response({
            "error": "Unauthorized",
            "message": "Valid API key required"
        }, 401)
        return
    
    # Check admin permission (new requirement)
    if not self._check_admin_permission():
        self._send_json_response({
            "error": "Forbidden",
            "message": "Admin privileges required for configuration changes"
        }, 403)
        return
    
    parsed = urlparse(self.path)
    path = parsed.path
    
    try:
        if path == "/config":
            self._handle_config_update()
        else:
            self._send_json_response({"error": "Not found"}, 404)
    except Exception as e:
        logger.error(f"Error handling PUT: {e}", exc_info=True)
        self._send_json_response({"error": str(e)}, 500)

def _check_admin_permission(self) -> bool:
    """Check if request has admin privileges."""
    admin_key = os.getenv("DASHBOARD_ADMIN_KEY")
    if not admin_key:
        return True  # If no admin key set, allow for backwards compatibility
    
    admin_header = self.headers.get('X-Admin-Key', '')
    if not admin_header:
        return False
    
    return hmac.compare_digest(admin_header, admin_key)

def _handle_config_update(self):
    """Handle configuration update request."""
    try:
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        updates = json.loads(body)
        
        # Validate updates
        validation_result = self._validate_config_updates(updates)
        if not validation_result['valid']:
            self._send_json_response({
                "error": "Validation failed",
                "details": validation_result['errors']
            }, 400)
            return
        
        # Backup current config
        backup_path = self._backup_config()
        
        # Apply updates
        config_path = Path("config/config.json")
        with open(config_path, 'r') as f:
            current_config = json.load(f)
        
        # Merge updates
        updated_config = self._merge_config(current_config, updates)
        
        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(updated_config, f, indent=2)
        
        # Log the change
        self._log_config_change(updates, backup_path)
        
        # Check if restart required
        restart_required = self._check_restart_required(updates)
        
        self._send_json_response({
            "success": True,
            "message": "Configuration updated successfully",
            "backup_path": str(backup_path),
            "restart_required": restart_required,
            "timestamp": datetime.now().isoformat()
        })
        
    except json.JSONDecodeError:
        self._send_json_response({
            "error": "Invalid JSON in request body"
        }, 400)
    except Exception as e:
        logger.error(f"Config update failed: {e}", exc_info=True)
        self._send_json_response({
            "error": "Configuration update failed",
            "details": str(e)
        }, 500)

def _validate_config_updates(self, updates: dict) -> dict:
    """Validate configuration updates."""
    errors = []
    
    # Validate camera settings
    if 'camera' in updates:
        camera = updates['camera']
        if 'index' in camera and not isinstance(camera['index'], int):
            errors.append("camera.index must be an integer")
        if 'resolution' in camera:
            if 'width' not in camera['resolution'] or 'height' not in camera['resolution']:
                errors.append("camera.resolution must have width and height")
    
    # Validate admin_dashboard settings
    if 'admin_dashboard' in updates:
        dashboard = updates['admin_dashboard']
        if 'port' in dashboard:
            port = dashboard['port']
            if not isinstance(port, int) or port < 1024 or port > 65535:
                errors.append("admin_dashboard.port must be between 1024-65535")
        if 'auth_enabled' in dashboard:
            if not isinstance(dashboard['auth_enabled'], bool):
                errors.append("admin_dashboard.auth_enabled must be boolean")
    
    # Validate cloud settings
    if 'cloud' in updates:
        cloud = updates['cloud']
        if 'enabled' in cloud and not isinstance(cloud['enabled'], bool):
            errors.append("cloud.enabled must be boolean")
        if 'retry_attempts' in cloud:
            if not isinstance(cloud['retry_attempts'], int) or cloud['retry_attempts'] < 1:
                errors.append("cloud.retry_attempts must be positive integer")
    
    # Prevent sensitive field updates via API
    sensitive_fields = ['cloud.url', 'cloud.api_key']
    for field in sensitive_fields:
        parts = field.split('.')
        if len(parts) == 2 and parts[0] in updates and parts[1] in updates[parts[0]]:
            errors.append(f"{field} cannot be updated via API (use .env file)")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def _merge_config(self, current: dict, updates: dict) -> dict:
    """Recursively merge configuration updates."""
    result = current.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = self._merge_config(result[key], value)
        else:
            result[key] = value
    
    return result

def _backup_config(self) -> Path:
    """Create backup of current configuration."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("config/backups")
    backup_dir.mkdir(exist_ok=True)
    
    backup_path = backup_dir / f"config_backup_{timestamp}.json"
    
    import shutil
    shutil.copy2("config/config.json", backup_path)
    
    # Keep only last 10 backups
    backups = sorted(backup_dir.glob("config_backup_*.json"))
    if len(backups) > 10:
        for old_backup in backups[:-10]:
            old_backup.unlink()
    
    return backup_path

def _log_config_change(self, updates: dict, backup_path: Path):
    """Log configuration change to audit log."""
    audit_log = Path("data/logs/config_audit.log")
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    
    client_ip = self.client_address[0]
    timestamp = datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "client_ip": client_ip,
        "updates": updates,
        "backup_path": str(backup_path)
    }
    
    with open(audit_log, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    logger.info(f"Configuration updated by {client_ip}: {list(updates.keys())}")

def _check_restart_required(self, updates: dict) -> bool:
    """Check if updates require service restart."""
    restart_fields = [
        'camera',
        'admin_dashboard.port',
        'admin_dashboard.host',
        'cloud.enabled',
    ]
    
    for field in restart_fields:
        parts = field.split('.')
        check_dict = updates
        for part in parts:
            if part in check_dict:
                if len(parts) == 1 or isinstance(check_dict[part], dict):
                    return True
                check_dict = check_dict.get(part, {})
    
    return False
```

### Step 2: Add PATCH Endpoint for Partial Updates

```python
def do_PATCH(self):
    """Handle PATCH requests for partial config updates."""
    if not self._check_authentication() or not self._check_admin_permission():
        self._send_json_response({"error": "Unauthorized"}, 401)
        return
    
    parsed = urlparse(self.path)
    
    if parsed.path == "/config":
        self._handle_partial_config_update()
    else:
        self._send_json_response({"error": "Not found"}, 404)

def _handle_partial_config_update(self):
    """Handle partial configuration update (PATCH)."""
    # Similar to PUT but only updates specified fields
    # Use same validation and merge logic
    pass
```

### Step 3: Add Rollback Endpoint

```python
def _handle_config_rollback(self):
    """Rollback to a previous configuration."""
    # GET /config/rollback?backup=config_backup_20251129_194251.json
    
    query_params = parse_qs(urlparse(self.path).query)
    backup_name = query_params.get('backup', [None])[0]
    
    if not backup_name:
        self._send_json_response({
            "error": "Backup filename required"
        }, 400)
        return
    
    backup_path = Path("config/backups") / backup_name
    
    if not backup_path.exists():
        self._send_json_response({
            "error": "Backup not found"
        }, 404)
        return
    
    try:
        # Backup current before rollback
        current_backup = self._backup_config()
        
        # Restore from backup
        import shutil
        shutil.copy2(backup_path, "config/config.json")
        
        self._log_config_change({
            "action": "rollback",
            "from_backup": str(backup_path)
        }, current_backup)
        
        self._send_json_response({
            "success": True,
            "message": "Configuration rolled back successfully",
            "restored_from": str(backup_path),
            "restart_required": True
        })
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        self._send_json_response({
            "error": "Rollback failed",
            "details": str(e)
        }, 500)
```

### Step 4: Add Backup List Endpoint

```python
def _handle_config_backups(self):
    """List available configuration backups."""
    backup_dir = Path("config/backups")
    
    if not backup_dir.exists():
        self._send_json_response({"backups": []})
        return
    
    backups = []
    for backup_file in sorted(backup_dir.glob("config_backup_*.json"), reverse=True):
        stat = backup_file.stat()
        backups.append({
            "filename": backup_file.name,
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "path": f"/config/rollback?backup={backup_file.name}"
        })
    
    self._send_json_response({"backups": backups})
```

---

## Frontend Integration

### React Component for Configuration Management

```tsx
// components/ConfigurationManager.tsx
import React, { useState, useEffect } from 'react';
import { useApi } from '../contexts/ApiContext';

interface ConfigUpdate {
  [key: string]: any;
}

export const ConfigurationManager: React.FC = () => {
  const [config, setConfig] = useState<any>(null);
  const [updates, setUpdates] = useState<ConfigUpdate>({});
  const [loading, setLoading] = useState(false);
  const [adminKey, setAdminKey] = useState('');
  const { apiClient } = useApi();

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await apiClient.get('/config');
      setConfig(response.data);
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  };

  const handleUpdate = async () => {
    setLoading(true);
    try {
      const response = await apiClient.put('/config', updates, {
        headers: {
          'X-Admin-Key': adminKey,
        },
      });

      alert('Configuration updated successfully!');
      
      if (response.data.restart_required) {
        alert('Service restart required for changes to take effect.');
      }

      setUpdates({});
      loadConfig();
    } catch (error: any) {
      alert(`Update failed: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (path: string, value: any) => {
    const keys = path.split('.');
    const newUpdates = { ...updates };
    
    let current = newUpdates;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) {
        current[keys[i]] = {};
      }
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;
    
    setUpdates(newUpdates);
  };

  return (
    <div className="config-manager">
      <h2>Configuration Manager</h2>
      
      <div className="admin-key-input">
        <input
          type="password"
          placeholder="Admin Key"
          value={adminKey}
          onChange={(e) => setAdminKey(e.target.value)}
        />
      </div>

      {config && (
        <div className="config-sections">
          {/* Camera Settings */}
          <section>
            <h3>Camera Settings</h3>
            <label>
              Camera Index:
              <input
                type="number"
                defaultValue={config.camera?.index}
                onChange={(e) => handleFieldChange('camera.index', parseInt(e.target.value))}
              />
            </label>
          </section>

          {/* Dashboard Settings */}
          <section>
            <h3>Dashboard Settings</h3>
            <label>
              Port:
              <input
                type="number"
                defaultValue={config.admin_dashboard?.port}
                onChange={(e) => handleFieldChange('admin_dashboard.port', parseInt(e.target.value))}
              />
            </label>
            <label>
              Authentication:
              <input
                type="checkbox"
                defaultChecked={config.admin_dashboard?.auth_enabled}
                onChange={(e) => handleFieldChange('admin_dashboard.auth_enabled', e.target.checked)}
              />
            </label>
          </section>

          {/* Cloud Settings */}
          <section>
            <h3>Cloud Settings</h3>
            <label>
              Enabled:
              <input
                type="checkbox"
                defaultChecked={config.cloud?.enabled}
                onChange={(e) => handleFieldChange('cloud.enabled', e.target.checked)}
              />
            </label>
            <label>
              Sync Interval (seconds):
              <input
                type="number"
                defaultValue={config.cloud?.sync_interval}
                onChange={(e) => handleFieldChange('cloud.sync_interval', parseInt(e.target.value))}
              />
            </label>
          </section>
        </div>
      )}

      <div className="actions">
        <button onClick={handleUpdate} disabled={loading || !adminKey}>
          {loading ? 'Updating...' : 'Apply Changes'}
        </button>
        <button onClick={loadConfig}>Reset</button>
      </div>

      {Object.keys(updates).length > 0 && (
        <div className="pending-changes">
          <h4>Pending Changes:</h4>
          <pre>{JSON.stringify(updates, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};
```

### Backup Management Component

```tsx
// components/ConfigBackups.tsx
import React, { useState, useEffect } from 'react';
import { useApi } from '../contexts/ApiContext';

interface Backup {
  filename: string;
  size_bytes: number;
  created: string;
  path: string;
}

export const ConfigBackups: React.FC = () => {
  const [backups, setBackups] = useState<Backup[]>([]);
  const [adminKey, setAdminKey] = useState('');
  const { apiClient } = useApi();

  useEffect(() => {
    loadBackups();
  }, []);

  const loadBackups = async () => {
    try {
      const response = await apiClient.get('/config/backups');
      setBackups(response.data.backups);
    } catch (error) {
      console.error('Failed to load backups:', error);
    }
  };

  const handleRollback = async (backup: Backup) => {
    if (!confirm(`Rollback to ${backup.filename}? This requires a service restart.`)) {
      return;
    }

    try {
      await apiClient.post(backup.path, null, {
        headers: { 'X-Admin-Key': adminKey },
      });
      alert('Rollback successful! Please restart the service.');
    } catch (error: any) {
      alert(`Rollback failed: ${error.response?.data?.error || error.message}`);
    }
  };

  return (
    <div className="config-backups">
      <h2>Configuration Backups</h2>
      
      <input
        type="password"
        placeholder="Admin Key"
        value={adminKey}
        onChange={(e) => setAdminKey(e.target.value)}
      />

      <table>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Created</th>
            <th>Size</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {backups.map((backup) => (
            <tr key={backup.filename}>
              <td>{backup.filename}</td>
              <td>{new Date(backup.created).toLocaleString()}</td>
              <td>{(backup.size_bytes / 1024).toFixed(1)} KB</td>
              <td>
                <button
                  onClick={() => handleRollback(backup)}
                  disabled={!adminKey}
                >
                  Rollback
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

---

## API Endpoints Summary

### Read Operations (Current)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/config` | View configuration (sanitized) | API Key |

### Write Operations (New)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| PUT | `/config` | Replace configuration sections | API Key + Admin Key |
| PATCH | `/config` | Partial configuration update | API Key + Admin Key |
| GET | `/config/backups` | List configuration backups | API Key |
| POST | `/config/rollback?backup=<file>` | Rollback to backup | API Key + Admin Key |

---

## Security Implementation

### Environment Variables

```bash
# .env
DASHBOARD_API_KEY=regular-api-key-for-viewing
DASHBOARD_ADMIN_KEY=super-secret-admin-key-for-changes
```

### Configuration

```json
// config/config.json
{
  "admin_dashboard": {
    "auth_enabled": true,
    "config_changes_enabled": true,
    "require_admin_key": true,
    "allowed_config_fields": [
      "camera.index",
      "camera.resolution",
      "admin_dashboard.port",
      "cloud.enabled",
      "cloud.sync_interval"
    ]
  }
}
```

### Audit Log Format

```json
{
  "timestamp": "2025-11-29T20:15:30.123456",
  "client_ip": "192.168.1.100",
  "action": "config_update",
  "updates": {
    "cloud": {
      "sync_interval": 120
    }
  },
  "backup_path": "config/backups/config_backup_20251129_201530.json",
  "restart_required": false
}
```

---

## Usage Examples

### Update Camera Index

```bash
curl -X PUT http://192.168.1.22:8080/config \
  -H "Authorization: Bearer regular-api-key" \
  -H "X-Admin-Key: super-secret-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "camera": {
      "index": 1
    }
  }'
```

### Enable/Disable Cloud Sync

```bash
curl -X PUT http://192.168.1.22:8080/config \
  -H "Authorization: Bearer regular-api-key" \
  -H "X-Admin-Key: super-secret-admin-key" \
  -d '{
    "cloud": {
      "enabled": false
    }
  }'
```

### List Backups

```bash
curl -H "Authorization: Bearer regular-api-key" \
  http://192.168.1.22:8080/config/backups
```

### Rollback Configuration

```bash
curl -X POST \
  -H "Authorization: Bearer regular-api-key" \
  -H "X-Admin-Key: super-secret-admin-key" \
  "http://192.168.1.22:8080/config/rollback?backup=config_backup_20251129_194251.json"
```

---

## Best Practices

### 1. Validation Rules

Always validate:
- ✅ Data types (int, bool, string)
- ✅ Value ranges (ports: 1024-65535)
- ✅ Required fields present
- ✅ No injection attempts
- ✅ Sensitive fields protected

### 2. Change Management

For each update:
1. ✅ Validate input
2. ✅ Create backup
3. ✅ Apply changes
4. ✅ Log audit entry
5. ✅ Notify if restart required
6. ✅ Return clear response

### 3. Restart Handling

```bash
# After config change requiring restart
sudo systemctl restart attendance-dashboard

# Or for full system
sudo systemctl restart attendance.service
```

### 4. Monitoring

Monitor audit log:
```bash
tail -f data/logs/config_audit.log | jq .
```

---

## Testing

### Test Configuration Update

```bash
# Save current config
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8080/config > /tmp/current_config.json

# Make a change
curl -X PUT http://localhost:8080/config \
  -H "Authorization: Bearer $API_KEY" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -d '{"cloud":{"sync_interval":120}}'

# Verify change
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8080/config | jq .cloud.sync_interval

# Rollback if needed
BACKUP=$(curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8080/config/backups | jq -r '.backups[0].filename')

curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  "http://localhost:8080/config/rollback?backup=$BACKUP"
```

---

## Migration Guide

### Phase 1: Add Read-Only Admin Key Check
- Add `DASHBOARD_ADMIN_KEY` to `.env`
- Implement `_check_admin_permission()`
- Keep current behavior for viewing

### Phase 2: Implement PUT Endpoint
- Add `do_PUT()` method
- Implement validation
- Add backup mechanism
- Add audit logging

### Phase 3: Add Backup Management
- Implement backup listing
- Add rollback endpoint
- Test recovery procedures

### Phase 4: Frontend Integration
- Build admin UI components
- Add change preview
- Implement confirmation dialogs

---

## Troubleshooting

### Configuration Update Failed

**Check:**
1. Admin key is correct (`DASHBOARD_ADMIN_KEY` in `.env`)
2. Request includes both API key and admin key
3. JSON is valid
4. Values pass validation
5. File permissions allow writing to `config/`

### Rollback Failed

**Check:**
1. Backup file exists in `config/backups/`
2. Backup file is valid JSON
3. File permissions on `config/config.json`

### Changes Not Applied

**Check:**
1. Service restart if required
2. Config file actually updated: `cat config/config.json | jq .`
3. No syntax errors in updated config

---

## Notes for Implementation

⚠️ **Important Reminders:**

1. **Two-Key System**: Regular API key for viewing, admin key for changes
2. **Always Backup**: Create backup before any modification
3. **Audit Everything**: Log all changes with IP and timestamp
4. **Validate Input**: Never trust client input
5. **Restart Detection**: Notify user when restart needed
6. **Sensitive Fields**: Block API updates to credentials (use .env only)
7. **Rollback Ready**: Keep last 10 backups minimum
8. **Test Thoroughly**: Test rollback procedure before production

---

**Status:** Documentation Complete  
**Implementation Required:** Backend changes to `admin_dashboard.py`  
**Frontend Required:** React components for admin UI  
**Security Level:** Two-factor (API key + Admin key)
