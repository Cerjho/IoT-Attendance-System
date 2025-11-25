# Supabase Cloud Sync Setup Guide

## Quick Setup (5 minutes)

### Step 1: Create Supabase Tables

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project
3. Click **SQL Editor** in the left sidebar
4. Click **New Query**
5. Copy and paste the contents of `scripts/supabase_setup.sql`
6. Click **Run** (or press Ctrl+Enter)

You should see: **Success. No rows returned**

### Step 2: Create Storage Bucket

1. In Supabase Dashboard, click **Storage** in the left sidebar
2. Click **New bucket**
3. Name: `attendance-photos`
4. **Public bucket**: Toggle ON (for easy access)
5. Click **Create bucket**

### Step 3: Configure Your Application

Edit your `.env` file:

```bash
# Get these from Supabase Dashboard → Settings → API
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-public-key-here
DEVICE_ID=device_001
```

**Where to find credentials:**
- URL: Settings → API → Project URL
- Key: Settings → API → Project API keys → `anon` `public` key

### Step 4: Enable Cloud Sync

Edit `config/config.json`:

```json
{
  "cloud": {
    "enabled": true
  }
}
```

### Step 5: Restart the System

```bash
# Stop current process (Ctrl+C if running)

# Restart
./start_attendance.sh --headless
```

## Verification

### Check if credentials work:

```bash
source venv/bin/activate
python -c "
from supabase import create_client
import os

url = os.getenv('SUPABASE_URL', 'not-set')
key = os.getenv('SUPABASE_KEY', 'not-set')

print(f'URL: {url}')
print(f'Key: {key[:20]}...' if len(key) > 20 else f'Key: {key}')

if url != 'not-set' and key != 'not-set':
    try:
        client = create_client(url, key)
        result = client.table('attendance').select('*').limit(1).execute()
        print('✅ Connection successful!')
        print(f'Found {len(result.data)} records')
    except Exception as e:
        print(f'❌ Connection failed: {e}')
else:
    print('❌ Credentials not configured')
"
```

### Check sync status:

```bash
source venv/bin/activate
python -c "
from attendance_system import IoTAttendanceSystem
s = IoTAttendanceSystem()
status = s.cloud_sync.get_sync_status()
print(f'Cloud Sync Enabled: {status[\"enabled\"]}')
print(f'Online: {status[\"online\"]}')
print(f'Pending Records: {status[\"unsynced_records\"]}')
print(f'Queue Size: {status[\"queue_size\"]}')
"
```

### Force sync all pending records:

```bash
source venv/bin/activate
python -c "
from attendance_system import IoTAttendanceSystem
s = IoTAttendanceSystem()
result = s.cloud_sync.force_sync_all()
print(f'Synced: {result[\"succeeded\"]}/{result[\"processed\"]} records')
"
```

## View Data in Supabase

### Method 1: Table Editor
1. Go to Supabase Dashboard
2. Click **Table Editor**
3. Select **attendance** table
4. View your synced records

### Method 2: SQL Query
1. Click **SQL Editor**
2. Run:
```sql
SELECT 
  id,
  student_id,
  timestamp,
  photo_url,
  status,
  device_id
FROM attendance
ORDER BY timestamp DESC
LIMIT 20;
```

### Method 3: Check photos
1. Click **Storage**
2. Select **attendance-photos** bucket
3. Browse by student_id folders

## Troubleshooting

### "No tables found"
→ Run `scripts/supabase_setup.sql` in Supabase SQL Editor

### "Connection failed"
→ Check credentials in `.env` file
→ Verify Project URL and API key are correct

### "Storage bucket not found"
→ Create bucket named `attendance-photos` in Supabase Storage

### "Policy violation"
→ Tables have RLS enabled - policies are created in setup script
→ Re-run the SQL setup if needed

### Records not syncing
→ Check `cloud.enabled: true` in config.json
→ Verify internet connection
→ Check logs: `tail -f logs/attendance_system_*.log`

## Production Security (Optional)

For production, restrict access with better RLS policies:

```sql
-- Remove permissive policy
DROP POLICY "Allow all operations on attendance" ON attendance;

-- Create device-specific policy
CREATE POLICY "Device can insert own records"
  ON attendance
  FOR INSERT
  WITH CHECK (device_id = current_setting('app.device_id', true));

-- Create read policy
CREATE POLICY "Allow read access"
  ON attendance
  FOR SELECT
  USING (true);
```

Then set device_id when connecting:
```python
client.rpc('set_config', {
    'setting': 'app.device_id',
    'value': 'device_001'
})
```
