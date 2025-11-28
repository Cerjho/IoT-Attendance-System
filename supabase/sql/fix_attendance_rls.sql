-- Fix Attendance Table for Testing
-- Run this in Supabase SQL Editor

-- Step 1: Add photo_url column
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS photo_url TEXT;

-- Step 2: Enable RLS if not already enabled
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;

-- Step 3: Drop and recreate policies using DO block
DO $$ 
BEGIN
    -- Drop existing policies if they exist
    DROP POLICY IF EXISTS "Allow attendance inserts" ON attendance;
    DROP POLICY IF EXISTS "Allow attendance selects" ON attendance;
    DROP POLICY IF EXISTS "Enable insert for anon" ON attendance;
    DROP POLICY IF EXISTS "Enable read for anon" ON attendance;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

-- Step 4: Create new policies
CREATE POLICY "Enable insert for anon"
ON attendance
FOR INSERT
TO anon
WITH CHECK (true);

CREATE POLICY "Enable read for anon"
ON attendance
FOR SELECT
TO anon
USING (true);

-- Step 5: Verify
SELECT 
    schemaname,
    tablename, 
    policyname, 
    permissive,
    roles,
    cmd
FROM pg_policies 
WHERE tablename = 'attendance'
ORDER BY policyname;
