# Quick Start Guide: Roster Sync System

## Prerequisites

1. **Supabase Account** with project created
2. **students table** in Supabase database
3. **API credentials** (URL + API key)

---

## Step 1: Setup Supabase Database

### Create Students Table

Run this SQL in your Supabase SQL Editor:

```sql
-- Create students table
CREATE TABLE students (
  id SERIAL PRIMARY KEY,
  student_id TEXT UNIQUE NOT NULL,
  name TEXT,
  email TEXT,
  parent_phone TEXT,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for fast lookups
CREATE INDEX idx_students_student_id ON students(student_id);
CREATE INDEX idx_students_status ON students(status);

-- Optional: Add some sample data
INSERT INTO students (student_id, name, email, parent_phone, status) VALUES
  ('2021001', 'John Doe', 'john.doe@school.edu', '+1234567890', 'active'),
  ('2021002', 'Jane Smith', 'jane.smith@school.edu', '+1234567891', 'active'),
  ('2021003', 'Mike Johnson', 'mike.johnson@school.edu', '+1234567892', 'active');
```

---

## Step 2: Configure System

### Update `config/config.json`

```json
{
  "cloud": {
    "enabled": true,
    "url": "https://YOUR_PROJECT.supabase.co",
    "api_key": "YOUR_SUPABASE_API_KEY",
    "device_id": "device_001",
    "roster_sync": {
      "auto_sync_on_boot": true,
      "cache_expiry_hours": 24,
      "auto_wipe_after_class": true,
      "class_end_time": "18:00"
    }
  }
}
```

Replace:
- `YOUR_PROJECT` with your Supabase project ID
- `YOUR_SUPABASE_API_KEY` with your anon/public API key

---

## Step 3: Add Students to Supabase

### Option A: Add Individual Student

```bash
python manage_supabase_students.py --add 2021001 \
  --name "John Doe" \
  --email "john.doe@school.edu" \
  --phone "+1234567890"
```

### Option B: Import from CSV

1. Edit `students_template.csv` with your students:
   ```csv
   student_id,name,email,parent_phone
   2021001,John Doe,john.doe@school.edu,+1234567890
   2021002,Jane Smith,jane.smith@school.edu,+1234567891
   ```

2. Import:
   ```bash
   python manage_supabase_students.py --import-csv students_template.csv
   ```

### Option C: List Existing Students

```bash
python manage_supabase_students.py --list --limit 50
```

---

## Step 4: Test Roster Sync

```bash
# Run test script
python test_roster_sync.py
```

**Expected output:**
```
🧪 Roster Sync Test
======================================================================
[1] Loading configuration...
   Supabase URL: https://your-project.supabase.co
   ✓ Configuration loaded

[2] Initializing roster sync manager...
   ✓ Roster sync manager initialized

[3] Current cache status:
   Cached students: 0
   Sync needed: True

[4] Downloading today's roster from Supabase...
   📥 Downloaded 3 students from Supabase
   💾 Cached 3 students locally
   ✅ SUCCESS: Successfully synced 3 students

[5] Testing student lookup from cache...
   ✓ Found student 2021001:
     Name: John Doe
     Email: john.doe@school.edu
     Parent Phone: +1234567890

✅ Test complete!
```

---

## Step 5: Run Attendance System

```bash
# Run with display (for testing)
python attendance_system.py

# Run in headless mode (production)
bash start_attendance.sh --headless
```

**On startup, you should see:**
```
🚀 Auto-syncing roster on system startup...
📥 Downloaded 85 students from Supabase
💾 Cached 85 students locally
✅ Roster synced: 85 students cached for today
```

---

## Step 6: Test QR Scanning

1. **Generate QR codes** for your student IDs
2. **Scan a valid student ID** → Should proceed to face capture
3. **Scan an invalid student ID** → Should show "NOT IN TODAY'S ROSTER"

---

## Daily Operation

### Morning (Auto-sync)
- System boots at 6 AM
- Automatically downloads today's roster from Supabase
- Caches 30-100 students locally
- Ready for offline scanning

### During Class
- Students scan QR codes
- System checks local cache (< 100ms)
- Validates against roster
- Captures attendance photos
- Uploads to Supabase in real-time

### Evening (Auto-wipe)
- At 6 PM, system auto-wipes student cache
- Privacy compliance maintained
- Ready for next day

---

## Common Commands

### Student Management

```bash
# Add student
python manage_supabase_students.py --add STU001 --name "Test Student"

# Update student
python manage_supabase_students.py --update STU001 --phone "+9876543210"

# List students
python manage_supabase_students.py --list

# Delete student
python manage_supabase_students.py --delete STU001

# Import from CSV
python manage_supabase_students.py --import-csv students.csv
```

### Roster Sync

```bash
# Test sync
python test_roster_sync.py

# Check cache status
python -c "
from src.sync import RosterSyncManager
from src.utils import load_config
config = load_config('config/config.json')
roster = RosterSyncManager(config['cloud'])
print(roster.get_cache_info())
"

# Force manual sync
python -c "
from src.sync import RosterSyncManager
from src.utils import load_config
config = load_config('config/config.json')
roster = RosterSyncManager(config['cloud'])
result = roster.download_today_roster(force=True)
print(result)
"

# Manual wipe cache
python -c "
from src.sync import RosterSyncManager
from src.utils import load_config
config = load_config('config/config.json')
roster = RosterSyncManager(config['cloud'])
roster.wipe_roster_cache()
"
```

---

## Troubleshooting

### Issue: "Roster sync failed: Connection error"

**Fix:**
1. Check internet connection
2. Verify Supabase URL in config.json
3. Test API connection:
   ```bash
   curl -X GET "https://YOUR_PROJECT.supabase.co/rest/v1/students?limit=1" \
     -H "apikey: YOUR_API_KEY" \
     -H "Authorization: Bearer YOUR_API_KEY"
   ```

### Issue: "Student not in today's roster"

**Fix:**
1. Verify student exists in Supabase:
   ```bash
   python manage_supabase_students.py --list
   ```
2. If missing, add student:
   ```bash
   python manage_supabase_students.py --add STUDENT_ID --name "Name"
   ```
3. Force re-sync roster:
   ```bash
   python test_roster_sync.py
   ```

### Issue: "No students in cache"

**Fix:**
1. Check if Supabase table has data
2. Force sync:
   ```bash
   python -c "
   from src.sync import RosterSyncManager
   from src.utils import load_config
   roster = RosterSyncManager(load_config('config/config.json')['cloud'])
   print(roster.download_today_roster(force=True))
   "
   ```

---

## Performance Verification

After setup, verify performance:

```bash
# Check sync time
time python -c "
from src.sync import RosterSyncManager
from src.utils import load_config
roster = RosterSyncManager(load_config('config/config.json')['cloud'])
roster.download_today_roster(force=True)
"

# Check lookup speed (should be < 100ms)
python -c "
import time
from src.sync import RosterSyncManager
from src.utils import load_config

roster = RosterSyncManager(load_config('config/config.json')['cloud'])
roster.download_today_roster(force=True)

# Measure lookup time
start = time.time()
student = roster.get_cached_student('2021001')
elapsed = (time.time() - start) * 1000
print(f'Lookup time: {elapsed:.2f}ms')
print(f'Student: {student}')
"
```

---

## Next Steps

1. ✅ **Add all your students** to Supabase
2. ✅ **Test roster sync** thoroughly
3. ✅ **Configure auto-wipe** time for your schedule
4. ✅ **Generate QR codes** for student IDs
5. ✅ **Run system** in production
6. ✅ **Monitor logs** for any issues

---

## Documentation

- **Full Documentation:** `ROSTER_SYNC.md`
- **Implementation Notes:** `ROSTER_SYNC_IMPLEMENTATION.md`
- **Auto-Capture System:** `AUTO_CAPTURE.md`

---

**Need help?** Check the logs in `logs/attendance_system.log`
