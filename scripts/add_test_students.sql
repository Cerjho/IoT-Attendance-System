-- Add Test Students to Supabase
-- Run this in Supabase Dashboard → SQL Editor

INSERT INTO students (
    student_number,
    first_name,
    last_name,
    grade_level,
    section,
    parent_guardian_contact,
    status
) VALUES
    ('2021001', 'Juan', 'Dela Cruz', '11', 'STEM-A', '+639480205567', 'active'),
    ('2021002', 'Maria', 'Santos', '11', 'STEM-A', '+639923783237', 'active'),
    ('2021003', 'Pedro', 'Reyes', '12', 'ABM-B', '+639480205567', 'active'),
    ('STU001', 'Test', 'Student One', '11', 'STEM-A', '+639123456789', 'active'),
    ('STU002', 'Test', 'Student Two', '11', 'STEM-B', '+639123456790', 'active'),
    ('221566', 'Student', 'Sample A', '12', 'ABM-A', '+639123456791', 'active'),
    ('233294', 'Student', 'Sample B', '11', 'HUMSS-A', '+639123456792', 'active'),
    ('171770', 'Student', 'Sample C', '12', 'GAS-A', '+639123456793', 'active')
ON CONFLICT (student_number) DO NOTHING;

-- Verify students were added
SELECT student_number, first_name, last_name, grade_level, section, status
FROM students
ORDER BY student_number;
