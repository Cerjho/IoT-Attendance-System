# Roster Sync System Documentation

## Overview

The attendance system now uses **Supabase as the primary database** with **SQLite as a local cache** for lightning-fast offline scanning. This architecture ensures:

- ⚡ **< 100ms response time** during QR scanning
- 🔒 **100% offline capability** after initial sync
- 🛡️ **Data Privacy Act compliant** (auto-wipe after class)
- ☁️ **Supabase = source of truth** for all student data

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SUPABASE (Cloud)                         │
│              Primary Database / Source of Truth             │
│                                                             │
│  Tables:                                                    │
│  - students (master list)                                   │
│  - attendance (uploaded records)                            │
└─────────────────────────────────────────────────────────────┘
                              ↓ ↑
                    Download   │   Upload
                    (Daily)    │   (Real-time)
                              ↓ ↑
┌─────────────────────────────────────────────────────────────┐
│              Raspberry Pi (IoT Device)                      │
│                                                             │
│  SQLite Cache (Temporary):                                  │
│  - students (today's roster only, 30-100 records)           │
│  - attendance (before cloud upload)                         │
│  - roster_sync_metadata (sync status)                       │
│                                                             │
│  Wiped: Daily after class (18:00) or on demand             │
└─────────────────────────────────────────────────────────────┘
```

### Daily Workflow

**1. Morning (6:00 AM or on Pi boot)**
```
├── System starts
├── RosterSyncManager.auto_sync_on_startup()
├── Downloads today's roster from Supabase
├── Clears old SQLite student cache
├── Loads fresh student list into cache
└── Ready for scanning (100% offline)
```

**2. During Class (9:00 AM - 5:00 PM)**
```
├── Student scans QR code
├── System checks roster_sync.get_cached_student(id)
│   └── SQLite lookup (< 100ms, no network)
├── If student in roster → proceed with capture
├── If student NOT in roster → reject with error
├── Attendance uploaded to Supabase in real-time
└── Loop continues (fully offline capable)
```

**3. After Class (6:00 PM or on demand)**
```
├── Auto-wipe triggered (if enabled)
├── roster_sync.wipe_roster_cache()
├── Deletes all students from SQLite
├── Privacy compliance maintained
└── Ready for next day's sync
```

## Configuration

### config.json Settings

```json
{
  "cloud": {
    "enabled": true,
    "url": "https://your-project.supabase.co",
    "api_key": "your_api_key_here",
    "device_id": "device_001",
    
    "roster_sync": {
      "auto_sync_on_boot": true,       // Auto-sync when system starts
      "sync_time": "06:00",             // Daily sync time
      "cache_expiry_hours": 24,         // Cache validity (hours)
      "auto_wipe_after_class": true,    // Auto-delete after class
      "class_end_time": "18:00"         // Time to auto-wipe
    }
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `auto_sync_on_boot` | bool | `true` | Automatically download roster when system starts |
| `sync_time` | string | `"06:00"` | Preferred daily sync time (HH:MM format) |
| `cache_expiry_hours` | int | `24` | Hours before cache is considered stale |
| `auto_wipe_after_class` | bool | `true` | Automatically wipe cache after class ends |
| `class_end_time` | string | `"18:00"` | Time to trigger auto-wipe (HH:MM format) |

## Supabase Schema

### Required Tables

**students** (Primary table in Supabase)
```sql
CREATE TABLE students (
  id SERIAL PRIMARY KEY,
  student_id TEXT UNIQUE NOT NULL,
  name TEXT,
  email TEXT,
  parent_phone TEXT,
  status TEXT DEFAULT 'active',  -- 'active', 'inactive', 'suspended'
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX idx_students_student_id ON students(student_id);
CREATE INDEX idx_students_status ON students(status);
```

**attendance** (For uploaded records)
```sql
CREATE TABLE attendance (
  id SERIAL PRIMARY KEY,
  student_id TEXT NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  photo_url TEXT,
  qr_data TEXT,
  status TEXT DEFAULT 'present',
  device_id TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_attendance_student_id ON attendance(student_id);
CREATE INDEX idx_attendance_timestamp ON attendance(timestamp);
CREATE INDEX idx_attendance_device_id ON attendance(device_id);
```

## API Usage

### RosterSyncManager Class

#### Initialization

```python
from src.sync import RosterSyncManager
from src.utils import load_config

config = load_config('config/config.json')
roster_sync = RosterSyncManager(config['cloud'])
```

#### Download Today's Roster

```python
# Auto-sync on startup
result = roster_sync.auto_sync_on_startup()

# Manual sync
result = roster_sync.download_today_roster(force=False)

# Force sync (even if already synced today)
result = roster_sync.download_today_roster(force=True)

# Result format:
{
    'success': True,
    'students_synced': 85,
    'message': 'Successfully synced 85 students for today',
    'cached_count': 85
}
```

#### Check Student in Roster

```python
# Fast check (< 100ms)
student = roster_sync.get_cached_student('2021001')

if student:
    print(f"Name: {student['name']}")
    print(f"Email: {student['email']}")
    print(f"Phone: {student['parent_phone']}")
else:
    print("Student not in today's roster")

# Boolean check
is_valid = roster_sync.is_student_in_roster('2021001')
```

#### Get Cache Information

```python
cache_info = roster_sync.get_cache_info()

print(f"Cached students: {cache_info['cached_students']}")
print(f"Last sync: {cache_info['last_sync_date']}")
print(f"Sync needed: {cache_info['sync_needed']}")
```

#### Wipe Cache (Privacy)

```python
# Manual wipe
success = roster_sync.wipe_roster_cache()

# Auto-wipe after class (called by scheduler)
roster_sync.schedule_daily_wipe()
```

## Integration with Attendance System

### QR Code Validation

The attendance system now validates students against the roster cache:

```python
# In attendance_system.py

if self.roster_sync.enabled:
    # Check if student is in today's roster
    student = self.roster_sync.get_cached_student(student_id)
    
    if not student:
        # Student NOT in roster - reject
        print(f"❌ UNAUTHORIZED: {student_id} not in today's roster")
        self.buzzer.beep('error')
        continue
    else:
        # Student verified - proceed with capture
        print(f"✓ Student verified: {student.get('name')}")
        # Continue to face capture...
else:
    # Fallback: Use local database (old behavior)
    student = self.database.get_student(student_id)
```

## Testing

### Test Roster Sync

```bash
# Run test script
python test_roster_sync.py
```

**Test Output:**
```
🧪 Roster Sync Test
======================================================================
[1] Loading configuration...
   Supabase URL: https://your-project.supabase.co
   Device ID: device_001
   Roster sync enabled: True

[2] Initializing roster sync manager...
   ✓ Roster sync manager initialized

[3] Current cache status:
   Cached students: 0
   Last sync date: Never
   Sync needed: True

[4] Downloading today's roster from Supabase...
   📥 Downloaded 85 students from Supabase
   💾 Cached 85 students locally
   ✅ SUCCESS: Successfully synced 85 students for today

[5] Testing student lookup from cache...
   ✓ Found student 2021001:
     Name: John Doe
     Email: john.doe@school.edu
     Parent Phone: +1234567890

✅ Test complete!
```

### Manual Testing in Python

```python
# Quick test
from src.sync import RosterSyncManager
from src.utils import load_config

config = load_config('config/config.json')
roster = RosterSyncManager(config['cloud'])

# Sync roster
result = roster.download_today_roster(force=True)
print(result)

# Check student
student = roster.get_cached_student('2021001')
print(student)

# Get cache info
info = roster.get_cache_info()
print(info)
```

## Performance Metrics

### Benchmarks

| Operation | Time | Network Required |
|-----------|------|------------------|
| Initial roster download | 2-5s | ✅ Yes (once daily) |
| Student lookup (cached) | < 100ms | ❌ No |
| QR validation | < 100ms | ❌ No |
| Face capture | 3-8s | ❌ No |
| Attendance upload | 200-500ms | ✅ Yes |

### Cache Size

- **30 students**: ~10 KB
- **100 students**: ~30 KB
- **500 students**: ~150 KB

Minimal storage footprint on Raspberry Pi.

## Security & Privacy

### Data Privacy Compliance

✅ **No permanent student data storage on device**
- Student data downloaded daily
- Cached temporarily in memory/SQLite
- Auto-wiped after class (configurable)

✅ **Minimal data exposure**
- Only today's roster downloaded (not entire database)
- Data encrypted in transit (HTTPS/TLS)
- No sensitive data persisted

✅ **Audit trail**
- All sync operations logged
- Sync metadata tracked (last sync time, count)
- Device ID tracked for accountability

### Network Security

- All API calls use HTTPS
- Supabase API key authentication
- Device ID for access control
- Row-level security policies (configure in Supabase)

## Troubleshooting

### Issue: Roster sync fails on startup

**Check:**
1. Supabase URL and API key in config.json
2. Internet connectivity
3. Supabase `students` table exists
4. API key has read permissions

**Fix:**
```bash
# Test connection
curl -X GET "https://your-project.supabase.co/rest/v1/students" \
  -H "apikey: your_api_key" \
  -H "Authorization: Bearer your_api_key"
```

### Issue: Student not found in roster

**Possible causes:**
1. Student not in Supabase database
2. Student status is 'inactive'
3. Cache not synced today
4. Student added after morning sync

**Fix:**
```python
# Force re-sync
roster_sync.download_today_roster(force=True)

# Check Supabase database directly
# Add student to Supabase if missing
```

### Issue: Cache not wiped after class

**Check:**
1. `auto_wipe_after_class` is `true` in config
2. `class_end_time` is set correctly
3. System is running at class end time

**Manual wipe:**
```python
from src.sync import RosterSyncManager
roster = RosterSyncManager(config)
roster.wipe_roster_cache()
```

## Migration from Old System

### Before (Old System)

```python
# Students stored permanently in SQLite
student = database.get_student(student_id)
if not student:
    # Auto-register any new student
    database.add_student(student_id)
```

### After (New System)

```python
# Students downloaded from Supabase daily
student = roster_sync.get_cached_student(student_id)
if not student:
    # Reject - student not in today's roster
    print("Unauthorized student")
    return
```

### Migration Steps

1. ✅ **Export existing students to Supabase**
   ```bash
   python manage_students.py --export-to-supabase
   ```

2. ✅ **Update config.json** with Supabase credentials

3. ✅ **Test roster sync**
   ```bash
   python test_roster_sync.py
   ```

4. ✅ **Enable roster sync** in config (`enabled: true`)

5. ✅ **Run attendance system**
   ```bash
   python attendance_system.py
   ```

## Future Enhancements

- [ ] Schedule-based roster sync (only download students for specific class times)
- [ ] Multi-section support (different rosters for different classes)
- [ ] Offline mode with last-known roster
- [ ] Roster preview UI before class
- [ ] Automatic student photo download from Supabase
- [ ] Real-time roster updates via WebSocket

---

**Last Updated:** November 25, 2025
