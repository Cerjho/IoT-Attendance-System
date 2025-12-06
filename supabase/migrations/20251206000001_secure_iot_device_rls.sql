-- Secure RLS Policy for IoT Device Attendance Inserts
-- This migration allows IoT devices with anon key to insert attendance records
-- while maintaining security through device validation

-- Drop existing overly restrictive policies
DROP POLICY IF EXISTS "Allow INSERT for authenticated users only" ON attendance;
DROP POLICY IF EXISTS "Allow authenticated users to insert attendance" ON attendance;

-- ============================================================================
-- ATTENDANCE TABLE RLS POLICIES
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

-- Policy 2: Allow authenticated users (admin dashboard) to insert
CREATE POLICY "Allow authenticated users to insert attendance"
ON attendance
FOR INSERT
TO authenticated
WITH CHECK (true);

-- Policy 3: Allow everyone to read attendance (needed for parent portal)
CREATE POLICY "Allow public read access to attendance"
ON attendance
FOR SELECT
TO anon, authenticated
USING (true);

-- Policy 4: Only authenticated users can update/delete
CREATE POLICY "Allow authenticated users to update attendance"
ON attendance
FOR UPDATE
TO authenticated
USING (true)
WITH CHECK (true);

CREATE POLICY "Allow authenticated users to delete attendance"
ON attendance
FOR DELETE
TO authenticated
USING (true);

-- ============================================================================
-- IOT_DEVICES TABLE RLS POLICIES
-- ============================================================================

-- Ensure iot_devices table has proper RLS
ALTER TABLE iot_devices ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Allow anon to read active devices" ON iot_devices;
DROP POLICY IF EXISTS "Allow authenticated to manage devices" ON iot_devices;

-- Policy: Allow anon to read device info (for validation)
CREATE POLICY "Allow anon to read active devices"
ON iot_devices
FOR SELECT
TO anon, authenticated
USING (status = 'active');

-- Policy: Only authenticated users can manage devices
CREATE POLICY "Allow authenticated to manage devices"
ON iot_devices
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- ============================================================================
-- STUDENTS TABLE RLS POLICIES
-- ============================================================================

-- Ensure students table allows anon to read (needed for roster sync)
ALTER TABLE students ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon to read students" ON students;
DROP POLICY IF EXISTS "Allow authenticated to manage students" ON students;

-- Policy: Allow anon to read students (for roster sync and validation)
CREATE POLICY "Allow anon to read students"
ON students
FOR SELECT
TO anon, authenticated
USING (true);

-- Policy: Only authenticated users can manage students
CREATE POLICY "Allow authenticated to manage students"
ON students
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- ============================================================================
-- VERIFICATION & COMMENTS
-- ============================================================================

COMMENT ON POLICY "Allow IoT devices to insert attendance" ON attendance IS 
'Allows IoT devices using anon key to insert attendance records. Security enforced through:
1. Valid device_id required (must exist in iot_devices table)
2. Device must have status=active
3. Required fields validation (student_id, date, time_in/time_out)
This prevents unauthorized attendance insertion while allowing legitimate IoT devices to function.';

COMMENT ON POLICY "Allow anon to read active devices" ON iot_devices IS
'Allows anon key to validate device_id during attendance insertion. Only active devices are visible.';

COMMENT ON POLICY "Allow anon to read students" ON students IS
'Allows IoT devices to sync roster and validate student_ids. Read-only access prevents data modification.';
