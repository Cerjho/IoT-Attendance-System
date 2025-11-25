# 📱 SMS Parent Notifications - Quick Start

The attendance system now sends automatic SMS notifications to parents when students check in!

## ✅ Setup Status

- ✅ SMS Gateway configured and connected
- ✅ Cloud server: https://api.sms-gate.app
- ✅ Device ID: zmmfTkL3NacdGAfNqwD7q
- ✅ Database updated with parent_phone column
- ✅ Test connection successful

## 🚀 Quick Start

### 1. Add Parent Phone Numbers

**Single student:**
```bash
source venv/bin/activate
python manage_parents.py --add STU001 +1234567890 --name "Student Name"
```

**Bulk import from CSV:**
```bash
python manage_parents.py --import example_students.csv
```

### 2. View Students
```bash
# View students with parent phones
python manage_parents.py --view

# View all students
python manage_parents.py --view --all
```

### 3. Test SMS
```bash
# Test connection
python manage_parents.py --test-sms

# Send test SMS to your phone
python manage_parents.py --test-sms --phone +1234567890
```

### 4. Run Attendance System
```bash
./start_attendance.sh
```

**SMS will be sent automatically** when:
- Student scans QR code
- Face is detected
- Attendance is recorded
- Student has parent phone in database

## 📋 CSV Format

Create `students.csv`:
```csv
student_id,name,parent_phone
STU001,John Doe,+1234567890
STU002,Jane Smith,+1987654321
```

Then import:
```bash
python manage_parents.py --import students.csv
```

## 📱 SMS Message Format

```
Attendance Alert: John Doe (ID: STU001) checked in at 02:30 PM on November 23, 2025.
```

## ⚙️ Configuration

Edit `config/config.json`:
```json
{
  "sms_notifications": {
    "enabled": true,
    "send_on_capture": true
  }
}
```

## 🔍 Monitor SMS Activity

```bash
# Watch logs in real-time
tail -f logs/iot_attendance_system_*.log | grep -i sms

# View recent SMS
tail -50 logs/iot_attendance_system_*.log | grep "SMS notification"
```

## 📞 Phone Number Format

✅ **Correct:** `+1234567890` (international format with +)  
❌ **Wrong:** `1234567890` (missing +)  
❌ **Wrong:** `(123) 456-7890` (formatting)

## 🛠️ Troubleshooting

**SMS not sending?**
1. Check if parent phone is added: `python manage_parents.py --view`
2. Test connection: `python manage_parents.py --test-sms`
3. Check logs: `tail -f logs/*.log | grep -i sms`
4. Verify phone format includes + prefix

**Need help?**
- See full documentation: `SMS_NOTIFICATION_GUIDE.md`
- Check SMS Gateway app is running on your phone
- Verify internet connection

## 📚 Full Documentation

For complete details, see: **SMS_NOTIFICATION_GUIDE.md**

---

**Ready to use!** Just add parent phone numbers and start the system. 🎉
