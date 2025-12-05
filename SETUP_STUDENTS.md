# Quick Setup Guide - Add Students to Supabase

## Problem
The system is working but failing to sync because:
1. No students exist in Supabase database
2. No device mapping configured for enrichment trigger

## Solution: Add Data via Supabase Dashboard

### Step 1: Add Test Students

1. Go to **Supabase Dashboard**: https://ddblgwzylvwuucnpmtzi.supabase.co
2. Click **SQL Editor** (left sidebar)
3. Click **New Query**
4. Copy and paste contents of: `scripts/add_test_students.sql`
5. Click **Run** (or press Ctrl+Enter)

**Expected result:** 8 students added (2021001, 2021002, 2021003, STU001, STU002, etc.)

### Step 2: Setup Device Mapping

1. In SQL Editor, click **New Query**
2. Copy and paste contents of: `scripts/setup_device_mapping.sql`
3. Click **Run**

**Expected result:** 
- Sections created
- Device `pi-lab-01` mapped to `STEM-A-11`
- Teaching load created for enrichment trigger

### Step 3: Sync Roster to Local Cache

Back on the Pi terminal:

```bash
cd /home/iot/attendance-system
source .venv/bin/activate
python -c "from src.sync.roster_sync import RosterSync; from src.utils.config_loader import load_config; rs = RosterSync(load_config('config/config.json')); print(rs.sync_roster())"
```

**Expected output:** `✅ Roster synced: 8 students cached`

### Step 4: Start System

```bash
bash scripts/start_attendance.sh --headless
```

## Verify It Works

1. **Check students in Supabase:**
   ```sql
   SELECT COUNT(*) FROM students;
   -- Should return 8
   ```

2. **Check device mapping:**
   ```sql
   SELECT device_id, section_id FROM iot_devices WHERE device_id = 'pi-lab-01';
   -- Should show a section_id (UUID)
   ```

3. **Check teaching loads:**
   ```sql
   SELECT COUNT(*) FROM teaching_loads WHERE status = 'active';
   -- Should be at least 1
   ```

4. **Test QR scan:** Scan QR code for `2021001`, `2021002`, or `2021003`

## What This Does

- **Students table**: Contains all student records that the system can scan
- **iot_devices table**: Maps your device ID (`pi-lab-01`) to a section
- **teaching_loads table**: Links teachers, subjects, and sections (needed for enrichment trigger)
- **Enrichment trigger**: Automatically adds `section_id`, `subject_id`, `teaching_load_id` to attendance records

## Troubleshooting

**"Student not found in Supabase":**
- Run Step 1 again to add students
- Verify with: `SELECT student_number FROM students;`

**"Error getting cached student: no such column":**
- Run Step 3 to sync roster (this recreates the local cache with correct schema)

**"section_id is NULL in attendance":**
- Run Step 2 to setup device mapping
- Verify device has section_id in `iot_devices` table

**RLS Policy Error when inserting:**
- You're logged in - SQL Editor runs as authenticated user with full access
- If still blocked, temporarily disable RLS: `ALTER TABLE students DISABLE ROW LEVEL SECURITY;`
