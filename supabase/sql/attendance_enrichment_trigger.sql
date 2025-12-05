-- =====================================================
-- ATTENDANCE DATA ENRICHMENT TRIGGER
-- =====================================================
-- Purpose: Automatically populate section_id, subject_id, and teaching_load_id
--          when IoT device inserts attendance record
--
-- IoT Device Sends:
--   - student_id (UUID)
--   - date, time_in/time_out
--   - device_id (e.g., "pi-lab-01")
--   - status, photo_url, remarks
--
-- This Trigger Adds:
--   - section_id (from iot_devices table via device_id)
--   - subject_id (from teaching_loads via schedule matching)
--   - teaching_load_id (from teaching_loads via schedule matching)
-- =====================================================

-- Drop existing trigger and function if they exist
DROP TRIGGER IF EXISTS enrich_attendance_on_insert ON attendance;
DROP FUNCTION IF EXISTS enrich_attendance_data();

-- Create enrichment function
CREATE OR REPLACE FUNCTION enrich_attendance_data()
RETURNS TRIGGER AS $$
DECLARE
    device_section_id UUID;
    matched_teaching_load RECORD;
BEGIN
    -- Step 1: Get section_id from iot_devices table using device_id
    SELECT section_id INTO device_section_id
    FROM iot_devices
    WHERE device_id = NEW.device_id
      AND status = 'active'
    LIMIT 1;
    
    IF device_section_id IS NOT NULL THEN
        NEW.section_id := device_section_id;
        
        -- Step 2: Find active teaching load for this section
        -- Match based on:
        --   - section_id matches
        --   - status is 'active'
        --   - school_year matches (optional - adjust based on your needs)
        
        -- Simple version: Get first active teaching load for this section
        SELECT tl.id, tl.subject_id
        INTO matched_teaching_load
        FROM teaching_loads tl
        WHERE tl.section_id = device_section_id
          AND tl.status = 'active'
        LIMIT 1;
        
        -- Advanced version (commented out): Match based on schedule time
        -- This requires parsing the schedule field to match current time
        /*
        SELECT tl.id, tl.subject_id
        INTO matched_teaching_load
        FROM teaching_loads tl
        WHERE tl.section_id = device_section_id
          AND tl.status = 'active'
          -- Add time-based matching here based on your schedule format
          -- Example: AND tl.schedule LIKE '%' || TO_CHAR(NEW.time_in, 'HH24:MI') || '%'
        ORDER BY created_at DESC
        LIMIT 1;
        */
        
        IF matched_teaching_load.id IS NOT NULL THEN
            NEW.teaching_load_id := matched_teaching_load.id;
            NEW.subject_id := matched_teaching_load.subject_id;
        ELSE
            -- Log warning: No teaching load found
            RAISE NOTICE 'No active teaching load found for section_id: % on date: %', 
                device_section_id, NEW.date;
        END IF;
    ELSE
        -- Log warning: Device not found or has no section
        RAISE WARNING 'Device % not found in iot_devices or has no section_id', 
            NEW.device_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger that fires BEFORE INSERT
CREATE TRIGGER enrich_attendance_on_insert
    BEFORE INSERT ON attendance
    FOR EACH ROW
    EXECUTE FUNCTION enrich_attendance_data();

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Check if trigger is installed
-- SELECT trigger_name, event_manipulation, event_object_table 
-- FROM information_schema.triggers 
-- WHERE trigger_name = 'enrich_attendance_on_insert';

-- Test query: Check recent attendance records
-- SELECT 
--     a.id,
--     a.device_id,
--     a.section_id,
--     a.subject_id,
--     a.teaching_load_id,
--     s.section_name,
--     sub.subject_name,
--     t.first_name || ' ' || t.last_name as teacher_name
-- FROM attendance a
-- LEFT JOIN sections s ON a.section_id = s.id
-- LEFT JOIN subjects sub ON a.subject_id = sub.id
-- LEFT JOIN teaching_loads tl ON a.teaching_load_id = tl.id
-- LEFT JOIN teachers t ON tl.teacher_id = t.id
-- WHERE a.date = CURRENT_DATE
-- ORDER BY a.created_at DESC
-- LIMIT 20;

-- Check devices with section mappings
-- SELECT device_id, device_name, section_id, s.section_name, location
-- FROM iot_devices d
-- LEFT JOIN sections s ON d.section_id = s.id
-- WHERE status = 'active';

-- =====================================================
-- NOTES
-- =====================================================
-- 1. Ensure iot_devices table has device_id → section_id mappings
-- 2. Ensure teaching_loads table has active records for all sections
-- 3. For multiple subjects per section, implement schedule-based matching
-- 4. Consider adding a fallback teaching_load_id in iot_devices table
--    if real-time schedule matching is complex
-- 5. Monitor RAISE NOTICE/WARNING in PostgreSQL logs for unmatched records
