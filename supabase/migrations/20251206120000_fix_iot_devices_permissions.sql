-- Fix iot_devices table permissions for trigger function
-- Issue: enrich_attendance_data() trigger function with SECURITY DEFINER
-- cannot read iot_devices table due to RLS policies blocking the function owner

-- ============================================================================
-- STEP 1: Grant necessary permissions to the function owner role
-- ============================================================================

-- Grant SELECT permission on iot_devices to authenticated role
-- (triggers run as the user who created them, typically postgres or service_role)
GRANT SELECT ON iot_devices TO authenticated;
GRANT SELECT ON iot_devices TO anon;
GRANT SELECT ON iot_devices TO service_role;

-- Ensure the postgres user (superuser) has full access
-- Note: In Supabase, the trigger function owner is typically 'postgres'
GRANT ALL ON iot_devices TO postgres;

-- ============================================================================
-- STEP 2: Update RLS policy to allow trigger function access
-- ============================================================================

-- Drop existing read policies
DROP POLICY IF EXISTS "Allow anon to read active devices" ON iot_devices;
DROP POLICY IF EXISTS "Allow reading active devices" ON iot_devices;

-- Create more permissive read policy that works for both direct queries and triggers
CREATE POLICY "Allow reading active devices"
ON iot_devices
FOR SELECT
USING (status = 'active');

-- Alternative: Disable RLS for iot_devices if it's safe in your deployment
-- ALTER TABLE iot_devices DISABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 3: Ensure function is owned by proper role with permissions
-- ============================================================================

-- The function should be owned by postgres (superuser) or a role with SELECT on iot_devices
-- Reassign function ownership to postgres (this ensures SECURITY DEFINER runs with full permissions)
ALTER FUNCTION public.enrich_attendance_data() OWNER TO postgres;

-- ============================================================================
-- STEP 4: Grant execute permission on the function
-- ============================================================================

-- Allow anon and authenticated users to trigger this function via INSERT
GRANT EXECUTE ON FUNCTION public.enrich_attendance_data() TO anon;
GRANT EXECUTE ON FUNCTION public.enrich_attendance_data() TO authenticated;
GRANT EXECUTE ON FUNCTION public.enrich_attendance_data() TO service_role;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check table permissions
SELECT 
    grantee, 
    table_name, 
    privilege_type 
FROM information_schema.table_privileges 
WHERE table_name = 'iot_devices' 
ORDER BY grantee, privilege_type;

-- Check function owner
SELECT 
    proname as function_name,
    pg_get_userbyid(proowner) as owner,
    prosecdef as security_definer
FROM pg_proc 
WHERE proname = 'enrich_attendance_data';

-- Test query that the trigger will run (should work now)
-- SELECT section_id FROM iot_devices WHERE device_id = 'device_001' AND status = 'active' LIMIT 1;
