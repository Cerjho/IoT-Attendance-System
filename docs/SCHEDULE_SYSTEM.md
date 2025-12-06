# School Schedule System - Server-Based Configuration

## Overview

The attendance system now fetches school schedules from the **Supabase server** instead of hardcoded `config.json`. This allows centralized management of class times across all IoT devices.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SUPABASE SERVER                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  school_schedules table                               │  │
│  │  • Morning/afternoon session times                    │  │
│  │  • Login/logout windows                               │  │
│  │  • Late thresholds                                    │  │
│  │  • Cooldown settings                                  │  │
│  │  • Section-specific schedules (future)                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
                  📡 REST API (fetch schedules)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    IOT DEVICE (Raspberry Pi)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ScheduleSync                                         │  │
│  │  • Fetches from Supabase on startup                   │  │
│  │  • Caches locally in SQLite                           │  │
│  │  • Falls back to config if offline                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Local Cache (data/attendance.db)                     │  │
│  │  • school_schedules table                             │  │
│  │  • Offline operation support                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                            ↓                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  ScheduleManager                                       │  │
│  │  • Validates student scans                            │  │
│  │  • Determines on-time/late status                     │  │
│  │  • Enforces cooldown periods                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### `school_schedules` Table

```sql
CREATE TABLE school_schedules (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Morning session
    morning_start_time TIME NOT NULL DEFAULT '07:00:00',
    morning_end_time TIME NOT NULL DEFAULT '12:00:00',
    morning_login_window_start TIME NOT NULL DEFAULT '06:30:00',
    morning_login_window_end TIME NOT NULL DEFAULT '07:30:00',
    morning_logout_window_start TIME NOT NULL DEFAULT '11:30:00',
    morning_logout_window_end TIME NOT NULL DEFAULT '12:30:00',
    morning_late_threshold_minutes INTEGER NOT NULL DEFAULT 15,
    
    -- Afternoon session
    afternoon_start_time TIME NOT NULL DEFAULT '13:00:00',
    afternoon_end_time TIME NOT NULL DEFAULT '17:00:00',
    afternoon_login_window_start TIME NOT NULL DEFAULT '12:30:00',
    afternoon_login_window_end TIME NOT NULL DEFAULT '13:30:00',
    afternoon_logout_window_start TIME NOT NULL DEFAULT '16:30:00',
    afternoon_logout_window_end TIME NOT NULL DEFAULT '17:30:00',
    afternoon_late_threshold_minutes INTEGER NOT NULL DEFAULT 15,
    
    -- Settings
    auto_detect_session BOOLEAN DEFAULT TRUE,
    allow_early_arrival BOOLEAN DEFAULT TRUE,
    require_logout BOOLEAN DEFAULT TRUE,
    duplicate_scan_cooldown_minutes INTEGER DEFAULT 5,
    
    -- Status
    is_default BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Deployment

### 1. Deploy Migration to Supabase

**Option A: Using Supabase CLI (Recommended)**
```bash
# Install Supabase CLI if not installed
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Apply migration
supabase db push
```

**Option B: Manual SQL Execution**
```bash
# Run the deployment script
bash scripts/deploy_schedules.sh

# Or manually in Supabase SQL Editor:
# 1. Open Supabase Dashboard → SQL Editor
# 2. Copy contents of supabase/migrations/20251206150000_create_schedules_table.sql
# 3. Execute the SQL
```

### 2. Verify Migration

Check in Supabase Dashboard:
- Table Editor → `school_schedules` table should exist
- Should have 1 row: "Standard Schedule" (is_default=true)

### 3. Test Schedule Sync

```bash
# Test fetching schedules from server
python utils/test-scripts/test_schedule_sync.py
```

Expected output:
```
✅ Schedules synced successfully
✅ Default schedule loaded:
   Name: Standard Schedule
   📅 MORNING SESSION:
      Class Time: 07:00:00 - 12:00:00
      Login Window: 06:30:00 - 07:30:00
      ...
```

### 4. Restart Attendance System

```bash
# The system will now use server schedules
bash scripts/start_attendance.sh --headless
```

On startup, you should see:
```
✅ Using server schedule: Standard Schedule
```

## Managing Schedules

### Update Default Schedule

1. Open Supabase Dashboard → Table Editor
2. Navigate to `school_schedules` table
3. Edit the default schedule row
4. Change times as needed (e.g., morning_start_time = '08:00:00')
5. Restart IoT devices to fetch updated schedule

### Create Additional Schedules

```sql
-- Example: Create a schedule for half-day sessions
INSERT INTO school_schedules (
    name,
    description,
    morning_start_time,
    morning_end_time,
    morning_login_window_start,
    morning_login_window_end,
    morning_logout_window_start,
    morning_logout_window_end,
    morning_late_threshold_minutes,
    is_default,
    status
) VALUES (
    'Half Day Schedule',
    'For special events and half-day sessions',
    '08:00:00',  -- Start at 8 AM
    '12:00:00',  -- End at 12 PM
    '07:30:00',
    '08:30:00',
    '11:30:00',
    '12:30:00',
    15,
    FALSE,  -- Not default
    'active'
);
```

### Assign Schedule to Section (Future)

Once implemented, you'll be able to assign different schedules to different sections:

```sql
-- Assign schedule to a specific section
UPDATE sections 
SET schedule_id = '...'  -- UUID of schedule
WHERE section_code = 'Grade-10-A';
```

## Fallback Behavior

If schedule sync fails:
1. System logs warning: `"⚠️ Schedule sync failed, using config fallback"`
2. Falls back to `config/config.json` → `school_schedule` settings
3. System continues operating with config-based schedule
4. Retries sync on next startup

## Schedule Sync Process

### On System Startup:
1. `ScheduleSync` fetches active schedules from Supabase
2. Caches schedules in local SQLite (`data/attendance.db`)
3. `ScheduleManager` loads cached schedule
4. All scans validated against server schedule

### Automatic Refresh:
Currently: **On restart only**
Future: Periodic background sync (every 6 hours)

## Configuration

### Enable/Disable Schedule Sync

Schedule sync is automatically enabled if:
- `SUPABASE_URL` is set in `.env`
- `SUPABASE_KEY` is set in `.env`
- `cloud.enabled = true` in `config/config.json`

To disable and use config only:
- Set `cloud.enabled = false` in config

### Config Fallback Structure

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

## Benefits

### ✅ Centralized Management
- Update schedule once in Supabase
- All devices fetch latest schedule automatically
- No need to update each device's config file

### ✅ Flexibility
- Different schedules for different sections (future)
- Easy to adjust times for special events
- Version control through Supabase dashboard

### ✅ Reliability
- Offline operation with cached schedule
- Automatic fallback to config if server unavailable
- No disruption to attendance tracking

### ✅ Auditability
- Track schedule changes in Supabase
- `updated_at` timestamp on every change
- History of active schedules

## Troubleshooting

### Schedule Not Syncing

```bash
# Check connection
python utils/test-scripts/test_schedule_sync.py

# Verify .env variables
echo $SUPABASE_URL
echo $SUPABASE_KEY

# Check Supabase table
# Dashboard → Table Editor → school_schedules
```

### Using Wrong Schedule

```bash
# Check which schedule is loaded
# Look for startup message:
# "✅ Using server schedule: Standard Schedule"
# or
# "⚠️ Using config fallback"

# Force re-sync
rm data/attendance.db  # Clears cache
bash scripts/start_attendance.sh --headless
```

### RLS Permissions Error

```bash
# Re-run migration to fix policies
bash scripts/deploy_schedules.sh
```

## Files Modified

- **New Files:**
  - `supabase/migrations/20251206150000_create_schedules_table.sql`
  - `src/sync/schedule_sync.py`
  - `utils/test-scripts/test_schedule_sync.py`
  - `scripts/deploy_schedules.sh`
  - `docs/SCHEDULE_SYSTEM.md`

- **Modified Files:**
  - `src/attendance/schedule_manager.py` - Added server schedule support
  - `attendance_system.py` - Added schedule sync on startup

## Next Steps

1. **Deploy migration to Supabase**
2. **Test schedule sync**
3. **Customize default schedule** in Supabase dashboard
4. **Restart attendance system**
5. **Monitor logs** for successful schedule loading

## Support

For issues or questions:
- Check logs in `data/logs/attendance_system_YYYYMMDD.log`
- Run test script: `python utils/test-scripts/test_schedule_sync.py`
- Verify Supabase connection: Check Table Editor access
