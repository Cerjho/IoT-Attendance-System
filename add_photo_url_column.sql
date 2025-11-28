-- Add photo_url column to attendance table
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS photo_url TEXT;

COMMENT ON COLUMN attendance.photo_url IS 'URL to the captured photo in Supabase Storage';
