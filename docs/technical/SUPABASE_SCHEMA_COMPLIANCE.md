# Supabase Attendance Schema Compliance

**Date:** December 5, 2025  
**Status:** ✅ COMPLIANT - All required fields are satisfied during scanning

## Overview

This document describes the **data collection architecture** for the IoT Attendance System. The IoT device is a **simple data collector** that sends core attendance data to Supabase. The backend (database triggers, functions, or application logic) is responsible for enriching the data with contextual fields based on device location and student schedules.

### Architecture Principle

**IoT Device Role:** Collect and transmit raw attendance data  
**Backend Role:** Enrich data with context (section, subject, teaching load)  
**Supabase:** Single source of truth for all data

## Supabase Attendance Table Schema

### Complete Field List

| Field | Type | Nullable | Default | Source | Populated? |
|-------|------|----------|---------|--------|------------|
| `id` | UUID | NO | `gen_random_uuid()` | Auto-generated | ✅ Auto |
| `student_id` | UUID | NO | - | Resolved from student_number | ✅ Required |
| `section_id` | UUID | YES | NULL | **Backend determines** | 🔄 Backend |
| `subject_id` | UUID | YES | NULL | **Backend determines** | 🔄 Backend |
| `teaching_load_id` | UUID | YES | NULL | **Backend determines** | 🔄 Backend |
| `date` | DATE | NO | `CURRENT_DATE` | Scan timestamp | ✅ Required |
| `time_in` | TIME | YES | NULL | Login scan | ✅ Required* |
| `time_out` | TIME | YES | NULL | Logout scan | ✅ Required* |
| `status` | VARCHAR(20) | NO | `'present'` | Schedule logic | ✅ Required |
| `remarks` | TEXT | YES | NULL | QR + metadata | ✅ Required |
| `recorded_by` | UUID | YES | NULL | From config | ○ Config |
| `device_id` | VARCHAR(100) | YES | NULL | From config | ✅ Required |
| `photo_url` | TEXT | YES | NULL | Storage upload | ✅ Required |
| `created_at` | TIMESTAMPTZ | NO | `NOW()` | Auto-generated | ✅ Auto |
| `updated_at` | TIMESTAMPTZ | NO | `NOW()` | Auto-generated | ✅ Auto |

**\*Note:** Either `time_in` OR `time_out` is populated based on scan type.

## Field Population Flow

### 1. IoT Device Fields (Sent by Device)

#### `student_id` (UUID)
- **Source:** Resolved from QR code student_number via REST lookup
- **Flow:**
  1. QR scan extracts `student_number` (e.g., "2021001")
  2. Cloud sync queries `GET /rest/v1/students?student_number=eq.2021001&select=id`
  3. UUID extracted from response and used as `student_id`
- **File:** `src/cloud/cloud_sync.py:_insert_to_cloud()` (lines 211-241)
- **Validation:** Student must exist in Supabase students table

#### `date` (DATE)
- **Source:** Scan timestamp parsed to ISO date
- **Flow:** `datetime.now().date().isoformat()` → `"2025-12-05"`
- **File:** `src/cloud/cloud_sync.py` (line 413)
- **Format:** `YYYY-MM-DD`

#### `time_in` / `time_out` (TIME)
- **Source:** Scan timestamp parsed to ISO time
- **Flow:**
  1. `ScheduleManager.get_expected_scan_type()` determines LOGIN/LOGOUT
  2. Timestamp parsed: `datetime.now().time().isoformat()` → `"07:12:34"`
  3. Field selected based on scan_type: `"time_in"` or `"time_out"`
- **Files:**
  - Schedule logic: `src/attendance/schedule_manager.py` (lines 189-232)
  - Time extraction: `src/cloud/cloud_sync.py` (lines 424-428)
- **Format:** `HH:MM:SS`

#### `status` (VARCHAR)
- **Source:** Schedule-based determination with late threshold
- **Flow:**
  1. `ScheduleManager.determine_attendance_status()` checks time vs thresholds
  2. Returns: `"present"` (on-time) or `"late"` (past threshold)
- **File:** `src/attendance/schedule_manager.py` (lines 234-276)
- **Values:** `present`, `late`, `absent`, `excused` (validated)

#### `device_id` (VARCHAR)
- **Source:** Configuration file
- **Flow:** `config.cloud.device_id` → `"pi-lab-01"`
- **File:** `config/config.json` (line 84)
- **Validation:** Alphanumeric + hyphens/underscores only
- **Format:** Regex `^[a-zA-Z0-9_-]+$`

#### `photo_url` (TEXT)
- **Source:** Supabase Storage upload
- **Flow:**
  1. Photo captured and saved locally: `data/photos/{student_id}/{timestamp}.jpg`
  2. Uploaded to Storage: `POST /storage/v1/object/attendance-photos/{path}`
  3. Public URL returned: `https://.../object/public/attendance-photos/...`
  4. Stored in separate `photo_url` field (not just remarks)
- **Files:**
  - Upload: `src/cloud/photo_uploader.py:upload_photo()` (lines 52-110)
  - Integration: `src/cloud/cloud_sync.py` (lines 268-270)
- **Added:** Migration `20251128000000_add_photo_url_column.sql`

#### `remarks` (TEXT)
- **Source:** QR data and metadata
- **Flow:** `f"QR: {student_number}"` → `"QR: 2021001"`
- **File:** `src/cloud/cloud_sync.py` (line 265)
- **Note:** Simplified from previous format that included photo URL

### 2. Backend-Determined Fields (Populated by Backend)

These fields are **NOT sent by the IoT device**. The backend (database triggers, functions, or application logic) determines these values based on:
- Device location (from `iot_devices` table)
- Student schedule
- Current date/time
- Active teaching loads

#### `section_id` (UUID)
- **Determined by:** Backend looks up device's section via `iot_devices.section_id` using `device_id`
- **SQL Example:**
  ```sql
  UPDATE attendance SET section_id = (
    SELECT section_id FROM iot_devices WHERE device_id = NEW.device_id
  ) WHERE id = NEW.id;
  ```

#### `subject_id` (UUID) 
- **Determined by:** Backend matches `section_id` + current time + date to find active teaching load
- **Logic:** Query `teaching_loads` table for active class at scan time

#### `teaching_load_id` (UUID) - **CRITICAL FOR DASHBOARD ROUTING**
- **Determined by:** Backend matches `section_id` + `subject_id` + schedule to specific teaching load
- **Purpose:** Routes attendance to correct teacher dashboard
- **SQL Example:**
  ```sql
  SELECT id FROM teaching_loads 
  WHERE section_id = ? AND status = 'active'
  -- Additional time-based filtering based on schedule
  ```

**Implementation Note:** These fields should be populated by:
1. **Database triggers** on attendance INSERT
2. **Supabase Edge Functions** processing attendance
3. **Backend API** enrichment layer

### 3. Config-Dependent Field (Optional)

#### `recorded_by` (UUID)
- **Source:** Configuration file (optional)
- **Flow:** `config.cloud.recorded_by_teacher_uuid` → `attendance_data["recorded_by"]`
- **File:** `src/cloud/cloud_sync.py` (lines 284-287)
- **Config:** `config/config.json:cloud.recorded_by_teacher_uuid`
- **Default:** `null` (not set)
- **Use Case:** When device has designated operator/teacher

## Data Validation

### Queue Validation (`src/utils/queue_validator.py`)

#### Schema Definition
```python
ATTENDANCE_SCHEMA = {
    "required": ["status"],
    "optional": [
        "student_number", "student_id", "date", "time_in", "time_out",
        "photo_path", "photo_url", "device_id", "qr_data", "remarks",
        "timestamp", "scan_type", "id",
        "section_id", "subject_id", "teaching_load_id", "recorded_by"
    ],
    "status_values": ["present", "late", "absent", "excused"]
}
```

#### Validation Rules

1. **Required Field:** `status` must be present
2. **Student Identifier:** Either `student_number` OR `student_id` required
3. **Date/Time:** Either `date` OR `timestamp` required
4. **Type Checking:** All fields validated against expected types
5. **Status Values:** Must be one of: `present`, `late`, `absent`, `excused`
6. **Date Format:** `YYYY-MM-DD` (10 chars, `-` at positions 4,7)
7. **Time Format:** `HH:MM:SS` (3 parts, valid ranges)
8. **UUID Format:** Valid UUID v4 format for UUID fields (except student_id in queue)
9. **Device ID Format:** Alphanumeric + hyphens/underscores only

#### UUID Validation
- **Fields Validated:** `section_id`, `subject_id`, `teaching_load_id`, `recorded_by`
- **Pattern:** `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`
- **Note:** `student_id` in queue can be student_number (not UUID), as conversion happens during cloud sync

### Circuit Breaker Protection

All Supabase REST calls are wrapped with circuit breakers to prevent cascading failures:

- **Students Endpoint:** Separate circuit breaker for student lookups
- **Attendance Endpoint:** Separate circuit breaker for attendance inserts
- **Configuration:** `config.json:cloud.circuit_breaker_*` settings
- **Files:** `src/utils/circuit_breaker.py`, `src/cloud/cloud_sync.py` (lines 96-109)

### Network Timeouts

All network calls use configured timeouts to prevent hangs:

- **Supabase REST:** Connect: 5s, Read: 10s
- **Storage Upload:** Connect: 5s, Read: 30s
- **Configuration:** `config.json:network_timeouts`
- **File:** `src/utils/network_timeouts.py`

## Configuration

### Required Settings (`config/config.json`)

```json
{
  "cloud": {
    "enabled": true,
    "url": "${SUPABASE_URL}",
    "api_key": "${SUPABASE_KEY}",
    "device_id": "${DEVICE_ID}"
  }
}
```

### Optional Settings

```json
{
  "cloud": {
    "recorded_by_teacher_uuid": null
  }
}
```

**To enable optional field:**
- Set `recorded_by_teacher_uuid` to valid UUID from `teachers` table if you want to track which teacher/operator recorded each attendance

**Important:** `teaching_load_id` is **NOT configured** - it comes from the Supabase database via roster sync

### Environment Variables (`.env`)

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_api_key_here
DEVICE_ID=pi-lab-01
```

## Example Payloads

### IoT Device Payload (Sent by Device)

This is what the IoT device actually sends to Supabase:

```json
{
  "student_id": "3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4",
  "date": "2025-12-05",
  "time_in": "07:12:34",
  "status": "present",
  "device_id": "pi-lab-01",
  "photo_url": "https://example.supabase.co/storage/v1/object/public/attendance-photos/2021001/20251205_071234.jpg",
  "remarks": "QR: 2021001"
}
```

### Complete Record After Backend Processing

After backend enrichment (triggers/functions add context fields):

```json
{
  "id": "auto-generated-uuid",
  "student_id": "3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4",
  "section_id": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
  "subject_id": "b2c3d4e5-f6g7-8h9i-0j1k-l2m3n4o5p6q7",
  "teaching_load_id": "c3d4e5f6-g7h8-9i0j-1k2l-m3n4o5p6q7r8",
  "date": "2025-12-05",
  "time_in": "07:12:34",
  "status": "present",
  "device_id": "pi-lab-01",
  "photo_url": "https://example.supabase.co/storage/v1/object/public/attendance-photos/2021001/20251205_071234.jpg",
  "remarks": "QR: 2021001",
  "recorded_by": null,
  "created_at": "2025-12-05T07:12:34.123Z",
  "updated_at": "2025-12-05T07:12:34.123Z"
}
```

**Note:** `section_id`, `subject_id`, and `teaching_load_id` are added by backend, NOT by IoT device.

### Logout Record

```json
{
  "student_id": "3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4",
  "date": "2025-12-05",
  "time_out": "16:45:12",
  "status": "present",
  "device_id": "pi-lab-01",
  "remarks": "QR: 2021001"
}
```

## Testing

### Run Schema Compliance Test

```bash
cd /home/iot/attendance-system
source venv/bin/activate
python utils/test-scripts/test_schema_compliance.py
```

### Run Unit Tests

```bash
# Queue validator tests (18 tests)
pytest tests/test_queue_validator.py -v

# Cloud sync tests (2 tests)
pytest tests/test_cloud_sync_unit.py -v

# Integration tests (1 test)
pytest tests/test_queue_sync_integration.py -v -m integration

# Extended cloud sync tests (5 tests)
pytest tests/test_cloud_sync_extended.py -v -m integration
```

### All Tests

```bash
# Run all tests (excluding hardware)
pytest tests/ -v -m "not hardware"

# Expected: 162 passed, 3 skipped
```

## Troubleshooting

### Student Not Found

**Symptom:** Record stays in queue with error "Student not found in Supabase"

**Solution:**
1. Check student exists: `curl -s "${SUPABASE_URL}/rest/v1/students?student_number=eq.2021001" -H "apikey: ${SUPABASE_KEY}"`
2. Verify student_number matches QR code format
3. Check roster sync: `python scripts/force_sync.py`

### Missing Context Fields (section_id, subject_id, teaching_load_id)

**Symptom:** These fields are NULL in attendance records

**Root Cause:** Backend enrichment is not configured

**Solution - Implement Backend Logic:**

#### Option 1: Database Trigger (Recommended) ✅ IMPLEMENTED

**Migration:** `supabase/migrations/20251205150001_attendance_enrichment_trigger.sql`

The attendance enrichment trigger is already implemented and automatically enriches all attendance records with:
- `section_id` from `iot_devices` table via `device_id`
- `subject_id` from `teaching_loads` table via section + schedule matching
- `teaching_load_id` from `teaching_loads` table via section + schedule matching

**How it works:**
1. IoT device inserts attendance with core fields (student_id, date, time_in/time_out, device_id)
2. Trigger fires BEFORE INSERT
3. Trigger looks up device's section_id from `iot_devices` table
4. Trigger finds active teaching load for that section
5. Trigger populates section_id, subject_id, teaching_load_id
6. Complete record is saved to database

**Verification:**
```sql
-- Check if trigger is installed
SELECT trigger_name, event_manipulation 
FROM information_schema.triggers 
WHERE trigger_name = 'enrich_attendance_on_insert';

-- Check recent records have context fields populated
SELECT device_id, section_id, subject_id, teaching_load_id 
FROM attendance 
WHERE date = CURRENT_DATE
LIMIT 10;
```

**Setup Requirements:**
1. Ensure `iot_devices` table has device_id → section_id mappings
2. Ensure `teaching_loads` table has active records for all sections
3. Run migration: `psql $DATABASE_URL -f supabase/migrations/20251205150001_attendance_enrichment_trigger.sql`

#### Option 2: Supabase Edge Function

Create a function that intercepts attendance inserts and enriches them before storage.

#### Option 3: Application Layer

Add a middleware/service that enriches data before sending to Supabase.

**Verification:**
```sql
-- Check if context fields are populated
SELECT device_id, section_id, subject_id, teaching_load_id 
FROM attendance 
WHERE date = CURRENT_DATE
LIMIT 10;
```

### Photo URL Not Populated

**Symptom:** `photo_url` field is null in Supabase

**Solution:**
1. Check photo capture: `ls -lh data/photos/*/`
2. Verify storage bucket exists: `attendance-photos` (public)
3. Check photo upload logs: `grep "Photo URL" data/logs/*.log`
4. Ensure migration applied: `20251128000000_add_photo_url_column.sql`

### Invalid UUID Format

**Symptom:** Queue validation error "Invalid UUID format"

**Solution:**
1. Check which field is failing (section_id/subject_id/teaching_load_id/recorded_by)
2. Verify config value is valid UUID v4 format
3. For optional fields, set to `null` in config if not needed

### Device ID Validation Failed

**Symptom:** Queue validation error "Invalid device_id format"

**Solution:**
1. Ensure device_id contains only: letters, numbers, hyphens, underscores
2. No spaces or special characters allowed
3. Update `.env`: `DEVICE_ID=pi-lab-01`

## Migration History

### Phase 1: Photo URL Column (2025-11-28)
- **Migration:** `20251128000000_add_photo_url_column.sql`
- **Added:** `photo_url TEXT` column to attendance table
- **Index:** Created on photo_url (WHERE NOT NULL)

### Phase 2: Field Compliance (2025-12-05)
- **Roster Sync:** Extended to cache `section_id`, `subject_id`
- **Cloud Sync:** Added population of all contextual fields
- **Validation:** Enhanced queue validator with UUID format checks
- **Config:** Added `teaching_load_id`, `recorded_by_teacher_uuid` options

### Phase 3: Backend Enrichment Trigger (2025-12-05)
- **Migration:** `20251205150001_attendance_enrichment_trigger.sql`
- **Added:** Automatic enrichment of `section_id`, `subject_id`, `teaching_load_id`
- **Implementation:** PostgreSQL trigger on attendance INSERT
- **Benefit:** IoT device only sends core data, backend enriches with context

## References

- **Schema Definition:** `supabase/migrations/20251125000000_master_database_reset.sql` (lines 208-225)
- **Photo URL Migration:** `supabase/migrations/20251128000000_add_photo_url_column.sql`
- **Cloud Sync:** `src/cloud/cloud_sync.py:_insert_to_cloud()`
- **Roster Sync:** `src/sync/roster_sync.py`
- **Queue Validator:** `src/utils/queue_validator.py`
- **Config Template:** `config/config.json`
- **Test Script:** `utils/test-scripts/test_schema_compliance.py`

## Summary

✅ **IoT Device Responsibilities:**

- **7 Core Fields Collected:** student_id, date, time_in/time_out, status, device_id, photo_url, remarks
- **Validated:** Queue validation ensures data integrity before sending
- **Transmitted:** Circuit breaker protection for reliable API calls
- **Tested:** 162 tests passing for data collection and transmission

🔄 **Backend Responsibilities:**

- **3 Context Fields to Populate:** section_id, subject_id, teaching_load_id
- **Source:** iot_devices table, teaching_loads table, schedule logic
- **Implementation:** Database trigger, Edge Function, or middleware
- **Critical:** Required for dashboard routing and reporting

The system follows a **clean separation of concerns**:
- IoT device = **Data collector** (simple, reliable)
- Backend = **Data enricher** (context-aware, schedule-based)
- Supabase = **Single source of truth** (authoritative)
