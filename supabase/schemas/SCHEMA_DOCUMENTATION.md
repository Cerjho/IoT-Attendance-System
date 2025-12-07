# Supabase Database Schema Documentation

**Last Updated:** 2025-12-07  
**Project:** IoT Attendance System  
**Database:** Supabase PostgreSQL

## Schema Overview

This document describes the complete database schema deployed through migrations.

### Migration History

All migrations are in `supabase/migrations/` and have been applied to production:

1. `20241205030001_iot_devices_schema.sql` (683 bytes) - IoT device management
2. `20241205040001_add_qr_code_status.sql` (302 bytes) - QR code status field
3. `20241205141000_create_attendance_trigger.sql` (754 bytes) - Auto-timestamp trigger
4. `20241205150001_attendance_enrichment_trigger.sql` (2,291 bytes) - Section/subject enrichment
5. `20241205221100_enable_student_read_access.sql` (195 bytes) - RLS policy for students
6. `20241206230001_add_iot_devices_rls.sql` (622 bytes) - RLS policy for devices
7. `20251207000000_server_side_config.sql` (11,302 bytes) - SMS templates & notifications
8. `20251207000001_sample_data.sql` (11,133 bytes) - Test data (11 students, 4 schedules)

**Total Schema Size:** 27,282 bytes across 8 migration files

---

## Core Tables

### 1. `students`
Primary student records with contact information and schedule assignment.

**Columns:**
- `id` (UUID, PK) - Auto-generated unique identifier
- `student_number` (TEXT, UNIQUE) - Human-readable student ID (e.g., "2021001")
- `first_name` (TEXT, NOT NULL)
- `last_name` (TEXT, NOT NULL)
- `middle_name` (TEXT)
- `grade_level` (TEXT, NOT NULL) - Grade/year level
- `section_id` (UUID, FK → sections) - Assigned section
- `parent_guardian_contact` (TEXT) - Phone number for SMS
- `parent_guardian_email` (TEXT)
- `qr_code_status` (TEXT, DEFAULT 'pending') - QR generation status
- `created_at` (TIMESTAMPTZ, DEFAULT now())
- `updated_at` (TIMESTAMPTZ, DEFAULT now())

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE on `student_number`
- INDEX on `section_id` (for joins)

**RLS Policies:**
- Read access enabled for authenticated users

---

### 2. `sections`
Class sections with schedule assignments.

**Columns:**
- `id` (UUID, PK)
- `section_code` (TEXT, UNIQUE, NOT NULL) - e.g., "SEC-7A"
- `section_name` (TEXT, NOT NULL) - e.g., "Grade 7 - Section A"
- `schedule_id` (UUID, FK → school_schedules)
- `created_at` (TIMESTAMPTZ)

---

### 3. `school_schedules`
Time windows for attendance scanning with late thresholds.

**Columns:**
- `id` (UUID, PK)
- `schedule_name` (TEXT, UNIQUE, NOT NULL) - e.g., "Morning Session"
- `login_start` (TIME, NOT NULL) - Earliest login time
- `login_end` (TIME, NOT NULL) - Latest login time (late threshold)
- `logout_start` (TIME, NOT NULL) - Earliest logout time
- `logout_end` (TIME, NOT NULL) - Latest logout time
- `late_threshold_minutes` (INTEGER) - Grace period before "late"
- `early_logout_threshold_minutes` (INTEGER)
- `active` (BOOLEAN, DEFAULT true)
- `created_at` (TIMESTAMPTZ)

**Sample Schedules:**
- Morning Session: 7:00 AM - 12:00 PM
- Afternoon Session: 1:00 PM - 6:00 PM
- Full Day: 7:00 AM - 5:00 PM
- Flexible Schedule: 6:00 AM - 8:00 PM

---

### 4. `attendance`
Daily attendance records with scan timestamps and enrichment.

**Columns:**
- `id` (UUID, PK)
- `student_id` (UUID, FK → students, NOT NULL)
- `date` (DATE, NOT NULL)
- `time_in` (TIME) - Login timestamp
- `time_out` (TIME) - Logout timestamp
- `status` (TEXT) - "present", "late", "absent", etc.
- `device_id` (TEXT, FK → iot_devices) - Scanning device
- `section_id` (UUID, FK → sections) - Auto-enriched
- `subject_id` (UUID, FK → subjects) - Auto-enriched
- `teaching_load_id` (UUID) - Auto-enriched
- `photo_url` (TEXT) - Supabase Storage URL
- `remarks` (TEXT) - Additional notes (e.g., "QR: 2021001")
- `synced` (BOOLEAN, DEFAULT false) - Local sync status
- `created_at` (TIMESTAMPTZ, DEFAULT now())
- `updated_at` (TIMESTAMPTZ, DEFAULT now())

**Triggers:**
- `enrich_attendance_on_insert` - Auto-populates section/subject based on device location

**Indexes:**
- PRIMARY KEY on `id`
- INDEX on `student_id, date` (for daily lookups)
- INDEX on `device_id` (for device reports)

---

### 5. `iot_devices`
Registered IoT attendance scanners with location data.

**Columns:**
- `id` (UUID, PK)
- `device_id` (TEXT, UNIQUE, NOT NULL) - e.g., "device-001"
- `device_name` (TEXT) - Human-readable name
- `location` (TEXT) - Physical location description
- `section_id` (UUID, FK → sections) - Primary section
- `subject_id` (UUID, FK → subjects) - Primary subject
- `active` (BOOLEAN, DEFAULT true)
- `last_seen` (TIMESTAMPTZ)
- `created_at` (TIMESTAMPTZ)

**RLS Policies:**
- Read/write access for authenticated service role

---

### 6. `subjects`
Course subjects for attendance enrichment.

**Columns:**
- `id` (UUID, PK)
- `subject_code` (TEXT, UNIQUE)
- `subject_name` (TEXT, NOT NULL)
- `created_at` (TIMESTAMPTZ)

**Sample Subjects:**
- Math, Science, English, Filipino

---

### 7. `sms_templates`
Server-side SMS message templates with placeholders.

**Columns:**
- `id` (UUID, PK)
- `template_key` (TEXT, UNIQUE, NOT NULL) - e.g., "check_in", "late_arrival"
- `message_template` (TEXT, NOT NULL) - Message with {placeholders}
- `active` (BOOLEAN, DEFAULT true)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Default Templates:**
- `check_in` - Normal login message
- `check_out` - Normal logout message
- `late_arrival` - Late login warning
- `very_late_arrival` - Very late warning
- `early_logout` - Early logout notification
- `absent` - Absence notification
- `unauthorized_scan` - Outside schedule hours
- `system_error` - Error fallback

**Functions:**
- `get_sms_template(key TEXT)` - Retrieves active template by key

---

### 8. `notification_preferences`
Per-parent notification settings and quiet hours.

**Columns:**
- `id` (UUID, PK)
- `student_id` (UUID, FK → students, UNIQUE)
- `sms_enabled` (BOOLEAN, DEFAULT true)
- `email_enabled` (BOOLEAN, DEFAULT false)
- `quiet_hours_start` (TIME) - No notifications start
- `quiet_hours_end` (TIME) - No notifications end
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ)

**Functions:**
- `should_send_notification(student_id UUID)` - Checks if notification allowed (respects quiet hours)

---

## Database Functions

### `enrich_attendance_on_insert()`
**Type:** TRIGGER (BEFORE INSERT on `attendance`)  
**Purpose:** Auto-populate section/subject/teaching_load based on device location  
**Logic:**
1. Query `iot_devices` table for device's section/subject
2. Populate `section_id`, `subject_id`, `teaching_load_id` if NULL
3. Return modified NEW record

### `get_sms_template(template_key TEXT)`
**Returns:** TEXT (message template)  
**Purpose:** Retrieve active SMS template by key  
**Default:** Returns generic message if key not found

### `should_send_notification(student_id UUID)`
**Returns:** BOOLEAN  
**Purpose:** Check if notification should be sent (respects quiet hours)  
**Logic:**
1. Query `notification_preferences` for student
2. Check if SMS enabled
3. Verify current time not in quiet hours window
4. Return TRUE if allowed

---

## Row Level Security (RLS)

### Students Table
- **Policy:** `students_read_policy`
- **Operation:** SELECT
- **Rule:** `auth.role() = 'authenticated'`
- **Effect:** All authenticated users can read students

### IoT Devices Table
- **Policy:** `iot_devices_access_policy`
- **Operations:** SELECT, INSERT, UPDATE, DELETE
- **Rule:** `auth.role() = 'service_role'`
- **Effect:** Only service role can manage devices

---

## Storage Buckets

### `attendance-photos`
**Type:** Public bucket  
**Purpose:** Store student scan photos  
**Path Format:** `attendance-photos/{student_number}/{timestamp}_img.jpg`  
**Access:** Public read, authenticated write  
**Example URL:** `https://ddblgwzylvwuucnpmtzi.supabase.co/storage/v1/object/public/attendance-photos/2021001/20251207_071234_img.jpg`

---

## Sample Data (Test Environment)

**11 Test Students:**
- Student numbers: 2021001-2021007, STU001-002, 221566, 171770
- Distributed across 4 sections (SEC-7A, SEC-7B, SEC-8A, SEC-9A)
- Each with parent contact and email

**4 School Schedules:**
- Morning Session (7AM-12PM)
- Afternoon Session (1PM-6PM)
- Full Day (7AM-5PM)
- Flexible Schedule (6AM-8PM)

**4 Notification Preferences:**
- Various quiet hour configurations
- SMS enabled for all test accounts

---

## How to View Live Schema

Since Docker is not available on Raspberry Pi, use these methods:

### Method 1: Supabase Dashboard (Recommended)
```
https://supabase.com/dashboard/project/ddblgwzylvwuucnpmtzi/database/tables
```
- Click each table to see full structure
- View indexes, foreign keys, RLS policies

### Method 2: SQL Editor
```sql
-- List all tables
\dt

-- View table structure
\d+ students
\d+ attendance
\d+ school_schedules
-- etc.
```

### Method 3: Direct PostgreSQL Connection
If you have the connection string from Supabase dashboard:
```bash
pg_dump -h db.ddblgwzylvwuucnpmtzi.supabase.co \
  -U postgres \
  -d postgres \
  --schema-only \
  > schema_dump.sql
```

---

## Local SQLite Schema

The Raspberry Pi also maintains a local SQLite cache at `data/attendance.db`:

**students table:**
```sql
CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    uuid TEXT,
    name TEXT,
    email TEXT,
    parent_phone TEXT,
    section_id TEXT,
    schedule_id TEXT,
    allowed_session TEXT,
    created_at TEXT
)
```

**attendance table:**
```sql
CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    scan_type TEXT,
    status TEXT,
    photo_path TEXT,
    synced INTEGER DEFAULT 0
)
```

**sync_queue table:**
```sql
CREATE TABLE sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT,
    retry_count INTEGER DEFAULT 0
)
```

---

## Architecture Notes

- **Offline-First:** Local SQLite cache + cloud sync queue
- **Privacy:** Daily roster sync, cache wiped each evening
- **Enrichment:** Device location auto-populates section/subject in attendance
- **Notifications:** Server-side templates with quiet hours enforcement
- **Storage:** Photos uploaded to Supabase Storage, URLs saved in attendance.photo_url

---

**For Final Defense Reference:**
- Total Tables: 8 core tables
- Total Migrations: 8 files (27,282 bytes)
- Test Data: 11 students, 4 schedules, 4 sections
- RLS Policies: 2 (students read, devices service_role)
- Triggers: 1 (attendance enrichment)
- Functions: 3 (get_template, should_notify, enrich)
- Storage Buckets: 1 (attendance-photos, public)

