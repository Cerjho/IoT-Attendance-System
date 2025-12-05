-- Enable read access to students table for IoT devices
-- This allows the anon API key to read student records

-- Add policy to allow reading student records
DROP POLICY IF EXISTS "Allow device read students" ON students;
CREATE POLICY "Allow device read students" 
ON students 
FOR SELECT 
TO anon, authenticated
USING (status = 'active');

-- Verify RLS is enabled
-- SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'students';
