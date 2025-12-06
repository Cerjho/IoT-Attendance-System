-- Fix RLS policies for iot_devices table
-- The previous migration may have failed, so this ensures policies are correct

-- ============================================================================
-- Check current state and fix
-- ============================================================================

-- First, check if iot_devices table exists
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'iot_devices') THEN
        RAISE EXCEPTION 'iot_devices table does not exist. Run migration 20251206000002 first.';
    END IF;
END $$;

-- Enable RLS if not enabled
ALTER TABLE iot_devices ENABLE ROW LEVEL SECURITY;

-- Drop and recreate policies to ensure they're correct
DROP POLICY IF EXISTS "Allow anon to read active devices" ON iot_devices;
DROP POLICY IF EXISTS "Allow authenticated to manage devices" ON iot_devices;

-- Policy 1: Allow anon users to read ALL devices (not just active)
-- This is needed by the enrichment trigger which runs as anon role
CREATE POLICY "Allow anon to read iot_devices"
ON iot_devices
FOR SELECT
TO anon, authenticated
USING (true);

-- Policy 2: Allow authenticated users to manage devices
CREATE POLICY "Allow authenticated to manage iot_devices"
ON iot_devices
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- Verify the policies were created
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE tablename = 'iot_devices'
ORDER BY policyname;
