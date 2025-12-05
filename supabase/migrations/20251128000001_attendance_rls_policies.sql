-- RLS Policy for Testing Attendance Inserts
-- This allows inserts to the attendance table for testing

-- First, check if RLS is enabled
-- SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'attendance';

-- Option 1: Temporarily disable RLS (NOT RECOMMENDED for production)
-- ALTER TABLE attendance DISABLE ROW LEVEL SECURITY;

-- Option 2: Add a policy to allow inserts (RECOMMENDED)
-- This policy allows any authenticated user to insert attendance records
DROP POLICY IF EXISTS "Allow test inserts" ON attendance;
CREATE POLICY "Allow test inserts" 
ON attendance 
FOR INSERT 
TO anon, authenticated
WITH CHECK (true);

-- Option 3: If you want to allow inserts only with valid student_id
-- CREATE POLICY IF NOT EXISTS "Allow inserts with valid student" 
-- ON attendance 
-- FOR INSERT 
-- TO anon, authenticated
-- WITH CHECK (
--   EXISTS (
--     SELECT 1 FROM students WHERE students.id = attendance.student_id
--   )
-- );

-- Also add select policy so we can read the records
DROP POLICY IF EXISTS "Allow test selects" ON attendance;
CREATE POLICY "Allow test selects" 
ON attendance 
FOR SELECT 
TO anon, authenticated
USING (true);
