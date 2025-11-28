# Adding Photo URL Column to Attendance Table

## Steps to Add the Column:

1. **Go to Supabase Dashboard**
   - Navigate to: https://supabase.com/dashboard
   - Select your project: `ddblgwzylvwuucnpmtzi`

2. **Open SQL Editor**
   - Click "SQL Editor" in the left sidebar
   - Click "New Query"

3. **Run This SQL:**

```sql
-- Add photo_url column to attendance table
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS photo_url TEXT;

-- Add comment for documentation
COMMENT ON COLUMN attendance.photo_url IS 'Public URL to attendance photo in Storage';

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_attendance_photo_url ON attendance(photo_url) WHERE photo_url IS NOT NULL;
```

4. **Click "Run" button**

5. **Verify the column was added:**

```sql
-- Check table structure
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'attendance' 
ORDER BY ordinal_position;
```

## After Adding the Column:

Run the test script again:
```bash
python3 utils/test-scripts/test_upload_attendance.py data/photos/test_attendance_221566.jpg
```

This will:
- ✅ Upload the photo to Supabase Storage
- ✅ Create an attendance record with the photo URL
- ✅ Allow the photo to display on the attendance view page
