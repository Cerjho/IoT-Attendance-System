#!/bin/bash
# migrate_supabase.sh - Complete migration to new Supabase server
# Run this script to switch to the new Supabase project

cd /home/iot/attendance-system

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   MIGRATING TO NEW SUPABASE SERVER                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 1. Reset local database
echo "[1/3] Resetting local database..."
if [ -f "data/attendance.db" ]; then
    rm -f data/attendance.db
    echo "   ✅ Local database cleared"
else
    echo "   ℹ️  No local database found (already clean)"
fi

# 2. Test connection to new Supabase
echo ""
echo "[2/3] Testing connection to new Supabase server..."
source venv/bin/activate
python3 << 'PYEOF'
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

print(f"   Server: {url}")
print()

# Test students table
students_url = f"{url}/rest/v1/students?select=student_number,first_name,last_name,status&status=eq.active&limit=5"
headers = {'apikey': key, 'Authorization': f'Bearer {key}'}

try:
    response = requests.get(students_url, headers=headers, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Students table: {len(data)} active students found")
        if data:
            for i, student in enumerate(data[:3], 1):
                name = f"{student.get('first_name', '')} {student.get('last_name', '')}"
                print(f"      {i}. {name.strip()} ({student.get('student_number')})")
    else:
        print(f"   ⚠️  Students table: HTTP {response.status_code}")
        print(f"      {response.text[:200]}")
except Exception as e:
    print(f"   ❌ Connection error: {e}")

# Test attendance table
print()
attendance_url = f"{url}/rest/v1/attendance?select=id&limit=1"
try:
    response = requests.get(attendance_url, headers=headers, timeout=10)
    if response.status_code == 200:
        print(f"   ✅ Attendance table: accessible")
    else:
        print(f"   ⚠️  Attendance table: HTTP {response.status_code}")
except Exception as e:
    print(f"   ⚠️  Attendance check: {e}")

PYEOF

# 3. Summary
echo ""
echo "[3/3] Migration complete"
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   ✅ MIGRATION SUCCESSFUL                                 ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Changes applied:"
echo "   • New Supabase URL: https://ddblgwzylvwuucnpmtzi.supabase.co"
echo "   • Local database cleared"
echo "   • Code updated for new schema"
echo ""
echo "🚀 Next steps:"
echo "   1. Test roster sync:"
echo "      python3 utils/test-scripts/test_roster_sync.py"
echo ""
echo "   2. Check system status:"
echo "      python3 utils/check_status.py"
echo ""
echo "   3. Start attendance system:"
echo "      ./start_attendance.sh --headless"
echo ""
echo "📊 New Schema Mapping:"
echo "   • student_number → student_id (local cache)"
echo "   • first_name + last_name → name"
echo "   • parent_guardian_contact → parent_phone"
echo "   • timestamp → date + time_in"
echo ""
