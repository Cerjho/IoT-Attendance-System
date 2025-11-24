# SMS Parent Notification Feature - Documentation

**Date:** November 23, 2025  
**Feature:** SMS notifications to parents when students check in  
**Integration:** Android SMS Gateway Cloud Server

## 🎯 Overview

The attendance system now automatically sends SMS notifications to parents when their child checks in. This uses the Android SMS Gateway cloud server API to send real-time alerts.

## 📱 How It Works

### Attendance Flow with SMS
1. Student scans QR code
2. System detects face
3. Photo captured
4. Attendance recorded in database
5. **→ SMS notification sent to parent** ← NEW!
6. System returns to standby

### SMS Message Format
```
Attendance Alert: John Doe (ID: STU001) checked in at 02:30 PM on November 23, 2025.
```

## ⚙️ Configuration

### SMS Gateway Setup
Your Android SMS Gateway credentials are configured in `config/config.json`:

```json
{
  "sms_notifications": {
    "enabled": true,
    "username": "EWW3VZ",
    "password": "ri9-rbprxdf2ph",
    "device_id": "zmmfTkL3NacdGAfNqwD7q",
    "api_url": "https://api.sms-gate.app/3rdparty/v1/message",
    "message_template": "Attendance Alert: {student_name} (ID: {student_id}) checked in at {time} on {date}.",
    "send_on_capture": true,
    "retry_on_failure": true,
    "retry_attempts": 3
  }
}
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `enabled` | Enable/disable SMS notifications | `true` |
| `username` | SMS Gateway username | - |
| `password` | SMS Gateway password | - |
| `device_id` | SMS Gateway device ID | - |
| `api_url` | API endpoint URL | Cloud server URL |
| `message_template` | SMS message template | See above |
| `send_on_capture` | Send SMS immediately after attendance | `true` |
| `retry_on_failure` | Retry failed SMS attempts | `true` |
| `retry_attempts` | Number of retry attempts | `3` |

### Message Template Variables

You can customize the message template using these variables:
- `{student_id}` - Student's ID
- `{student_name}` - Student's name (or ID if name not set)
- `{time}` - Check-in time (e.g., "02:30 PM")
- `{date}` - Check-in date (e.g., "November 23, 2025")

## 📋 Managing Parent Phone Numbers

### Using the Management Script

The `manage_parents.py` script provides a complete interface for managing parent contact information.

#### View Students
```bash
# View students with parent phone numbers
source venv/bin/activate
python manage_parents.py --view

# View all students (including those without parent phones)
python manage_parents.py --view --all
```

#### Add/Update Parent Phone
```bash
# Add parent phone for a student
python manage_parents.py --add STU001 +1234567890

# Add with student name
python manage_parents.py --add STU001 +1234567890 --name "John Doe"
```

#### Import from CSV
Create a CSV file with this format:
```csv
student_id,name,parent_phone
STU001,John Doe,+1234567890
STU002,Jane Smith,+1987654321
STU003,Bob Johnson,+1555123456
```

Then import:
```bash
python manage_parents.py --import students.csv
```

#### Export to CSV
```bash
# Export to auto-generated filename
python manage_parents.py --export

# Export to specific file
python manage_parents.py --export my_students.csv
```

## 🧪 Testing SMS Notifications

### Test SMS Gateway Connection
```bash
source venv/bin/activate
python manage_parents.py --test-sms
```

Output:
```
================================================================================
SMS Notification Test
================================================================================

1. Testing SMS Gateway connection...
   Status: success
   Message: SMS Gateway connection OK
   
✓ Connection test successful!
   Use --phone <number> to send a test SMS

================================================================================
```

### Send Test SMS
```bash
python manage_parents.py --test-sms --phone +1234567890
```

This will:
1. Test the connection
2. Send a test attendance notification to the specified number
3. Report success/failure

## 🗄️ Database Schema

The `students` table now includes a `parent_phone` column:

```sql
CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    parent_phone TEXT,     -- NEW COLUMN
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Database Migration

The database schema is automatically updated when you first run the system. If you have an existing database, the new column will be added automatically.

To manually check/update your database:
```bash
sqlite3 data/attendance.db

-- Check table structure
.schema students

-- Add parent phone to existing student
UPDATE students SET parent_phone = '+1234567890' WHERE student_id = 'STU001';

-- View all students with parent phones
SELECT * FROM students WHERE parent_phone IS NOT NULL;
```

## 🔧 Troubleshooting

### SMS Not Sending

1. **Check if SMS is enabled**
   ```bash
   grep '"enabled"' config/config.json | grep sms -A 1
   ```
   Should show: `"enabled": true`

2. **Check credentials**
   Verify username, password, and device_id in config.json match your SMS Gateway app

3. **Test connection**
   ```bash
   python manage_parents.py --test-sms
   ```

4. **Check logs**
   ```bash
   tail -f logs/iot_attendance_system_*.log | grep -i sms
   ```

### Common Issues

**Issue:** "No parent phone number for student"  
**Solution:** Add parent phone using:
```bash
python manage_parents.py --add <student_id> <phone_number>
```

**Issue:** "SMS Gateway connection failed"  
**Solution:** 
- Verify internet connection
- Check SMS Gateway app is running on your phone
- Verify credentials in config.json
- Check device is online at https://api.sms-gate.app

**Issue:** "Authentication failed"  
**Solution:** Double-check username and password in config.json

**Issue:** SMS sent but not received  
**Solution:**
- Check phone number format (use E.164: +1234567890)
- Verify SMS Gateway device has signal
- Check SMS Gateway app logs on your phone

## 📞 Phone Number Format

Use E.164 international format:
- **Correct:** `+1234567890` (US/Canada)
- **Correct:** `+6281234567890` (Indonesia)
- **Incorrect:** `1234567890` (missing +)
- **Incorrect:** `(123) 456-7890` (formatting)

## 🔐 Security Notes

1. **Credentials Protection**
   - Keep `config/config.json` secure
   - Don't commit credentials to version control
   - Use environment variables for production

2. **SMS Gateway Security**
   - Your Android SMS Gateway credentials are stored securely
   - All communication uses HTTPS
   - Basic authentication is used for API calls

## 📊 Monitoring

### View SMS Activity in Logs
```bash
# Real-time monitoring
tail -f logs/iot_attendance_system_*.log | grep -i sms

# View recent SMS notifications
tail -100 logs/iot_attendance_system_*.log | grep "SMS notification sent"

# Count SMS sent today
grep "$(date +%Y-%m-%d)" logs/iot_attendance_system_*.log | grep -c "SMS notification sent"
```

### Check Which Students Have Parent Phones
```bash
python manage_parents.py --view
```

## 💡 Best Practices

1. **Import Parent Phones in Bulk**
   - Create a CSV with all student data
   - Import once using `--import`
   - Update individual records as needed

2. **Test Before Production**
   - Use `--test-sms` to verify setup
   - Send test to your own phone first
   - Confirm message format is correct

3. **Monitor Regularly**
   - Check logs for failed SMS
   - Verify parent phones are current
   - Update phone numbers as needed

4. **Customize Message Template**
   - Edit `message_template` in config.json
   - Keep messages concise (SMS character limit)
   - Include relevant information (student ID, name, time)

## 🚀 Quick Start Guide

### First-Time Setup

1. **Verify SMS Gateway is configured**
   ```bash
   python manage_parents.py --test-sms
   ```

2. **Add parent phone numbers**
   ```bash
   # Option A: Add individually
   python manage_parents.py --add STU001 +1234567890 --name "Student Name"
   
   # Option B: Import from CSV
   python manage_parents.py --import students.csv
   ```

3. **Test with a real attendance check**
   - Run the attendance system
   - Scan a QR code for a student with parent phone
   - Check if SMS is received

4. **Monitor logs**
   ```bash
   tail -f logs/iot_attendance_system_*.log
   ```

### Daily Operations

1. **Start attendance system** (SMS enabled automatically)
   ```bash
   ./start_attendance.sh
   ```

2. **Add new student's parent phone**
   ```bash
   python manage_parents.py --add <student_id> <phone>
   ```

3. **Check SMS status**
   ```bash
   tail -50 logs/iot_attendance_system_*.log | grep -i sms
   ```

## 📱 Android SMS Gateway App

Your SMS Gateway device details:
- **Username:** EWW3VZ
- **Password:** ri9-rbprxdf2ph
- **Device ID:** zmmfTkL3NacdGAfNqwD7q
- **Mode:** Cloud Server
- **API:** https://api.sms-gate.app/3rdparty/v1/message

### Managing the Gateway App

1. **Keep App Running**
   - App must be running to send SMS
   - Enable "Start on boot" in app settings
   - Disable battery optimization for the app

2. **Monitor Device**
   - Check device has internet connection
   - Verify device has cellular signal
   - Check app is in "Online" mode

3. **View Sent Messages**
   - Open SMS Gateway app
   - Check message history
   - Monitor for errors

## 🔄 Disabling SMS Notifications

To temporarily disable SMS:

1. **Edit config.json**
   ```json
   {
     "sms_notifications": {
       "enabled": false,
       ...
     }
   }
   ```

2. **Restart attendance system**
   ```bash
   # Stop current system (Ctrl+C)
   # Start again
   ./start_attendance.sh
   ```

Everything else continues to work normally (attendance recording, cloud sync, etc.).

## 📈 Features Summary

✅ **Automatic SMS notifications** when students check in  
✅ **Customizable message templates**  
✅ **Parent phone management** via CLI tool  
✅ **CSV import/export** for bulk operations  
✅ **Connection testing** before production  
✅ **Error handling and retries**  
✅ **Detailed logging** for monitoring  
✅ **E.164 phone number support**  
✅ **Cloud-based SMS gateway** (reliable delivery)  

## 📞 Support

For issues:
1. Check logs: `logs/iot_attendance_system_*.log`
2. Test connection: `python manage_parents.py --test-sms`
3. Review this documentation
4. Check Android SMS Gateway status on your phone

---

**Version:** 1.0  
**Date:** November 23, 2025  
**Integration:** Android SMS Gateway v1.51.3  
**Status:** Production Ready
