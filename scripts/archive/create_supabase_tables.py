#!/usr/bin/env python3
"""
Create Supabase Tables via REST API
This script creates the necessary tables in your Supabase database
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env file")
    exit(1)

print("🔍 Connecting to Supabase...")
print(f"URL: {SUPABASE_URL}\n")

# SQL to create tables
sql = """
-- Create attendance table
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp);
CREATE INDEX IF NOT EXISTS idx_attendance_device_id ON attendance(device_id);

-- Enable Row Level Security
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Allow all operations on attendance" ON attendance;

-- Create policy to allow all operations
CREATE POLICY "Allow all operations on attendance" 
  ON attendance 
  FOR ALL 
  USING (true)
  WITH CHECK (true);

SELECT 'Tables created successfully!' as message;
"""

print("📝 Creating tables in Supabase...\n")
print("Note: You need to run this SQL in Supabase SQL Editor:")
print("1. Go to https://app.supabase.com")
print("2. Select your project")
print("3. Click 'SQL Editor' in left sidebar")
print("4. Click 'New Query'")
print("5. Copy and paste the SQL below")
print("6. Click 'Run'\n")
print("="*70)
print(sql)
print("="*70)

# Try to check if table exists using REST API
print("\n🔍 Checking if attendance table exists...")

headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}'
}

try:
    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/attendance?select=id&limit=1',
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ Attendance table exists!")
        print(f"Response: {response.text}")
    elif response.status_code == 404 or 'does not exist' in response.text:
        print("❌ Attendance table does NOT exist")
        print("Please run the SQL above in Supabase SQL Editor")
    else:
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error checking table: {e}")

print("\n" + "="*70)
print("After creating tables, run this to sync your data:")
print("  python scripts/sync_to_cloud.py")
print("="*70)
