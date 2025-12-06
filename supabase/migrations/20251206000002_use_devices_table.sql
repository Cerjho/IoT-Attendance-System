-- Migration: Rename devices table to iot_devices and fix RLS policies
-- This ensures the IoT device can insert attendance records

-- ============================================================================
-- STEP 1: Drop old iot_devices table and rename devices to iot_devices
-- ============================================================================

-- Drop attendance policies that might conflict
DROP POLICY IF EXISTS "Allow IoT devices to insert attendance" ON attendance;
DROP POLICY IF EXISTS "Allow authenticated users to insert attendance" ON attendance;

-- Drop old iot_devices table completely (wrong structure)
DROP TABLE IF EXISTS iot_devices CASCADE;

-- Rename devices table to iot_devices (this has the correct structure)
ALTER TABLE devices RENAME TO iot_devices;

-- ============================================================================
-- STEP 2: Add RLS policies for iot_devices table
-- ============================================================================

-- Enable RLS on iot_devices table
ALTER TABLE iot_devices ENABLE ROW LEVEL SECURITY;

-- Allow anon users to read active devices (needed for device validation)
CREATE POLICY "Allow anon to read active devices"
ON iot_devices
FOR SELECT
TO anon
USING (status = 'active');

-- Allow authenticated users to manage devices
CREATE POLICY "Allow authenticated to manage devices"
ON iot_devices
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- ============================================================================
-- STEP 3: Recreate attendance INSERT policy with iot_devices table
-- ============================================================================

-- Policy 1: Allow IoT devices to INSERT attendance records
-- Security: Requires valid device_id in iot_devices table
CREATE POLICY "Allow IoT devices to insert attendance"
ON attendance
FOR INSERT
TO anon
WITH CHECK (
  -- Must provide a device_id
  device_id IS NOT NULL
  AND
  -- Device must exist in iot_devices table and be active
  EXISTS (
    SELECT 1 FROM iot_devices
    WHERE iot_devices.device_id = attendance.device_id
    AND iot_devices.status = 'active'
  )
  AND
  -- Must provide required fields
  student_id IS NOT NULL
  AND date IS NOT NULL
  AND (time_in IS NOT NULL OR time_out IS NOT NULL)
);

-- Policy 2: Allow authenticated users to insert attendance
CREATE POLICY "Allow authenticated users to insert attendance"
ON attendance
FOR INSERT
TO authenticated
WITH CHECK (true);

-- ============================================================================
-- STEP 4: Ensure device_001 exists in iot_devices table
-- ============================================================================

-- Insert device_001 if it doesn't exist (idempotent)
-- Note: devices table uses 'name' column (not 'device_name')
-- Note: location column is JSON type
INSERT INTO iot_devices (device_id, name, location, status)
VALUES (
  'device_001',
  'IoT Attendance Scanner',
  '{"building": "Main Building", "floor": "Ground Floor", "area": "Main Entrance"}'::jsonb,
  'active'
)
ON CONFLICT (device_id) DO UPDATE
SET 
  name = EXCLUDED.name,
  location = EXCLUDED.location,
  status = 'active',
  updated_at = NOW();

-- ============================================================================
-- VERIFICATION QUERIES (run these after migration to verify)
-- ============================================================================

-- Verify iot_devices table policies
-- SELECT schemaname, tablename, policyname, roles, cmd 
-- FROM pg_policies 
-- WHERE tablename = 'iot_devices';

-- Verify device_001 exists
-- SELECT * FROM iot_devices WHERE device_id = 'device_001';

-- Test anon can read iot_devices
-- SELECT * FROM iot_devices WHERE status = 'active';
