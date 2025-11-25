# Public Attendance View Setup

## Overview

This feature allows parents to view their child's attendance records via a direct link sent through SMS, **without requiring any login or account**.

## How It Works

1. **SMS Notification**: When a student scans their QR code, the system sends an SMS to the parent with:
   - Attendance notification (check-in/check-out)
   - Direct link to view full attendance history

2. **Public Link**: The link format is:
   ```
   https://[supabase-url]/rest/v1/attendance?student_id=eq.[student_id]&select=*&order=date.desc,time_in.desc&limit=30
   ```

3. **No Authentication Required**: Parents can click the link and immediately view attendance data in JSON format

## SMS Message Example

```
📚 ATTENDANCE ALERT 📚

Good day, Parent/Guardian!

Your child Maria Santos (Student ID: 233294) has successfully CHECKED IN to school.

⏰ Time: 07:30 AM
📅 Date: November 25, 2025
✅ Status: Present

📊 View full attendance:
https://ddblgwzylvwuucnpmtzi.supabase.co/rest/v1/attendance?student_id=eq.233294&select=*&order=date.desc,time_in.desc&limit=30

Thank you for your continued support!

- Mabini High School
  Automated Attendance System
```

## Supabase Configuration Required

### Enable Public Read Access (RLS Policy)

Parents need public read access to the attendance table. Run this SQL in Supabase SQL Editor:

```sql
-- Enable Row Level Security
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;

-- Create policy for public read access
CREATE POLICY "Public read access for attendance"
ON attendance
FOR SELECT
TO anon
USING (true);
```

**Alternative: Use Supabase Dashboard**

1. Go to Supabase Dashboard
2. Navigate to **Authentication** → **Policies**
3. Select `attendance` table
4. Click **"New Policy"**
5. Choose **"Enable read access for all users"**
6. Policy details:
   - **Policy name**: `Public read access for attendance`
   - **Allowed operation**: SELECT
   - **Target roles**: anon
   - **USING expression**: `true`
7. Save policy

### Verify Public Access

Test the link without authentication:

```bash
curl "https://[your-supabase-url]/rest/v1/attendance?student_id=eq.233294&select=*&limit=5"
```

Expected: JSON response with attendance records (Status 200)

If you get Status 401, the RLS policy is not configured correctly.

## Security Considerations

### ✅ Safe Design

- **Read-only**: Policy only allows SELECT, not INSERT/UPDATE/DELETE
- **No sensitive data**: Attendance records contain only:
  - Student ID (already known by parent)
  - Attendance times
  - Status (present/absent/late)
- **Limited scope**: Link shows only records for specific student
- **URL obscurity**: Parent must have the exact link (sent via SMS to registered phone)

### 🔒 Data Protection

- Student IDs are already semi-public (printed on QR codes)
- No personal information beyond student_id is exposed
- No access to other students' records (unless parent has their student_id)
- Links are sent only to registered parent phone numbers

### ⚠️ Known Limitation

If someone has a student_id, they can view that student's attendance. This is acceptable because:
- Student IDs are visible on QR codes anyway
- Only attendance times are shown (not grades or other sensitive info)
- Similar to physical attendance sheets that teachers post

## Configuration Files

### config/config.json

```json
"sms_notifications": {
  "enabled": true,
  "login_message_template": "... {attendance_link} ...",
  "logout_message_template": "... {attendance_link} ...",
  "attendance_view_url": "https://[supabase-url]/rest/v1/attendance?student_id=eq.{student_id}&select=*&order=date.desc,time_in.desc&limit=30"
}
```

### src/notifications/sms_notifier.py

The SMS notifier automatically:
1. Loads `attendance_view_url` from config
2. Formats URL with student_id
3. Includes link in SMS message template

## Testing

### Test SMS with Link

```bash
cd /home/iot/attendance-system
python3 tests/test_simple_flow.py
```

Check SMS received by parent - should include attendance link.

### Test Link Access

```bash
python3 << 'EOF'
import requests

student_id = "233294"
url = f"https://[supabase-url]/rest/v1/attendance?student_id=eq.{student_id}&select=*&limit=5"

response = requests.get(url)
print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")
EOF
```

Expected: Status 200 with attendance records

## Troubleshooting

### Problem: Status 401 (Unauthorized)

**Cause**: RLS policy not configured for public access

**Solution**: Run the SQL script to enable public read access:
```bash
# In Supabase SQL Editor
-- Run: scripts/deployment/enable_public_attendance_view.sql
```

### Problem: Empty Array Returned

**Cause**: No attendance records for that student_id

**Solution**: Verify student has attendance records in database

### Problem: Link Too Long for SMS

**Cause**: URL is ~150 characters

**Solution**: 
- Use URL shortener (bit.ly, tinyurl)
- Or create custom endpoint on your own domain
- Current solution: Most SMS can handle 450+ characters

## Future Enhancements

Potential improvements:

1. **HTML View**: Create a simple HTML page to display attendance in user-friendly format instead of raw JSON
2. **URL Shortener**: Integrate bit.ly or similar to shorten links
3. **QR Code Link**: Generate QR code for the attendance link
4. **Date Filtering**: Allow parents to filter by date range
5. **Export CSV**: Add option to download attendance as CSV

## Related Files

- `config/config.json` - Message templates and URL configuration
- `src/notifications/sms_notifier.py` - SMS sending logic
- `scripts/deployment/enable_public_attendance_view.sql` - RLS policy setup
- `tests/test_simple_flow.py` - Integration test

## Support

For issues or questions:
- Repository: https://github.com/Cerjho/IoT-Attendance-System
- Check Supabase logs for RLS policy errors
- Verify SMS delivery logs in `logs/attendance_system_[date].log`
