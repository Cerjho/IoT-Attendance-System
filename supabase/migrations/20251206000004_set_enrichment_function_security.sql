-- Set SECURITY DEFINER for attendance enrichment function
-- Ensures the trigger can read iot_devices regardless of caller role

-- Drop trigger temporarily to avoid dependency issues during function replace
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.triggers
        WHERE event_object_table = 'attendance'
          AND trigger_name = 'enrich_attendance_on_insert'
    ) THEN
        DROP TRIGGER enrich_attendance_on_insert ON public.attendance;
    END IF;
END $$;

-- Recreate function with SECURITY DEFINER and safe search_path
CREATE OR REPLACE FUNCTION public.enrich_attendance_data()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
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
        SELECT tl.id, tl.subject_id
        INTO matched_teaching_load
        FROM teaching_loads tl
        WHERE tl.section_id = device_section_id
          AND tl.status = 'active'
        LIMIT 1;
        
        IF matched_teaching_load.id IS NOT NULL THEN
            NEW.teaching_load_id := matched_teaching_load.id;
            NEW.subject_id := matched_teaching_load.subject_id;
        ELSE
            RAISE NOTICE 'No active teaching load found for section_id: % on date: %', 
                device_section_id, NEW.date;
        END IF;
    ELSE
        RAISE WARNING 'Device % not found in iot_devices or has no section_id', 
            NEW.device_id;
    END IF;
    
    RETURN NEW;
END;
$$;

-- Restore trigger
CREATE TRIGGER enrich_attendance_on_insert
    BEFORE INSERT ON public.attendance
    FOR EACH ROW
    EXECUTE FUNCTION public.enrich_attendance_data();

-- Verify function security
SELECT proname, prosecdef
FROM pg_proc
WHERE proname = 'enrich_attendance_data';
