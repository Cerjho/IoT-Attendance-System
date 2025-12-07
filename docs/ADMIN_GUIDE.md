# Administrator Guide

Complete guide for managing the IoT Attendance System, including schedule configuration, SMS templates, notification preferences, and troubleshooting.

## Table of Contents

1. [Schedule Management](#schedule-management)
2. [SMS Template Management](#sms-template-management)
3. [Notification Preferences](#notification-preferences)
4. [Section Assignment](#section-assignment)
5. [System Monitoring](#system-monitoring)
6. [Troubleshooting](#troubleshooting)
7. [Common Tasks](#common-tasks)

---

## Schedule Management

### Understanding School Schedules

School schedules define time windows for attendance:
- **Morning Only**: Students attend 7:00 AM - 12:00 PM
- **Afternoon Only**: Students attend 1:00 PM - 6:00 PM
- **Both Sessions**: Students can attend either session
- **No Restriction**: No schedule validation (rare)

### Viewing Schedules

**Via Supabase Dashboard:**
1. Go to your Supabase project
2. Navigate to Table Editor
3. Select `school_schedules` table
4. View all defined schedules

**Via SQL:**
```sql
SELECT 
    id, 
    name, 
    morning_start_time, 
    morning_end_time,
    afternoon_start_time,
    afternoon_end_time,
    is_default,
    status
FROM school_schedules
ORDER BY name;
```

### Creating a New Schedule

**Via Supabase Dashboard:**
1. Go to Table Editor → `school_schedules`
2. Click "Insert row"
3. Fill in:
   - **name**: Descriptive name (e.g., "Morning Only")
   - **morning_start_time**: e.g., "07:00:00"
   - **morning_end_time**: e.g., "12:00:00"
   - **afternoon_start_time**: e.g., "13:00:00" (or NULL)
   - **afternoon_end_time**: e.g., "18:00:00" (or NULL)
   - **is_default**: Set TRUE for default schedule
   - **status**: "active"
4. Click "Save"

**Via SQL:**
```sql
INSERT INTO school_schedules (
    name,
    morning_start_time,
    morning_end_time,
    afternoon_start_time,
    afternoon_end_time,
    is_default,
    status
) VALUES (
    'Morning Only',
    '07:00:00',
    '12:00:00',
    NULL,
    NULL,
    FALSE,
    'active'
);
```

### Setting Default Schedule

Only one schedule should be marked as default:

```sql
-- Clear all defaults
UPDATE school_schedules SET is_default = FALSE;

-- Set new default
UPDATE school_schedules 
SET is_default = TRUE 
WHERE name = 'Both Sessions';
```

### Deactivating a Schedule

```sql
UPDATE school_schedules 
SET status = 'inactive' 
WHERE name = 'Old Schedule';
```

---

## SMS Template Management

### Understanding Templates

The system uses 8 notification types:
- **check_in**: Normal check-in notification
- **check_out**: Normal check-out notification
- **late_arrival**: Student arrived late
- **early_departure**: Student left early
- **absence_detected**: Student absent
- **schedule_violation**: Wrong schedule scan attempt
- **multiple_scans**: Duplicate scan detected
- **system_alert**: System-generated alerts

### Viewing Templates

**Via Supabase Dashboard:**
1. Go to Table Editor → `sms_templates`
2. View all templates

**Via SQL:**
```sql
SELECT 
    template_type,
    template_name,
    message_template,
    variables,
    is_active
FROM sms_templates
ORDER BY template_type;
```

**Via API:**
```bash
export $(cat .env | grep -v '^#' | xargs)

curl -X GET "${SUPABASE_URL}/rest/v1/sms_templates" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"
```

### Template Variables

Templates support these variables (use `{{variable}}` format):
- `{{student_name}}`: Student full name
- `{{student_number}}`: Student ID/number
- `{{time}}`: Formatted time (e.g., "07:30 AM")
- `{{date}}`: Formatted date (e.g., "December 7, 2025")
- `{{school_name}}`: School name
- `{{attendance_link}}`: Link to view attendance
- `{{minutes_late}}`: Minutes late (for late_arrival)
- `{{expected_session}}`: Expected session (for violations)
- `{{attempted_session}}`: Attempted session (for violations)

### Editing a Template

**Via Supabase Dashboard:**
1. Go to Table Editor → `sms_templates`
2. Find the template row
3. Click to edit
4. Modify `message_template` field
5. Click "Save"

**Via SQL:**
```sql
UPDATE sms_templates 
SET message_template = 'Good day! {{student_name}} ({{student_number}}) checked in at {{time}}. - {{school_name}}'
WHERE template_type = 'check_in';
```

**Example: Customize Late Arrival Message**
```sql
UPDATE sms_templates 
SET message_template = '⚠️ LATE: {{student_name}} arrived {{minutes_late}} minutes late at {{time}} on {{date}}. Please ensure punctuality. - {{school_name}}'
WHERE template_type = 'late_arrival';
```

### Creating a Custom Template

```sql
INSERT INTO sms_templates (
    template_type,
    template_name,
    message_template,
    variables,
    is_active
) VALUES (
    'custom_alert',
    'Custom Alert Template',
    'ALERT: {{student_name}} - {{custom_message}} at {{time}}',
    '["student_name", "custom_message", "time", "school_name"]',
    TRUE
);
```

### Deactivating a Template

```sql
UPDATE sms_templates 
SET is_active = FALSE 
WHERE template_type = 'multiple_scans';
```

### Testing Templates

**Fetch specific template:**
```bash
export $(cat .env | grep -v '^#' | xargs)

curl -X POST "${SUPABASE_URL}/rest/v1/rpc/get_sms_template" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"template_type_param": "check_in"}'
```

**Run test suite:**
```bash
python utils/test-scripts/test_templates_preferences.py
```

---

## Notification Preferences

### Understanding Preferences

Parents can customize:
- Which notification types to receive
- Quiet hours (no notifications during sleep)
- Per-student preferences
- Unsubscribe option

### Viewing Preferences

**Via SQL:**
```sql
SELECT 
    phone_number,
    student_id,
    notifications_enabled,
    quiet_hours_start,
    quiet_hours_end,
    notification_types
FROM notification_preferences
ORDER BY phone_number;
```

### Creating Preference Entry

```sql
INSERT INTO notification_preferences (
    phone_number,
    student_id,
    notifications_enabled,
    quiet_hours_start,
    quiet_hours_end,
    notification_types
) VALUES (
    '+639171234567',
    '3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4'::uuid,
    TRUE,
    '22:00:00',
    '06:00:00',
    '["check_in", "check_out", "late_arrival", "absence_detected"]'
);
```

### Updating Preferences

**Change quiet hours:**
```sql
UPDATE notification_preferences 
SET quiet_hours_start = '23:00:00',
    quiet_hours_end = '05:00:00'
WHERE phone_number = '+639171234567';
```

**Disable specific notifications:**
```sql
UPDATE notification_preferences 
SET notification_types = '["late_arrival", "absence_detected"]'
WHERE phone_number = '+639171234567';
```

**Unsubscribe a parent:**
```sql
UPDATE notification_preferences 
SET notifications_enabled = FALSE 
WHERE phone_number = '+639171234567';
```

### Testing Preference Checks

```bash
export $(cat .env | grep -v '^#' | xargs)

curl -X POST "${SUPABASE_URL}/rest/v1/rpc/should_send_notification" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_param": "+639171234567",
    "student_id_param": "3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4",
    "notification_type": "check_in"
  }'
```

Expected response: `true` or `false`

---

## Section Assignment

### Understanding Section Schedules

Each section is assigned a schedule that determines:
- When students can scan (morning/afternoon/both)
- Validation rules applied during scanning
- Late arrival threshold

### Viewing Section Assignments

**Via Script:**
```bash
python scripts/assign_schedules.py --show
```

**Via SQL:**
```sql
SELECT 
    s.section_code,
    s.section_name,
    sch.name as schedule_name
FROM sections s
LEFT JOIN school_schedules sch ON s.schedule_id = sch.id
ORDER BY s.section_code;
```

### Assigning Schedules

**Assign default schedule to all sections:**
```bash
python scripts/assign_schedules.py --default-all
```

**Assign schedule by pattern:**
```bash
# All STEM sections get Morning Only schedule
python scripts/assign_schedules.py --pattern "STEM" --schedule "Morning Only"

# All Grade 11 sections get Afternoon Only schedule
python scripts/assign_schedules.py --pattern "11-" --schedule "Afternoon Only"
```

**Assign to specific sections:**
```bash
python scripts/assign_schedules.py --sections "11-STEM-A" "11-STEM-B" --schedule "Morning Only"
```

**Via SQL:**
```sql
-- Assign specific section
UPDATE sections 
SET schedule_id = (SELECT id FROM school_schedules WHERE name = 'Morning Only')
WHERE section_code = '11-STEM-A';

-- Assign all unassigned sections to default
UPDATE sections 
SET schedule_id = (SELECT id FROM school_schedules WHERE is_default = TRUE)
WHERE schedule_id IS NULL;
```

### Bulk Assignment Example

```bash
# Step 1: Assign default to all
python scripts/assign_schedules.py --default-all

# Step 2: Override specific sections
python scripts/assign_schedules.py --pattern "STEM" --schedule "Morning Only"
python scripts/assign_schedules.py --pattern "ABM" --schedule "Afternoon Only"

# Step 3: Verify assignments
python scripts/assign_schedules.py --show
```

---

## System Monitoring

### Check System Status

```bash
python scripts/status.py
```

### Check Schedule Validation Stats

```python
from src.attendance.schedule_validator import ScheduleValidator

validator = ScheduleValidator()
stats = validator.get_schedule_stats()

print(f"Total students: {stats['total']}")
print(f"Morning only: {stats['morning']}")
print(f"Afternoon only: {stats['afternoon']}")
print(f"Both sessions: {stats['both']}")
print(f"No schedule: {stats['none']}")
```

### Check Template Cache Status

```python
from src.notifications.template_cache import TemplateCache

cache = TemplateCache()
stats = cache.get_cache_stats()

print(f"Total templates: {stats['total_templates']}")
print(f"Active templates: {stats['active_templates']}")
print(f"Cache age: {stats.get('cache_age_hours', 0):.1f} hours")
print(f"Is stale: {stats['is_stale']}")
```

### View Recent Logs

```bash
# System logs
tail -f data/logs/system.log

# Schedule validation events
grep -i "schedule" data/logs/system.log | tail -20

# Template fetch events
grep -i "template" data/logs/system.log | tail -20
```

### Monitor Validation Rejections

```bash
# Count wrong-schedule rejections today
grep "WRONG_SESSION" data/logs/system.log | grep "$(date +%Y-%m-%d)" | wc -l

# Show rejected scans
grep "WRONG_SESSION" data/logs/system.log | tail -10
```

---

## Troubleshooting

### Schedule Validation Issues

**Problem: All scans rejected**
```bash
# Check if schedules are assigned
python scripts/assign_schedules.py --show

# If no schedules assigned, assign default
python scripts/assign_schedules.py --default-all

# Force roster sync to update local cache
python scripts/force_sync.py --roster
```

**Problem: Wrong schedule assigned to section**
```bash
# Check current assignment
python scripts/assign_schedules.py --show

# Reassign correct schedule
python scripts/assign_schedules.py --sections "11-STEM-A" --schedule "Morning Only"

# Force roster sync
python scripts/force_sync.py --roster
```

### Template Issues

**Problem: Old templates still being used**
```bash
# Refresh templates from server
python -c "
from src.notifications.template_cache import TemplateCache
cache = TemplateCache()
cache.clear_cache()
print('Cache cleared. Restart system to refresh.')
"

# Restart system
bash scripts/start_attendance.sh
```

**Problem: Templates not found**
```bash
# Check if migration deployed
export $(cat .env | grep -v '^#' | xargs)
curl "${SUPABASE_URL}/rest/v1/sms_templates?select=count" \
  -H "apikey: ${SUPABASE_KEY}"

# If empty, deploy migration
bash scripts/deploy_server_config.sh
```

### Notification Issues

**Problem: No SMS being sent**
1. Check SMS configuration in `config/config.json`
2. Verify credentials in `.env`
3. Test SMS gateway connection
4. Check notification preferences in database

**Problem: Duplicate SMS sent**
- System has 5-minute cooldown by default
- Check `cooldown_minutes` in config
- Review `recent_notifications` cache

---

## Common Tasks

### Daily Operations

**Morning Startup:**
```bash
# Start system
bash scripts/start_attendance.sh

# Verify system health
python scripts/status.py

# Check schedule sync
python utils/test-scripts/test_schedule_validation.py
```

**End of Day:**
```bash
# View attendance summary
tail -100 data/logs/system.log | grep "attendance recorded"

# Check for validation issues
grep "WRONG_SESSION\|NO_SCHEDULE" data/logs/system.log | wc -l
```

### Weekly Maintenance

```bash
# Refresh templates from server
python -c "
from src.notifications.template_cache import TemplateCache
cache = TemplateCache()
cache.clear_cache()
"
bash scripts/start_attendance.sh

# Verify schedule assignments
python scripts/assign_schedules.py --show

# Run full test suite
python utils/test-scripts/test_schedule_validation.py
python utils/test-scripts/test_templates_preferences.py
```

### Semester Updates

**Updating schedules for new semester:**
```sql
-- 1. Create new schedules if needed
INSERT INTO school_schedules (...) VALUES (...);

-- 2. Reassign sections
-- Via script:
python scripts/assign_schedules.py --default-all

-- 3. Force roster sync on all devices
python scripts/force_sync.py --roster

-- 4. Verify on test device
python utils/test-scripts/test_schedule_validation.py
```

### Emergency Procedures

**Disable schedule validation temporarily:**
```json
// In config/config.json
{
  "schedule_validation": {
    "enabled": false
  }
}
```

**Disable SMS notifications temporarily:**
```json
// In config/config.json
{
  "sms": {
    "enabled": false
  }
}
```

**Emergency template update:**
```sql
-- Update template immediately
UPDATE sms_templates 
SET message_template = 'URGENT: {{student_name}} - Contact school immediately.'
WHERE template_type = 'system_alert';

-- Clear cache on devices (requires restart)
```

---

## Best Practices

### Schedule Management
1. Always have one default schedule
2. Test schedule changes on one device first
3. Update schedules during off-hours
4. Document schedule changes

### Template Management
1. Keep templates concise (SMS is 160 chars)
2. Test templates before deploying
3. Include school name for context
4. Maintain consistent formatting

### Section Assignment
1. Assign schedules in bulk by pattern
2. Verify assignments after changes
3. Force roster sync after bulk updates
4. Keep assignment records

### Monitoring
1. Check logs daily
2. Monitor validation rejection rates
3. Review SMS delivery status weekly
4. Maintain system health checks

---

## Support

### Documentation References
- [Schedule Validation Guide](SCHEDULE_VALIDATION.md)
- [Server-Side Config Guide](SERVER_SIDE_CONFIG.md)
- [System Overview](technical/SYSTEM_OVERVIEW.md)

### Test Scripts
- `utils/test-scripts/test_schedule_validation.py`
- `utils/test-scripts/test_templates_preferences.py`

### Management Scripts
- `scripts/assign_schedules.py`
- `scripts/deploy_server_config.sh`
- `scripts/force_sync.py`
- `scripts/status.py`

### Log Files
- `data/logs/system.log` - Main system log
- `data/logs/error.log` - Error log
- `data/logs/sms.log` - SMS notification log

---

**Last Updated:** December 7, 2025  
**Version:** 2.0 (Server-Side Configuration)
