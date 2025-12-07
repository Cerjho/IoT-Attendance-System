-- Sample Data for Testing IoT Attendance System
-- This creates complete test data for all tables

-- =====================================================
-- Sample School Schedules
-- =====================================================

-- Insert schedules only if they don't exist
INSERT INTO school_schedules (
    name, description,
    morning_start_time, morning_end_time,
    morning_login_window_start, morning_login_window_end,
    morning_logout_window_start, morning_logout_window_end,
    morning_late_threshold_minutes,
    afternoon_start_time, afternoon_end_time,
    afternoon_login_window_start, afternoon_login_window_end,
    afternoon_logout_window_start, afternoon_logout_window_end,
    afternoon_late_threshold_minutes,
    is_default, status
)
SELECT 
    'Morning Session', 'Morning class schedule (7 AM - 12 PM)',
    '07:00:00', '12:00:00',
    '06:30:00', '07:30:00',
    '11:30:00', '12:30:00',
    15,
    '13:00:00', '13:00:00',  -- Same time for afternoon (not used)
    '13:00:00', '13:00:00',
    '13:00:00', '13:00:00',
    15,
    false, 'active'
WHERE NOT EXISTS (SELECT 1 FROM school_schedules WHERE name = 'Morning Session');

INSERT INTO school_schedules (
    name, description,
    morning_start_time, morning_end_time,
    morning_login_window_start, morning_login_window_end,
    morning_logout_window_start, morning_logout_window_end,
    morning_late_threshold_minutes,
    afternoon_start_time, afternoon_end_time,
    afternoon_login_window_start, afternoon_login_window_end,
    afternoon_logout_window_start, afternoon_logout_window_end,
    afternoon_late_threshold_minutes,
    is_default, status
)
SELECT 
    'Afternoon Session', 'Afternoon class schedule (1 PM - 6 PM)',
    '13:00:00', '13:00:00',  -- Same time for morning (not used)
    '13:00:00', '13:00:00',
    '13:00:00', '13:00:00',
    15,
    '13:00:00', '18:00:00',
    '12:30:00', '13:30:00',
    '17:30:00', '18:30:00',
    15,
    false, 'active'
WHERE NOT EXISTS (SELECT 1 FROM school_schedules WHERE name = 'Afternoon Session');

INSERT INTO school_schedules (
    name, description,
    morning_start_time, morning_end_time,
    morning_login_window_start, morning_login_window_end,
    morning_logout_window_start, morning_logout_window_end,
    morning_late_threshold_minutes,
    afternoon_start_time, afternoon_end_time,
    afternoon_login_window_start, afternoon_login_window_end,
    afternoon_logout_window_start, afternoon_logout_window_end,
    afternoon_late_threshold_minutes,
    is_default, status
)
SELECT 
    'Full Day (Both Sessions)', 'Full day schedule with morning and afternoon',
    '07:00:00', '12:00:00',
    '06:30:00', '07:30:00',
    '11:30:00', '12:30:00',
    15,
    '13:00:00', '18:00:00',
    '12:30:00', '13:30:00',
    '17:30:00', '18:30:00',
    15,
    false, 'active'
WHERE NOT EXISTS (SELECT 1 FROM school_schedules WHERE name = 'Full Day (Both Sessions)');

INSERT INTO school_schedules (
    name, description,
    morning_start_time, morning_end_time,
    morning_login_window_start, morning_login_window_end,
    morning_logout_window_start, morning_logout_window_end,
    morning_late_threshold_minutes,
    afternoon_start_time, afternoon_end_time,
    afternoon_login_window_start, afternoon_login_window_end,
    afternoon_logout_window_start, afternoon_logout_window_end,
    afternoon_late_threshold_minutes,
    is_default, status
)
SELECT 
    'Flexible Schedule', 'Flexible schedule (6 AM - 8 PM)',
    '06:00:00', '20:00:00',
    '05:30:00', '06:30:00',
    '19:30:00', '20:30:00',
    15,
    '06:00:00', '20:00:00',  -- Same as morning for flexibility
    '05:30:00', '06:30:00',
    '19:30:00', '20:30:00',
    15,
    false, 'active'
WHERE NOT EXISTS (SELECT 1 FROM school_schedules WHERE name = 'Flexible Schedule');

-- =====================================================
-- Sample Students
-- =====================================================

-- Note: Using UUID v4 format for student IDs
-- Delete existing test students first to avoid conflicts
DELETE FROM students WHERE student_number IN ('2021001', '2021002', '2021003', '2021004', '2021005', '2021006', '2021007', 'STU001', 'STU002', '221566', '171770');

INSERT INTO students (id, student_number, first_name, last_name, middle_name, grade_level, section_id, parent_guardian_contact, parent_guardian_email, status) VALUES
-- Morning students
('11111111-1111-1111-1111-111111111111', '2021001', 'Juan', 'Dela Cruz', 'Santos', '11', NULL, '+639171234567', 'parent1@example.com', 'active'),
('22222222-2222-2222-2222-222222222222', '2021002', 'Maria', 'Santos', 'Garcia', '11', NULL, '+639171234568', 'parent2@example.com', 'active'),
('33333333-3333-3333-3333-333333333333', '2021003', 'Pedro', 'Reyes', 'Cruz', '11', NULL, '+639171234569', 'parent3@example.com', 'active'),

-- Afternoon students
('44444444-4444-4444-4444-444444444444', '2021004', 'Ana', 'Lopez', 'Mendoza', '12', NULL, '+639171234570', 'parent4@example.com', 'active'),
('55555555-5555-5555-5555-555555555555', '2021005', 'Carlos', 'Ramos', 'Torres', '12', NULL, '+639171234571', 'parent5@example.com', 'active'),

-- Both sessions students
('66666666-6666-6666-6666-666666666666', '2021006', 'Lisa', 'Fernandez', 'Aquino', '11', NULL, '+639171234572', 'parent6@example.com', 'active'),
('77777777-7777-7777-7777-777777777777', '2021007', 'Mark', 'Gonzales', 'Rivera', '12', NULL, '+639171234573', 'parent7@example.com', 'active'),

-- Test students (existing ones with proper UUIDs)
('88888888-8888-8888-8888-888888888888', 'STU001', 'Test Student', 'One', 'A', '11', NULL, '+639171234574', 'test1@example.com', 'active'),
('99999999-9999-9999-9999-999999999999', 'STU002', 'Test Student', 'Two', 'B', '11', NULL, '+639171234575', 'test2@example.com', 'active'),
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '221566', 'Sample', 'Student', 'C', '12', NULL, '+639171234576', 'test3@example.com', 'active'),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '171770', 'Demo', 'Student', 'D', '12', NULL, '+639171234577', 'test4@example.com', 'active');

-- =====================================================
-- Sample Sections
-- =====================================================

-- Insert sections only if they don't exist (with schedule_id)
DELETE FROM sections WHERE section_code IN ('SEC-7A', 'SEC-7B', 'SEC-8A', 'SEC-9A');

INSERT INTO sections (section_code, section_name, grade_level, schedule_id, status) VALUES
('SEC-7A', 'Grade 7 - Section A (Morning)', '7', (SELECT id FROM school_schedules WHERE name = 'Morning Session'), 'active'),
('SEC-7B', 'Grade 7 - Section B (Afternoon)', '7', (SELECT id FROM school_schedules WHERE name = 'Afternoon Session'), 'active'),
('SEC-8A', 'Grade 8 - Section A (Full Day)', '8', (SELECT id FROM school_schedules WHERE name = 'Full Day (Both Sessions)'), 'active'),
('SEC-9A', 'Grade 9 - Section A (Flexible)', '9', (SELECT id FROM school_schedules WHERE name = 'Flexible Schedule'), 'active');

-- Update students with sections (using section_code to find the generated IDs)
UPDATE students SET section_id = (SELECT id FROM sections WHERE section_code = 'SEC-7A') WHERE student_number IN ('2021001', '2021002', '2021003');
UPDATE students SET section_id = (SELECT id FROM sections WHERE section_code = 'SEC-7B') WHERE student_number IN ('2021004', '2021005');
UPDATE students SET section_id = (SELECT id FROM sections WHERE section_code = 'SEC-8A') WHERE student_number IN ('2021006', '2021007');
UPDATE students SET section_id = (SELECT id FROM sections WHERE section_code = 'SEC-9A') WHERE student_number IN ('STU001', 'STU002', '221566', '171770');

-- =====================================================
-- Sample Subjects
-- =====================================================

-- Insert subjects only if they don't exist
INSERT INTO subjects (name, code, description, status)
SELECT 'Mathematics', 'MATH-7', 'Grade 7 Mathematics', 'active'
WHERE NOT EXISTS (SELECT 1 FROM subjects WHERE code = 'MATH-7');

INSERT INTO subjects (name, code, description, status)
SELECT 'Science', 'SCI-7', 'Grade 7 Science', 'active'
WHERE NOT EXISTS (SELECT 1 FROM subjects WHERE code = 'SCI-7');

INSERT INTO subjects (name, code, description, status)
SELECT 'English', 'ENG-7', 'Grade 7 English', 'active'
WHERE NOT EXISTS (SELECT 1 FROM subjects WHERE code = 'ENG-7');

INSERT INTO subjects (name, code, description, status)
SELECT 'Filipino', 'FIL-7', 'Grade 7 Filipino', 'active'
WHERE NOT EXISTS (SELECT 1 FROM subjects WHERE code = 'FIL-7');

-- =====================================================
-- IoT Devices (Using Existing Devices)
-- =====================================================

-- Update existing devices with test sections
-- Note: Your current device is 'device-001' (appears twice in database)
-- We'll keep the existing devices and just link them to test sections

UPDATE iot_devices 
SET section_id = (SELECT id FROM sections WHERE section_code = 'SEC-8A')
WHERE device_id = 'device-001' 
AND id = '8016ecae-fbd7-47d8-8292-5bc532bc7a23';

UPDATE iot_devices 
SET section_id = (SELECT id FROM sections WHERE section_code = 'SEC-9A')
WHERE device_id = 'device-001' 
AND id = 'cbb8165b-77fe-4253-8e24-b1ddbdb1eec8';

-- =====================================================
-- Sample Attendance Records (Past 7 days)
-- =====================================================

-- Today's attendance (morning students)
INSERT INTO attendance (student_id, date, time_in, time_out, status, device_id, remarks) VALUES
('11111111-1111-1111-1111-111111111111', CURRENT_DATE, '07:15:00', '12:05:00', 'present', 'device-001', 'Auto-captured'),
('22222222-2222-2222-2222-222222222222', CURRENT_DATE, '07:45:00', NULL, 'late', 'device-001', 'Late arrival - 45 mins'),
('33333333-3333-3333-3333-333333333333', CURRENT_DATE, '07:10:00', '12:00:00', 'present', 'device-001', 'Auto-captured');

-- Today's attendance (afternoon students)
INSERT INTO attendance (student_id, date, time_in, time_out, status, device_id, remarks) VALUES
('44444444-4444-4444-4444-444444444444', CURRENT_DATE, '13:05:00', NULL, 'present', 'device-001', 'Auto-captured'),
('55555555-5555-5555-5555-555555555555', CURRENT_DATE, '13:30:00', NULL, 'late', 'device-001', 'Late arrival - 30 mins');

-- Yesterday's attendance
INSERT INTO attendance (student_id, date, time_in, time_out, status, device_id, remarks) VALUES
('11111111-1111-1111-1111-111111111111', CURRENT_DATE - INTERVAL '1 day', '07:05:00', '12:00:00', 'present', 'device-001', 'Auto-captured'),
('22222222-2222-2222-2222-222222222222', CURRENT_DATE - INTERVAL '1 day', '07:10:00', '12:05:00', 'present', 'device-001', 'Auto-captured'),
('44444444-4444-4444-4444-444444444444', CURRENT_DATE - INTERVAL '1 day', '13:00:00', '18:00:00', 'present', 'device-001', 'Auto-captured'),
('55555555-5555-5555-5555-555555555555', CURRENT_DATE - INTERVAL '1 day', '13:10:00', '18:05:00', 'present', 'device-001', 'Auto-captured');

-- Last week's attendance (sample data)
INSERT INTO attendance (student_id, date, time_in, time_out, status, device_id, remarks) VALUES
('11111111-1111-1111-1111-111111111111', CURRENT_DATE - INTERVAL '2 days', '07:20:00', '12:00:00', 'present', 'device-001', 'Auto-captured'),
('22222222-2222-2222-2222-222222222222', CURRENT_DATE - INTERVAL '2 days', '07:50:00', '12:10:00', 'late', 'device-001', 'Late arrival'),
('66666666-6666-6666-6666-666666666666', CURRENT_DATE - INTERVAL '2 days', '07:05:00', '12:00:00', 'present', 'device-001', 'Auto-captured'),
('77777777-7777-7777-7777-777777777777', CURRENT_DATE - INTERVAL '2 days', '13:05:00', '18:00:00', 'present', 'device-001', 'Auto-captured');

-- =====================================================
-- Sample Notification Preferences
-- =====================================================

INSERT INTO notification_preferences (
    parent_phone, 
    student_id, 
    check_in_enabled, 
    check_out_enabled, 
    late_arrival_enabled,
    no_checkout_enabled,
    absence_alert_enabled,
    schedule_violation_enabled,
    quiet_hours_enabled,
    quiet_hours_start,
    quiet_hours_end
) VALUES
-- Parent wants all notifications
('+639171234567', '11111111-1111-1111-1111-111111111111', true, true, true, true, true, true, true, '22:00:00', '06:00:00'),

-- Parent only wants critical notifications
('+639171234568', '22222222-2222-2222-2222-222222222222', false, false, true, true, true, true, true, '21:00:00', '07:00:00'),

-- Parent wants no quiet hours
('+639171234569', '33333333-3333-3333-3333-333333333333', true, true, true, false, false, false, false, NULL, NULL),

-- Parent wants minimal notifications
('+639171234570', '44444444-4444-4444-4444-444444444444', true, false, true, false, false, true, true, '22:00:00', '06:00:00')
ON CONFLICT (parent_phone, student_id) DO UPDATE SET
    check_in_enabled = EXCLUDED.check_in_enabled,
    check_out_enabled = EXCLUDED.check_out_enabled,
    late_arrival_enabled = EXCLUDED.late_arrival_enabled;

-- =====================================================
-- Verification Queries
-- =====================================================

-- Count records created
DO $$
DECLARE
    schedule_count INTEGER;
    student_count INTEGER;
    section_count INTEGER;
    device_count INTEGER;
    attendance_count INTEGER;
    preference_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO schedule_count FROM school_schedules;
    SELECT COUNT(*) INTO student_count FROM students;
    SELECT COUNT(*) INTO section_count FROM sections;
    SELECT COUNT(*) INTO device_count FROM iot_devices WHERE device_id = 'device-001';
    SELECT COUNT(*) INTO attendance_count FROM attendance;
    SELECT COUNT(*) INTO preference_count FROM notification_preferences;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Sample Data Created Successfully!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'School Schedules: %', schedule_count;
    RAISE NOTICE 'Students: %', student_count;
    RAISE NOTICE 'Sections: %', section_count;
    RAISE NOTICE 'IoT Devices: %', device_count;
    RAISE NOTICE 'Attendance Records: %', attendance_count;
    RAISE NOTICE 'Notification Preferences: %', preference_count;
    RAISE NOTICE '========================================';
END $$;

-- =====================================================
-- Sample Data Summary Comments
-- =====================================================

COMMENT ON TABLE students IS 'Contains 11 test students across different schedules';
COMMENT ON TABLE sections IS 'Contains 4 sections with different schedule assignments';

-- Note: Using existing IoT devices (device-001) from your system

-- =====================================================
-- Quick Test Queries
-- =====================================================

-- To view all students with their schedules:
-- SELECT s.student_number, s.first_name, s.last_name, 
--        sec.name as section, sch.name as schedule
-- FROM students s
-- LEFT JOIN sections sec ON s.section_id = sec.id
-- LEFT JOIN school_schedules sch ON sec.schedule_id = sch.id
-- ORDER BY s.student_number;

-- To view today's attendance:
-- SELECT s.student_number, s.first_name, s.last_name,
--        a.time_in, a.time_out, a.status, a.device_id
-- FROM attendance a
-- JOIN students s ON a.student_id = s.id
-- WHERE a.date = CURRENT_DATE
-- ORDER BY a.time_in;

-- To test notification preferences:
-- SELECT s.student_number, s.first_name, 
--        np.check_in_enabled, np.late_arrival_enabled,
--        np.quiet_hours_enabled
-- FROM notification_preferences np
-- JOIN students s ON np.student_id = s.id;
