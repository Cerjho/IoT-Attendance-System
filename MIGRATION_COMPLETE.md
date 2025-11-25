# ✅ MIGRATION TO NEW SUPABASE SERVER - COMPLETE

**Date:** 25 November 2025  
**Old Server:** `https://ufckpgswkziojwoqosxw.supabase.co`  
**New Server:** `https://ddblgwzylvwuucnpmtzi.supabase.co`

---

## 🔄 Changes Applied

### 1. **Configuration Updated**
- ✅ `.env` - New Supabase URL and API key
- ✅ Local database reset (attendance.db cleared)

### 2. **Code Adaptations**

#### **`src/sync/roster_sync.py`** (Student Roster Sync)
**Updated to work with new schema:**

| Old Field | New Field | Mapping |
|-----------|-----------|---------|
| `student_id` | `student_number` | Direct mapping |
| `name` | `first_name + middle_name + last_name` | Concatenated |
| `parent_phone` | `parent_guardian_contact` | Direct mapping |
| N/A | `grade_level` | Downloaded for context |
| N/A | `section` | Downloaded for context |
| N/A | `status` | Filtered: only `active` |

**What it does:**
- Downloads all **active students** from Supabase
- Caches locally in SQLite for offline operation
- Maps new schema fields to local cache structure
- Enables fast QR code lookup (< 100ms)

#### **`src/cloud/cloud_sync.py`** (Attendance Upload)
**Updated to work with new attendance schema:**

| Old Format | New Format | Conversion |
|------------|------------|------------|
| `student_id` (string) | `student_id` (UUID) | Lookup via student_number |
| `timestamp` (datetime) | `date` + `time_in` | Split into DATE and TIME |
| `photo_url` | `remarks` | Stored in remarks field |
| `qr_data` | `remarks` | Stored in remarks field |
| N/A | `device_id` | Added from config |

**What it does:**
1. **Student UUID Lookup:** Queries students table to get UUID from student_number
2. **Date/Time Split:** Converts timestamp to separate date and time fields
3. **Attendance Insert:** Uploads to new attendance table structure
4. **Offline Queue:** Stores failed uploads for retry

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IOT ATTENDANCE DEVICE                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. QR CODE SCAN                                            │
│     └─> Student scans QR (student_number)                   │
│                                                             │
│  2. LOCAL LOOKUP                                            │
│     └─> Check SQLite cache (< 100ms)                        │
│         ├─> Found: Proceed to capture                       │
│         └─> Not Found: Show "Not in roster"                 │
│                                                             │
│  3. PHOTO CAPTURE                                           │
│     └─> Face detection → Quality checks → Save photo        │
│                                                             │
│  4. LOCAL SAVE                                              │
│     └─> SQLite: attendance table                            │
│         ├─> student_id (student_number)                     │
│         ├─> timestamp                                       │
│         ├─> photo_path                                      │
│         └─> qr_data                                         │
│                                                             │
│  5. CLOUD SYNC                                              │
│     └─> REST API → Supabase                                 │
│         ├─> Lookup: student_number → UUID                   │
│         ├─> Split: timestamp → date + time_in               │
│         └─> Insert: attendance table                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               NEW SUPABASE SERVER                           │
│         https://ddblgwzylvwuucnpmtzi.supabase.co           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 STUDENTS TABLE                                          │
│     ├─> id: UUID (primary key)                             │
│     ├─> student_number: VARCHAR (scanned from QR)          │
│     ├─> first_name, last_name: VARCHAR                     │
│     ├─> parent_guardian_contact: VARCHAR                   │
│     ├─> grade_level, section: VARCHAR                      │
│     └─> status: active/inactive                            │
│                                                             │
│  📝 ATTENDANCE TABLE                                        │
│     ├─> id: UUID (primary key)                             │
│     ├─> student_id: UUID (FK → students.id)                │
│     ├─> date: DATE                                         │
│     ├─> time_in: TIME                                      │
│     ├─> status: present/late/absent                        │
│     ├─> device_id: VARCHAR (device_001)                    │
│     └─> remarks: TEXT (QR data, photo URL)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    WEB PORTAL                               │
│              (Your teammate's system)                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  • View attendance records                                  │
│  • Generate reports                                         │
│  • Manage students                                          │
│  • Monitor IoT devices                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Testing & Verification

### Run Migration Script
```bash
cd /home/iot/attendance-system
chmod +x migrate_supabase.sh
./migrate_supabase.sh
```

### Test Connection
```bash
python3 utils/test_new_supabase.py
```

This will verify:
- ✅ Connection to new Supabase server
- ✅ Students table accessibility
- ✅ Attendance table structure
- ✅ UUID lookup functionality

### Test Roster Sync
```bash
python3 utils/test-scripts/test_roster_sync.py
```

Expected output:
```
📥 Downloaded N active students from new Supabase server
💾 Cached N students locally
✅ Roster sync complete
```

### Check System Status
```bash
python3 utils/check_status.py
```

Should show:
- ✅ Database initialized
- ✅ Cloud sync enabled
- ✅ Roster cache: N students
- ✅ Supabase: https://ddblgwzylvwuucnpmtzi.supabase.co

---

## 📋 What the IoT System Does

### **FOR THE IOT DEVICE:**

1. **Daily Roster Sync** (Automatic on boot)
   - Downloads all active students from Supabase
   - Caches locally for offline operation
   - Updates daily at 6:00 AM (configurable)

2. **QR Code Scanning**
   - Student scans QR code (contains student_number)
   - Fast lookup in local cache (< 100ms)
   - Validates student is in roster

3. **Photo Capture**
   - Face detection with 9 quality checks
   - Auto-capture when quality threshold met
   - Saves locally in `data/photos/`

4. **Attendance Recording**
   - Saves to local SQLite immediately
   - Queues for cloud sync
   - Prevents duplicate scans (same day)

5. **Cloud Sync**
   - Maps student_number → UUID (via Supabase lookup)
   - Splits timestamp → date + time_in
   - Uploads to new attendance table
   - Retries on failure (offline queue)

### **FOR THE WEB PORTAL:**

Your teammate's portal can now:
- Query attendance records with proper UUIDs
- Join students and attendance tables
- Generate reports by date, section, grade
- Track attendance patterns
- Export data for analysis

---

## 🔒 Data Flow Example

### When a student scans QR code:

```
1. QR Code: "2024-0001" (student_number)
   
2. Local Cache Lookup:
   SELECT * FROM students WHERE student_id = '2024-0001'
   Result: { name: "Juan Dela Cruz", parent_phone: "09171234567" }
   
3. Photo Capture:
   Face detected → Quality OK → Saved: data/photos/2024-0001_20251125_143022.jpg
   
4. Local SQLite:
   INSERT INTO attendance (student_id, timestamp, photo_path, status)
   VALUES ('2024-0001', '2025-11-25T14:30:22', 'data/photos/...', 'present')
   
5. Cloud Sync (Background):
   
   Step A: Lookup UUID
   GET /students?student_number=eq.2024-0001&select=id
   Result: { id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890" }
   
   Step B: Insert Attendance
   POST /attendance
   Body: {
     student_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
     date: "2025-11-25",
     time_in: "14:30:22",
     status: "present",
     device_id: "device_001",
     remarks: "QR: 2024-0001 | Photo: data/photos/..."
   }
   
6. SMS Notification (Optional):
   To: 09171234567
   Message: "Good day! Juan Dela Cruz checked in at 2:30 PM"
```

---

## ⚙️ Configuration

All settings in `config/config.json`:

```json
{
  "cloud": {
    "enabled": true,
    "provider": "supabase",
    "url": "${SUPABASE_URL}",
    "api_key": "${SUPABASE_KEY}",
    "device_id": "${DEVICE_ID}",
    "sync_interval": 60,
    "sync_on_capture": true,
    "roster_sync": {
      "auto_sync_on_boot": true,
      "sync_time": "06:00",
      "cache_expiry_hours": 24,
      "auto_wipe_after_class": false,
      "class_end_time": "18:00"
    }
  }
}
```

---

## 🎯 Ready to Use

The system is now configured and ready to:

1. ✅ Download student roster from new Supabase
2. ✅ Cache students locally for offline operation  
3. ✅ Scan QR codes (student_number)
4. ✅ Capture photos with face detection
5. ✅ Upload attendance with proper UUID mapping
6. ✅ Work offline with sync queue
7. ✅ Send SMS notifications

### Start the system:
```bash
./start_attendance.sh --headless
```

### Monitor logs:
```bash
tail -f data/logs/attendance_system_*.log
```

---

## 📞 Support

If you encounter issues:

1. Check connection: `python3 utils/test_new_supabase.py`
2. Verify roster: `python3 utils/check_status.py`
3. View logs: `cat data/logs/attendance_system_*.log`
4. Test manually: Scan a QR code and check Supabase dashboard

---

**Migration Status:** ✅ **COMPLETE**  
**System Status:** ✅ **READY**  
**Next Step:** Start attendance system and test with actual QR codes
