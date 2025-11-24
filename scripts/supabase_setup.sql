-- Supabase Database Setup for IoT Attendance System
-- Run this SQL in your Supabase SQL Editor

-- 1. Create attendance table
CREATE TABLE IF NOT EXISTS attendance (
  id BIGSERIAL PRIMARY KEY,
  student_id TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  photo_url TEXT,
  qr_data TEXT,
  status TEXT DEFAULT 'present',
  device_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp);
CREATE INDEX IF NOT EXISTS idx_attendance_device_id ON attendance(device_id);
CREATE INDEX IF NOT EXISTS idx_attendance_status ON attendance(status);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;

-- 4. Create policy to allow all operations (adjust for production)
DROP POLICY IF EXISTS "Allow all operations on attendance" ON attendance;
CREATE POLICY "Allow all operations on attendance" 
  ON attendance 
  FOR ALL 
  USING (true)
  WITH CHECK (true);

-- 5. Optional: Create students table
CREATE TABLE IF NOT EXISTS students (
  id BIGSERIAL PRIMARY KEY,
  student_id TEXT UNIQUE NOT NULL,
  name TEXT,
  email TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id);

ALTER TABLE students ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all operations on students" ON students;
CREATE POLICY "Allow all operations on students"
  ON students
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 6. Verify tables created
SELECT 
  schemaname,
  tablename,
  tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('attendance', 'students');
