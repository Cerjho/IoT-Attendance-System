# Server-Side Configuration Migration

## Overview

Moved configuration from local `config.json` to server-side database tables for centralized management. This eliminates the need to edit local config files on each device and enables dynamic updates.

## What Was Moved

### 1. School Schedules ✅
**Before:** Hardcoded in `config.json`
```json
"school_schedule": {
  "morning_class": { "start_time": "07:00", ... },
  "afternoon_class": { "start_time": "13:00", ... }
}
```

**After:** Stored in `school_schedules` table
- Managed via Supabase dashboard
- Multiple schedules per school
- Linked to sections via `sections.schedule_id`
- Already implemented ✅

### 2. SMS Templates 🆕
**Before:** Hardcoded in `config.json`
```json
"login_message_template": "📚 MABINI HIGH SCHOOL\n\n✅ CHECK-IN...",
"logout_message_template": "🏁 CHECK-OUT...",
...
```

**After:** Stored in `sms_templates` table
- 8 template types (check_in, check_out, late_arrival, etc.)
- Customizable per school
- Variable substitution support
- Active/inactive toggle

### 3. Notification Preferences 🆕
**Before:** Global settings in `config.json`
```json
"notification_preferences": {
  "check_in": true,
  "check_out": true,
  ...
}
```

**After:** Stored in `notification_preferences` table
- Per-parent customization
- Quiet hours per family
- Unsubscribe support
- Default preferences for new users

### 4. Device Metadata ✅
**Before:** Hardcoded in `config.json`
```json
"device_name": "IT Lab - Main Device",
"location": {
  "building": "Main Building",
  "floor": "Floor 1",
  "room": "IT Lab"
}
```

**After:** Stored in `iot_devices` table
- Managed centrally
- Linked to teaching assignments
- Dynamic location updates
- Already implemented ✅

## What Remains in config.json

Only **device-level technical settings** that don't need central management:

```json
{
  "camera": { ... },           // Hardware settings
  "photo": { ... },            // Capture settings
  "image_processing": { ... }, // Quality settings
  "logging": { ... },          // Local logs
  "buzzer": { ... },           // GPIO pins
  "rgb_led": { ... },          // GPIO pins
  "power_button": { ... },     // GPIO pins
  "network_timeouts": { ... }, // Connection settings
  "disk_monitor": { ... },     // Local storage
  "cloud": {
    "url": "${SUPABASE_URL}",  // Connection only
    "api_key": "${SUPABASE_KEY}"
  },
  "sms_notifications": {
    "username": "${SMS_USERNAME}", // Credentials only
    "api_url": "${SMS_API_URL}"
  }
}
```

## Database Schema

### sms_templates
```sql
CREATE TABLE sms_templates (
    id UUID PRIMARY KEY,
    template_name VARCHAR(50) UNIQUE,
    template_type VARCHAR(50),  -- check_in, check_out, etc.
    message_template TEXT,
    variables TEXT[],            -- Variable names used
    is_active BOOLEAN,
    school_name VARCHAR(200),
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### notification_preferences
```sql
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY,
    parent_phone VARCHAR(20),
    student_id UUID REFERENCES students(id),
    check_in_enabled BOOLEAN DEFAULT TRUE,
    check_out_enabled BOOLEAN DEFAULT TRUE,
    late_arrival_enabled BOOLEAN DEFAULT TRUE,
    schedule_violation_enabled BOOLEAN DEFAULT FALSE,
    quiet_hours_start TIME DEFAULT '22:00:00',
    quiet_hours_end TIME DEFAULT '06:00:00',
    quiet_hours_enabled BOOLEAN DEFAULT TRUE,
    unsubscribed BOOLEAN DEFAULT FALSE
);
```

## Migration Steps

### 1. Deploy Migration
```bash
cd /home/iot/attendance-system
bash scripts/deploy_schedules.sh
# Or manually:
psql $DATABASE_URL -f supabase/migrations/20251207000000_server_side_config.sql
```

### 2. Verify Tables Created
```sql
-- Check SMS templates
SELECT template_type, template_name, is_active 
FROM sms_templates;

-- Should show 8 templates (all active)
```

### 3. Update IoT Devices Code
Code changes needed to fetch from server:

**SMS Templates:**
```python
# OLD: Read from config
template = config['sms_notifications']['login_message_template']

# NEW: Fetch from database
def get_sms_template(template_type: str) -> str:
    response = requests.get(
        f"{supabase_url}/rest/v1/rpc/get_sms_template",
        params={"template_type_param": template_type},
        headers={"apikey": supabase_key}
    )
    data = response.json()
    return data[0]['message_template']
```

**Notification Check:**
```python
# Check if parent wants this notification
def should_send(phone: str, student_id: str, type: str) -> bool:
    response = requests.get(
        f"{supabase_url}/rest/v1/rpc/should_send_notification",
        params={
            "phone_param": phone,
            "student_id_param": student_id,
            "notification_type": type
        },
        headers={"apikey": supabase_key}
    )
    return response.json()
```

### 4. Update Devices
```bash
# Pull latest code
cd /home/iot/attendance-system
git pull origin main

# Restart system
bash scripts/start_attendance.sh
```

## Benefits

### For Administrators
- ✅ **Centralized Management** - Update all devices from one place
- ✅ **No SSH Required** - Edit via Supabase dashboard
- ✅ **Template Management** - Customize SMS messages easily
- ✅ **Per-School Branding** - Different templates per school
- ✅ **Version Control** - Track template changes
- ✅ **A/B Testing** - Test different message formats

### For Parents
- ✅ **Customizable Notifications** - Choose what alerts to receive
- ✅ **Quiet Hours** - Set family-specific do-not-disturb times
- ✅ **Unsubscribe Option** - Easy opt-out per student
- ✅ **Preference Portal** - Manage via web interface

### For Devices
- ✅ **Smaller Config Files** - Less local configuration
- ✅ **Dynamic Updates** - No restart needed for template changes
- ✅ **Consistent Behavior** - All devices use same templates
- ✅ **Fallback Support** - Continue working if server unavailable

## API Usage

### Get SMS Template
```http
POST /rest/v1/rpc/get_sms_template
Content-Type: application/json

{
  "template_type_param": "check_in"
}
```

**Response:**
```json
[{
  "template_name": "Check-In Notification",
  "message_template": "📚 {school_name}\n\n✅ CHECK-IN: {student_name}...",
  "variables": ["school_name", "student_name", "time", "date"],
  "school_name": "MABINI HIGH SCHOOL"
}]
```

### Check Notification Preference
```http
POST /rest/v1/rpc/should_send_notification
Content-Type: application/json

{
  "phone_param": "+639123456789",
  "student_id_param": "uuid-here",
  "notification_type": "check_in"
}
```

**Response:**
```json
true  // or false
```

### Update Parent Preferences
```http
PATCH /rest/v1/notification_preferences?parent_phone=eq.+639123456789&student_id=eq.uuid-here
Content-Type: application/json

{
  "late_arrival_enabled": false,
  "quiet_hours_start": "21:00:00",
  "quiet_hours_end": "07:00:00"
}
```

## Parent Preference Portal

Example interface for parents to manage preferences:

```html
<!-- Parent notification settings -->
<form>
  <h3>Notification Settings for [Student Name]</h3>
  
  <label>
    <input type="checkbox" checked> Check-In Notifications
  </label>
  <label>
    <input type="checkbox" checked> Check-Out Notifications
  </label>
  <label>
    <input type="checkbox" checked> Late Arrival Alerts
  </label>
  <label>
    <input type="checkbox"> Schedule Violation Alerts
  </label>
  
  <h4>Quiet Hours</h4>
  <label>Enable: <input type="checkbox" checked></label>
  <label>Start: <input type="time" value="22:00"></label>
  <label>End: <input type="time" value="06:00"></label>
  
  <button>Save Preferences</button>
  <button>Unsubscribe from All</button>
</form>
```

## Rollback Plan

If issues occur, restore hardcoded config:

```bash
# Revert to previous commit
git revert HEAD

# Or manually restore school_schedule section to config.json
```

System will fall back to local config if server templates unavailable.

## Testing

```bash
# Test SMS template retrieval
curl -X POST "${SUPABASE_URL}/rest/v1/rpc/get_sms_template" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"template_type_param": "check_in"}'

# Test notification check
curl -X POST "${SUPABASE_URL}/rest/v1/rpc/should_send_notification" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_param": "+639123456789",
    "student_id_param": "uuid-here",
    "notification_type": "check_in"
  }'
```

## Future Enhancements

1. **Template Versioning** - Track template history
2. **A/B Testing** - Test different message formats
3. **Scheduled Templates** - Different messages by time/day
4. **Multi-Language** - Templates in multiple languages
5. **Rich Media** - Support for images/links in SMS
6. **Analytics** - Track open rates and engagement

---

**Migration Date:** 2025-12-07  
**Status:** Ready for deployment  
**Impact:** All devices need code update to fetch server config
