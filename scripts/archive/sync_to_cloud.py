#!/usr/bin/env python3
"""
Sync Local Attendance Records to Supabase Cloud
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("="*70)
print("SYNC TO SUPABASE CLOUD")
print("="*70)

from attendance_system import IoTAttendanceSystem

print("\n🔄 Initializing system...")
system = IoTAttendanceSystem()

print(f"\n📊 Current Status:")
status = system.cloud_sync.get_sync_status()
print(f"  - Cloud Sync: {'✅ Enabled' if status['enabled'] else '❌ Disabled'}")
print(f"  - Online: {'✅ Yes' if status['online'] else '❌ No'}")
print(f"  - Device ID: {status['device_id']}")
print(f"  - Unsynced Records: {status['unsynced_records']}")
print(f"  - Queue Size: {status['queue_size']}")

if not status['enabled']:
    print("\n❌ Cloud sync is disabled!")
    print("Enable it in config/config.json: cloud.enabled = true")
    exit(1)

if not status['online']:
    print("\n❌ No internet connection!")
    print("Check your network and try again.")
    exit(1)

if status['unsynced_records'] == 0:
    print("\n✅ All records are already synced!")
    exit(0)

print(f"\n🚀 Starting sync of {status['unsynced_records']} records...")
print("This may take a moment...\n")

try:
    result = system.cloud_sync.force_sync_all()
    
    print("="*70)
    print("SYNC COMPLETE")
    print("="*70)
    print(f"\n✅ Successfully synced: {result['succeeded']} records")
    
    if result['failed'] > 0:
        print(f"❌ Failed to sync: {result['failed']} records")
        print("\nCheck logs for details:")
        print("  tail -f data/logs/attendance_system_*.log | grep -i sync")
    
    print(f"\n📊 Final Status:")
    status = system.cloud_sync.get_sync_status()
    print(f"  - Unsynced Records: {status['unsynced_records']}")
    print(f"  - Queue Size: {status['queue_size']}")
    
    print("\n💡 View your data in Supabase:")
    print("  https://app.supabase.com → Table Editor → attendance")
    print("\n" + "="*70)
    
except Exception as e:
    print(f"\n❌ Error during sync: {e}")
    print("\nPossible issues:")
    print("  1. Tables not created in Supabase")
    print("     → Run: python scripts/create_supabase_tables.py")
    print("  2. Storage bucket not created")
    print("     → Create 'attendance-photos' bucket in Supabase Storage")
    print("  3. Wrong credentials")
    print("     → Check .env file")
    exit(1)
