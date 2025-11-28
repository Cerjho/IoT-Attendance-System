# SMS Notification Features Guide

## Overview
Enhanced SMS notification system with concise messages, smart alerts, and parent preferences.

---

## Message Templates

### 1. **Check-In** (Default: Enabled)
```
📚 MABINI HIGH SCHOOL

✅ CHECK-IN: Maria Santos
🕐 09:00 AM | Nov 28, 2025

View: [link]
```
**Length**: ~65 characters (excluding link)

### 2. **Check-Out** (Default: Enabled)
```
📚 MABINI HIGH SCHOOL

🏁 CHECK-OUT: Maria Santos
🕐 03:30 PM | Nov 28, 2025

View: [link]
```

### 3. **Late Arrival** (Default: Enabled)
```
⚠️ LATE ARRIVAL

Maria Santos checked in at 09:25 AM
(25 mins late)
📅 Nov 28, 2025

View: [link]

- Mabini High School
```

### 4. **No Check-Out Alert** (Default: Disabled)
```
⚠️ NO CHECK-OUT

Maria Santos did not check out today.
Last seen: 09:00 AM

Please verify.

View: [link]

- Mabini High School
```

### 5. **Absence Alert** (Default: Disabled)
```
❗ ABSENCE ALERT

Maria Santos not detected at school today (Nov 28, 2025).

If excused, please contact office.

View: [link]

- Mabini High School
```

### 6. **Weekly Summary** (Default: Disabled)
```
📊 WEEKLY SUMMARY

Maria Santos
Present: 4/5
Late: 1
Absent: 0

View: [link]

- Mabini High School
```

### 7. **Monthly Summary** (Default: Disabled)
```
📊 MONTHLY SUMMARY

Maria Santos
Present: 18/20 (90%)
Late: 2 times
Absent: 0 days

View: [link]

- Mabini High School
```

---

## Smart Features

### Quiet Hours
- **Default**: 22:00 (10 PM) to 06:00 (6 AM)
- No SMS sent during sleep hours
- Configurable in `config.json`

### Duplicate Prevention
- **Cooldown**: 5 minutes between same notification type
- Prevents spam if student scans multiple times
- Per-student, per-notification-type tracking

### Unsubscribe Option
- Automatic "Reply STOP to unsubscribe" text
- SMS compliance feature
- Can be disabled in config

---

## Configuration

### Enable/Disable Notification Types

In `config/config.json`:

```json
"notification_preferences": {
  "check_in": true,        // ✅ Enabled by default
  "check_out": true,       // ✅ Enabled by default
  "late_arrival": true,    // ✅ Enabled by default
  "absence": false,        // ❌ Disabled (requires manual setup)
  "no_checkout": false,    // ❌ Disabled (requires manual setup)
  "weekly_summary": false, // ❌ Disabled (requires manual setup)
  "monthly_summary": false // ❌ Disabled (requires manual setup)
}
```

### Quiet Hours Setup

```json
"quiet_hours": {
  "enabled": true,
  "start": "22:00",  // 10 PM
  "end": "06:00"     // 6 AM
}
```

### Cooldown Configuration

```json
"duplicate_sms_cooldown_minutes": 5
```

---

## Cost Optimization

### Message Length Comparison

| Type | Old Template | New Template | Savings |
|------|-------------|--------------|---------|
| Check-In | ~180 chars | ~65 chars | **63%** |
| Check-Out | ~180 chars | ~65 chars | **63%** |

**SMS Cost Reduction**: Up to **63% fewer characters** per message!

### Recommended Settings for Cost Savings

1. **Disable optional alerts**:
   - Set `no_checkout` to `false` (parents can check web link)
   - Set `weekly_summary` to `false` (use monthly only)

2. **Enable quiet hours**:
   - Prevents unnecessary overnight SMS

3. **Use cooldown**:
   - Prevents duplicate SMS if student rescans

---

## Usage Examples

### Basic Check-In Flow
```
1. Student scans QR code at 9:00 AM
2. System checks: 
   - Is it quiet hours? ❌ No (daytime)
   - Was SMS sent in last 5 mins? ❌ No
   - Is check_in enabled? ✅ Yes
3. SMS sent to parent
4. Cooldown timer starts (5 minutes)
```

### Late Arrival Flow
```
1. Student scans at 9:25 AM (25 mins late)
2. System checks:
   - Is it quiet hours? ❌ No
   - Is late_arrival enabled? ✅ Yes
   - Calculate minutes late: 25 minutes
3. SMS sent with late alert
4. Status marked as "late" in database
```

### No Check-Out Alert (End of Day)
```
1. System runs at 5:00 PM
2. Checks all students with check-in but no check-out
3. For each student:
   - Is no_checkout enabled? ✅ Yes
   - Is parent phone available? ✅ Yes
4. SMS sent to parents
```

---

## Testing

### Test SMS Notification
```bash
python3 test_sms_message.py
```

### Test with Real Student
```bash
# Uses student 221566 (John Paolo Gonzales)
python3 test_sms_message.py --student 221566
```

### Verify Configuration
```bash
# Check SMS templates
cat config/config.json | grep -A 20 "sms_notifications"
```

---

## Troubleshooting

### SMS Not Sending

1. **Check Configuration**:
   ```bash
   grep "enabled" config/config.json | grep sms
   ```

2. **Verify Credentials**:
   ```bash
   grep "SMS_" .env
   ```

3. **Check Logs**:
   ```bash
   tail -f data/logs/attendance_*.log | grep SMS
   ```

### SMS Sending But Not Received

1. **Verify Phone Format**:
   - Must be in format: `09XXXXXXXXX` or `+639XXXXXXXXX`

2. **Check Quiet Hours**:
   - Current time between 22:00-06:00?

3. **Check Cooldown**:
   - Was SMS sent in last 5 minutes?

### Cost Too High

1. **Disable Optional Alerts**:
   - Set `weekly_summary` and `monthly_summary` to `false`
   - Keep only check_in and late_arrival

2. **Increase Cooldown**:
   - Change `duplicate_sms_cooldown_minutes` to `10` or `15`

---

## Future Enhancements

Potential additions (not yet implemented):

- [ ] Two-way SMS (parents can reply)
- [ ] Custom SMS per parent preference
- [ ] Photo attachments via MMS
- [ ] Multi-language support
- [ ] Bulk SMS for announcements
- [ ] SMS delivery reports

---

## Support

For issues or questions:
- Check logs: `data/logs/`
- Review config: `config/config.json`
- Test connection: `python3 test_sms_message.py`

**School Contact**: [Your School Office Number]
