-- Storage policies for attendance-photos bucket

-- Create storage bucket if not exists (via INSERT)
INSERT INTO storage.buckets (id, name, public)
VALUES ('attendance-photos', 'attendance-photos', true)
ON CONFLICT (id) DO NOTHING;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Public Access" ON storage.objects;
DROP POLICY IF EXISTS "Allow all operations" ON storage.objects;

-- Create policy to allow all operations on attendance-photos bucket
CREATE POLICY "Allow all operations on attendance-photos"
ON storage.objects
FOR ALL
TO public
USING (bucket_id = 'attendance-photos')
WITH CHECK (bucket_id = 'attendance-photos');
