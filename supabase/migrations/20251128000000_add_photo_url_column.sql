-- Migration: Add photo_url column to attendance table
-- Date: 2025-11-28
-- Description: Add photo_url column to store Supabase Storage photo URLs

ALTER TABLE attendance ADD COLUMN IF NOT EXISTS photo_url TEXT;

COMMENT ON COLUMN attendance.photo_url IS 'Public URL to the captured attendance photo stored in Supabase Storage bucket';

-- Create index for faster queries (optional but recommended)
CREATE INDEX IF NOT EXISTS idx_attendance_photo_url ON attendance(photo_url) WHERE photo_url IS NOT NULL;
