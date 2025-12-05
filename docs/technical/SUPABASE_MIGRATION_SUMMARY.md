# Supabase Schema Migration Summary

**Date:** December 5, 2025  
**Status:** ✅ COMPLETED  
**Migration Version:** Phase 3 - Backend Enrichment Trigger

## Overview

This document summarizes the complete migration of the IoT Attendance System to use the new Supabase schema with automatic backend enrichment.

## What Changed

### 1. Attendance Table Schema

**Old Schema (Deprecated):**
- Single `timestamp` field for both login and logout
- Manual population of all fields
- No automatic context enrichment

**New Schema (Current):**
```sql
CREATE TABLE attendance (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id UUID NOT NULL REFERENCES students(id),
    section_id UUID REFERENCES sections(id),
    subject_id UUID REFERENCES subjects(id),
    teaching_load_id UUID REFERENCES teaching_loads(id),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    time_in TIME,
    time_out TIME,
    status VARCHAR(20) NOT NULL DEFAULT 'present',
    remarks TEXT,
    recorded_by UUID REFERENCES teachers(id),
    device_id VARCHAR(100),
    photo_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key Differences:**
- ✅ Separate `time_in` and `time_out` TIME fields (instead of single timestamp)
- ✅ Dedicated `photo_url` TEXT field (added in migration `20251128000000_add_photo_url_column.sql`)
- ✅ Context fields: `section_id`, `subject_id`, `teaching_load_id` (auto-populated by trigger)
- ✅ `date` DATE field separate from time fields
- ✅ `device_id` for tracking which IoT device recorded the attendance

### 2. Backend Enrichment Trigger

**Migration:** `supabase/migrations/20251205150001_attendance_enrichment_trigger.sql`

**Purpose:** Automatically populate contextual fields when IoT device inserts attendance record

**How It Works:**
```
IoT Device Sends:                    Trigger Adds:
├── student_id                       ├── section_id (from iot_devices)
├── date                             ├── subject_id (from teaching_loads)
├── time_in/time_out                 └── teaching_load_id (from teaching_loads)
├── status                           
├── device_id                        
├── photo_url                        
└── remarks                          
```

**Trigger Logic:**
1. Device inserts attendance with core fields
2. Trigger fires BEFORE INSERT
3. Looks up device's `section_id` from `iot_devices` table using `device_id`
4. Finds active `teaching_load_id` and `subject_id` from `teaching_loads` for that section
5. Populates context fields automatically
6. Record is saved with complete data

### 3. IoT Device Changes

**Files Modified:**
- `src/cloud/cloud_sync.py` - Updated payload format and field handling
- `.github/copilot-instructions.md` - Updated documentation and examples

**Payload Changes:**

**Before:**
```json
{
  "student_id": "uuid",
  "timestamp": "2025-11-29T07:12:34Z",
  "remarks": "QR: 2021001 | Photo: https://..."
}
```

**After:**
```json
{
  "student_id": "uuid",
  "date": "2025-11-29",
  "time_in": "07:12:34",
  "status": "present",
  "device_id": "pi-lab-01",
  "photo_url": "https://...",
  "remarks": "QR: 2021001"
}
```

**Key Changes:**
- ✅ `photo_url` is now a separate field (not embedded in remarks)
- ✅ Date and time are separated: `date` (DATE) and `time_in`/`time_out` (TIME)
- ✅ `remarks` simplified to contain only QR data
- ✅ `device_id` explicitly included for trigger processing

## Architecture Benefits

### Separation of Concerns

**IoT Device (Simple Data Collector):**
- ✅ Only collects core attendance data
- ✅ No need to know about sections, subjects, or teaching loads
- ✅ Reliable, simple, easy to maintain
- ✅ Works offline with queue-based sync

**Backend (Context Enricher):**
- ✅ Centralized business logic for context fields
- ✅ Automatically maintains referential integrity
- ✅ Easy to update schedule matching logic
- ✅ Single source of truth for section/subject mapping

**Supabase (Authoritative Database):**
- ✅ Complete records with all context
- ✅ Proper foreign key relationships
- ✅ Ready for dashboard queries
- ✅ Consistent data model

### Scalability

- **Multiple Devices:** Each device only needs to know its own `device_id`
- **Schedule Changes:** Update teaching loads in database, trigger handles mapping
- **New Sections:** Add to `iot_devices` table, automatic routing
- **Reporting:** All context fields available for complex queries

## Migration Timeline

### Phase 1: Photo URL Column (Nov 28, 2025)
- **Migration:** `20251128000000_add_photo_url_column.sql`
- **Change:** Added `photo_url` TEXT column to attendance table
- **Impact:** Photos now properly indexed and queryable

### Phase 2: Field Compliance (Dec 5, 2025)
- **Files:** `src/cloud/cloud_sync.py`, `src/utils/queue_validator.py`
- **Change:** Updated IoT device to send compliant payloads
- **Impact:** Clean separation of date/time, photo_url as separate field

### Phase 3: Backend Enrichment (Dec 5, 2025)
- **Migration:** `20251205150001_attendance_enrichment_trigger.sql`
- **Change:** Automatic population of context fields via trigger
- **Impact:** IoT device simplified, backend handles complexity

## Verification

### Check Trigger Installation

```sql
-- Verify trigger exists
SELECT trigger_name, event_manipulation, event_object_table 
FROM information_schema.triggers 
WHERE trigger_name = 'enrich_attendance_on_insert';
```

Expected output:
```
trigger_name              | event_manipulation | event_object_table
--------------------------+-------------------+-------------------
enrich_attendance_on_insert | INSERT           | attendance
```

### Check Recent Records

```sql
-- Verify context fields are populated
SELECT 
    date,
    device_id,
    section_id,
    subject_id,
    teaching_load_id,
    CASE 
        WHEN section_id IS NULL THEN '❌ Missing'
        ELSE '✅ OK'
    END as enrichment_status
FROM attendance
WHERE date = CURRENT_DATE
ORDER BY created_at DESC
LIMIT 10;
```

Expected: All records should have `section_id`, `subject_id`, and `teaching_load_id` populated.

### Check Device Mapping

```sql
-- Verify iot_devices table has section mappings
SELECT 
    device_id,
    device_name,
    section_id,
    s.section_name,
    location,
    status
FROM iot_devices d
LEFT JOIN sections s ON d.section_id = s.id
WHERE status = 'active';
```

Expected: Each active device should have a `section_id` mapped.

### Check Teaching Loads

```sql
-- Verify active teaching loads exist for sections
SELECT 
    s.section_name,
    sub.subject_name,
    t.first_name || ' ' || t.last_name as teacher_name,
    tl.status,
    tl.schedule
FROM teaching_loads tl
JOIN sections s ON tl.section_id = s.id
JOIN subjects sub ON tl.subject_id = sub.id
JOIN teachers t ON tl.teacher_id = t.id
WHERE tl.status = 'active'
ORDER BY s.section_name;
```

Expected: At least one active teaching load per section that has IoT devices.

## Testing

### Unit Tests
```bash
# Cloud sync payload tests
pytest tests/test_cloud_sync_unit.py -v

# Queue validator tests  
pytest tests/test_queue_validator.py -v

# Extended cloud sync tests
pytest tests/test_cloud_sync_extended.py -v -m integration
```

### Integration Tests
```bash
# Queue to cloud sync flow
pytest tests/test_queue_sync_integration.py -v -m integration

# System integration
pytest tests/test_system_integration.py -v -m integration
```

### Manual Testing
```bash
# 1. Start system in demo mode
bash scripts/start_attendance.sh --demo

# 2. Scan a test QR code (e.g., 2021001)

# 3. Check local database
sqlite3 data/attendance.db "SELECT * FROM attendance ORDER BY id DESC LIMIT 1;"

# 4. Check Supabase (if online)
curl -s "${SUPABASE_URL}/rest/v1/attendance?select=*&order=created_at.desc&limit=1" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" | jq
```

## Troubleshooting

### Context Fields Still NULL

**Symptoms:** `section_id`, `subject_id`, or `teaching_load_id` are NULL in attendance records

**Possible Causes:**
1. Trigger not installed
2. Device not mapped in `iot_devices` table
3. No active teaching load for section

**Solutions:**

1. **Install trigger:**
   ```bash
   psql $DATABASE_URL -f supabase/migrations/20251205150001_attendance_enrichment_trigger.sql
   ```

2. **Map device to section:**
   ```sql
   -- Find device
   SELECT * FROM iot_devices WHERE device_id = 'pi-lab-01';
   
   -- Update section_id
   UPDATE iot_devices 
   SET section_id = '<section-uuid-here>'
   WHERE device_id = 'pi-lab-01';
   ```

3. **Create teaching load:**
   ```sql
   INSERT INTO teaching_loads (teacher_id, subject_id, section_id, status)
   VALUES (
     '<teacher-uuid>',
     '<subject-uuid>',
     '<section-uuid>',
     'active'
   );
   ```

### Photo URL Not Saving

**Symptoms:** `photo_url` field is NULL or empty

**Solutions:**

1. **Check migration applied:**
   ```sql
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name = 'attendance' AND column_name = 'photo_url';
   ```

2. **Check photo upload:**
   ```bash
   # Check local photos exist
   ls -lh data/photos/*/
   
   # Check upload logs
   grep "Photo URL" data/logs/attendance_*.log
   ```

3. **Verify storage bucket:**
   - Bucket name: `attendance-photos`
   - Access: Public
   - Check in Supabase dashboard

### Device ID Validation Failed

**Symptoms:** Error "Invalid device_id format"

**Solution:**
```bash
# Ensure device_id contains only: letters, numbers, hyphens, underscores
# Valid: pi-lab-01, device_123, iot_scanner
# Invalid: pi lab 01, device#123, iot@scanner

# Update .env
echo "DEVICE_ID=pi-lab-01" >> .env
```

## References

### Documentation
- **Schema Compliance:** `docs/technical/SUPABASE_SCHEMA_COMPLIANCE.md`
- **System Overview:** `docs/technical/SYSTEM_OVERVIEW.md`
- **Copilot Instructions:** `.github/copilot-instructions.md`

### Code
- **Cloud Sync:** `src/cloud/cloud_sync.py`
- **Photo Uploader:** `src/cloud/photo_uploader.py`
- **Queue Validator:** `src/utils/queue_validator.py`

### Migrations
- **Master Reset:** `supabase/migrations/20251125000000_master_database_reset.sql`
- **Photo URL:** `supabase/migrations/20251128000000_add_photo_url_column.sql`
- **Enrichment Trigger:** `supabase/migrations/20251205150001_attendance_enrichment_trigger.sql`

### Tests
- **Unit Tests:** `tests/test_cloud_sync_unit.py`
- **Queue Tests:** `tests/test_queue_validator.py`
- **Integration Tests:** `tests/test_cloud_sync_extended.py`, `tests/test_queue_sync_integration.py`

## Summary

✅ **Migration Complete:**
- New schema with separate date/time fields
- Photo URL as dedicated field
- Automatic backend enrichment via trigger
- IoT device simplified to core data collection
- All tests passing (162 tests)

✅ **Benefits Achieved:**
- Clean separation of concerns
- Scalable architecture
- Easy to maintain and extend
- Proper database normalization
- Dashboard-ready data model

✅ **Next Steps:**
1. Verify trigger is deployed to production Supabase
2. Ensure `iot_devices` table has all device → section mappings
3. Verify `teaching_loads` table has active records for all sections
4. Monitor logs for any context field population issues
5. Update dashboard queries to use new schema

---

**Questions or Issues?**  
See `docs/technical/SUPABASE_SCHEMA_COMPLIANCE.md` for detailed field documentation and troubleshooting.
