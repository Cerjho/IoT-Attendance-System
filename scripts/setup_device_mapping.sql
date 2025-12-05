-- Setup IoT Device and Section Mapping
-- Run this in Supabase Dashboard → SQL Editor

-- First, create a test section if it doesn't exist
INSERT INTO sections (
    section_code,
    section_name,
    grade_level,
    status
) VALUES
    ('STEM-A-11', 'Grade 11 - STEM A', '11', 'active'),
    ('STEM-B-11', 'Grade 11 - STEM B', '11', 'active'),
    ('ABM-B-12', 'Grade 12 - ABM B', '12', 'active')
ON CONFLICT (section_code) DO NOTHING;

-- Get section IDs
DO $$
DECLARE
    stem_a_section_id UUID;
    device_exists BOOLEAN;
BEGIN
    -- Get STEM-A section ID
    SELECT id INTO stem_a_section_id
    FROM sections
    WHERE section_code = 'STEM-A-11'
    LIMIT 1;

    -- Check if device already exists
    SELECT EXISTS(SELECT 1 FROM iot_devices WHERE device_id = 'pi-lab-01') INTO device_exists;

    -- Insert or update device
    IF NOT device_exists THEN
        INSERT INTO iot_devices (
            device_id,
            device_name,
            device_type,
            location,
            section_id,
            status
        ) VALUES (
            'pi-lab-01',
            'Lab 1 Attendance Scanner',
            'QR Scanner',
            'Computer Lab 1',
            stem_a_section_id,
            'active'
        );
        RAISE NOTICE 'Device pi-lab-01 created';
    ELSE
        UPDATE iot_devices
        SET section_id = stem_a_section_id,
            status = 'active'
        WHERE device_id = 'pi-lab-01';
        RAISE NOTICE 'Device pi-lab-01 updated';
    END IF;
END $$;

-- Create a test teacher if needed
INSERT INTO teachers (
    employee_number,
    first_name,
    last_name,
    email,
    status
) VALUES
    ('T001', 'Test', 'Teacher', 'teacher@example.com', 'active')
ON CONFLICT (employee_number) DO NOTHING;

-- Create teaching loads
DO $$
DECLARE
    stem_a_section_id UUID;
    teacher_id UUID;
    math_subject_id UUID;
BEGIN
    -- Get section and teacher IDs
    SELECT id INTO stem_a_section_id FROM sections WHERE section_code = 'STEM-A-11' LIMIT 1;
    SELECT id INTO teacher_id FROM teachers WHERE employee_number = 'T001' LIMIT 1;
    
    -- Create or get Math subject
    INSERT INTO subjects (code, name, grade_level, status)
    VALUES ('MATH11', 'Mathematics 11', '11', 'active')
    ON CONFLICT (code) DO NOTHING;
    
    SELECT id INTO math_subject_id FROM subjects WHERE code = 'MATH11' LIMIT 1;
    
    -- Create teaching load
    INSERT INTO teaching_loads (
        teacher_id,
        subject_id,
        section_id,
        school_year,
        status
    ) VALUES (
        teacher_id,
        math_subject_id,
        stem_a_section_id,
        '2024-2025',
        'active'
    )
    ON CONFLICT (teacher_id, subject_id, section_id, school_year) DO NOTHING;
    
    RAISE NOTICE 'Teaching load created';
END $$;

-- Verify setup
SELECT 
    d.device_id,
    d.device_name,
    d.location,
    s.section_name,
    d.status
FROM iot_devices d
LEFT JOIN sections s ON d.section_id = s.id
WHERE d.device_id = 'pi-lab-01';
