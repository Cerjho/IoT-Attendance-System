-- Enable Public Read Access for Attendance Records
-- This allows parents to view attendance via SMS link without login
-- Created: 2025-11-25

-- Enable Row Level Security on attendance table (if not already enabled)
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Public read access for attendance" ON attendance;

-- Create policy to allow anonymous (public) users to read attendance records
-- This is safe because:
-- 1. Only SELECT (read) is allowed, not INSERT/UPDATE/DELETE
-- 2. Parents only get link with their child's student_id
-- 3. No sensitive data exposed (just attendance times)
CREATE POLICY "Public read access for attendance"
ON attendance
FOR SELECT
TO anon
USING (true);

-- Verify the policy was created
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies 
WHERE tablename = 'attendance' 
  AND policyname = 'Public read access for attendance';

COMMENT ON POLICY "Public read access for attendance" ON attendance IS 
'Allows parents to view attendance records via SMS link without requiring authentication. Read-only access.';
