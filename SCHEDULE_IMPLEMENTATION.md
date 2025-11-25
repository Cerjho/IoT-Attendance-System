# School Schedule Implementation - Complete

## Overview
The IoT attendance system now supports **dual-session** school schedules with separate **morning** and **afternoon** classes, tracking both **arrival (login)** and **dismissal (logout)** times.

---

## Schedule Configuration

### Morning Class
- **Class Hours:** 7:00 AM - 12:00 PM
- **Login Window:** 6:30 AM - 7:30 AM (arrival tracking)
- **Logout Window:** 11:30 AM - 12:30 PM (dismissal tracking)
- **Late Threshold:** 15 minutes after class start

### Afternoon Class
- **Class Hours:** 1:00 PM - 5:00 PM
- **Login Window:** 12:30 PM - 1:30 PM (arrival tracking)
- **Logout Window:** 4:30 PM - 5:30 PM (dismissal tracking)
- **Late Threshold:** 15 minutes after class start

---

## How It Works

### 1. **Auto-Detection**
The system automatically detects:
- Current session (morning/afternoon)
- Expected scan type (login/logout)
- Attendance status (present/late)

### 2. **Login (Arrival) Tracking**
When a student scans during login window:
```
Time: 7:10 AM (Morning class)
→ Detected: Login scan
→ Status: Present (on time)
→ Records: time_in = 07:10:00
```

### 3. **Logout (Dismissal) Tracking**
When a student scans during logout window:
```
Time: 11:50 AM (Morning class)
→ Detected: Logout scan
→ Status: Present
→ Records: time_out = 11:50:00
```

### 4. **Late Arrival Detection**
```
Time: 7:20 AM (Morning class)
→ 20 minutes after start (7:00 AM)
→ Status: Late (threshold: 15 min)
→ Records: time_in = 07:20:00, status = late
```

---

## Database Schema

### Supabase Attendance Table
```sql
attendance (
    id UUID PRIMARY KEY,
    student_id UUID,           -- Student reference
    date DATE,                 -- Attendance date
    time_in TIME,              -- Login/arrival time
    time_out TIME,             -- Logout/dismissal time (optional)
    status VARCHAR,            -- present, late, absent, excused
    device_id VARCHAR,         -- IoT device identifier
    remarks TEXT,              -- QR code data, notes
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
```

### Local SQLite Cache
```sql
attendance (
    id INTEGER PRIMARY KEY,
    student_id TEXT,
    timestamp TEXT,            -- Scan timestamp
    photo_path TEXT,           -- Photo file path
    qr_data TEXT,              -- QR code data
    scan_type TEXT,            -- 'time_in' or 'time_out'
    status TEXT,               -- 'present' or 'late'
    synced INTEGER DEFAULT 0
)
```

---

## Usage Examples

### Scenario 1: Morning Student - Full Day
```
7:05 AM  → Student scans QR
         → Login detected (morning session)
         → Status: Present
         → Saved: time_in = 07:05:00

11:55 AM → Student scans QR again
         → Logout detected (morning session)
         → Status: Present
         → Updated: time_out = 11:55:00
```

### Scenario 2: Afternoon Student
```
12:50 PM → Student scans QR
         → Login detected (afternoon session)
         → Status: Present
         → Saved: time_in = 12:50:00

4:55 PM  → Student scans QR again
         → Logout detected (afternoon session)
         → Status: Present
         → Updated: time_out = 16:55:00
```

### Scenario 3: Late Arrival
```
7:25 AM  → Student scans QR
         → Login detected (morning session)
         → 25 minutes after start (threshold: 15 min)
         → Status: Late
         → Saved: time_in = 07:25:00, status = late
```

### Scenario 4: Full-Day Student (Both Sessions)
```
7:10 AM  → Morning login
         → Record 1: date=2025-11-25, time_in=07:10, session=morning

12:00 PM → Morning logout
         → Update Record 1: time_out=12:00

1:05 PM  → Afternoon login
         → Record 2: date=2025-11-25, time_in=13:05, session=afternoon

5:00 PM  → Afternoon logout
         → Update Record 2: time_out=17:00
```

---

## Features

### ✅ Implemented

1. **Dual Session Support**
   - Morning class (7 AM - 12 PM)
   - Afternoon class (1 PM - 5 PM)

2. **Login/Logout Tracking**
   - Separate windows for arrival and dismissal
   - Auto-detection of scan type

3. **Late Detection**
   - Configurable threshold (15 minutes default)
   - Automatic status assignment

4. **Duplicate Prevention**
   - 5-minute cooldown between scans
   - Allows different scan types (login → logout)
   - Allows different sessions (morning → afternoon)

5. **Smart Sync**
   - Uploads to Supabase with proper time_in/time_out
   - Handles both fields correctly
   - Maintains offline queue

---

## Configuration

### config/config.json
```json
{
  "school_schedule": {
    "morning_class": {
      "start_time": "07:00",
      "end_time": "12:00",
      "login_window_start": "06:30",
      "login_window_end": "07:30",
      "logout_window_start": "11:30",
      "logout_window_end": "12:30",
      "late_threshold_minutes": 15
    },
    "afternoon_class": {
      "start_time": "13:00",
      "end_time": "17:00",
      "login_window_start": "12:30",
      "login_window_end": "13:30",
      "logout_window_start": "16:30",
      "logout_window_end": "17:30",
      "late_threshold_minutes": 15
    },
    "auto_detect_session": true,
    "allow_early_arrival": true,
    "require_logout": true,
    "duplicate_scan_cooldown_minutes": 5
  }
}
```

---

## Testing

### Run Schedule Test
```bash
python3 utils/test_schedule.py
```

This will test:
- Session detection at different times
- Login/logout window detection
- Late status determination
- Duplicate scan prevention
- Multiple session handling

### Expected Output
```
⏰ 07:00 - Morning class start
   Session: morning
   Expected: time_in
   Status: present
   Login window: ✅
   Logout window: ❌

⏰ 11:45 - Morning logout window
   Session: morning
   Expected: time_out
   Status: present
   Login window: ❌
   Logout window: ✅

⏰ 13:00 - Afternoon class start
   Session: afternoon
   Expected: time_in
   Status: present
   Login window: ✅
   Logout window: ❌
```

---

## System Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    STUDENT SCANS QR CODE                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              SCHEDULE MANAGER DETERMINES:                   │
│  • Current Session (morning/afternoon)                      │
│  • Expected Scan Type (login/logout)                        │
│  • Attendance Status (present/late)                         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  CHECK DUPLICATE SCAN                       │
│  • Same session + same scan type? → Block                   │
│  • Within 5-minute cooldown? → Block                        │
│  • Different session or scan type? → Allow                  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  CAPTURE PHOTO & SAVE                       │
│  • Face detection + quality checks                          │
│  • Save to local SQLite                                     │
│  • Record: scan_type (time_in/time_out)                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   SYNC TO SUPABASE                          │
│  • Lookup: student_number → UUID                            │
│  • Split: timestamp → date + (time_in OR time_out)          │
│  • Upload: attendance record                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Benefits

### For Students
- ✅ Clear tracking of arrival and dismissal
- ✅ Transparent late status
- ✅ Multiple sessions supported (morning + afternoon)

### For Teachers/Admin
- ✅ Complete attendance records (in + out)
- ✅ Accurate time tracking
- ✅ Late arrival monitoring
- ✅ Session-based reporting

### For Parents
- ✅ SMS notifications for both login and logout
- ✅ Peace of mind knowing arrival/dismissal times
- ✅ Real-time updates

---

## Next Steps

1. **Integration with Main System**
   - Update `attendance_system.py` to use ScheduleManager
   - Add schedule info to UI display
   - Update SMS messages with scan type

2. **Database Update**
   - Add `scan_type` column to local SQLite
   - Ensure Supabase accepts time_out field

3. **Testing**
   - Test with real students across different times
   - Verify login/logout detection
   - Check SMS notifications

---

**Status:** ✅ **READY FOR INTEGRATION**  
**Files Created:**
- `src/attendance/schedule_manager.py` - Core schedule logic
- `utils/test_schedule.py` - Testing utility
- `config/config.json` - Updated with schedule config
- `src/cloud/cloud_sync.py` - Updated for time_out support
