#!/usr/bin/env python3
"""
Test schedule sync from Supabase server
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

from src.sync.schedule_sync import ScheduleSync
from src.utils.config_loader import load_config

# Load environment
load_dotenv()

# Load config
config = load_config("config/config.json")

print("=" * 70)
print("🔄 TESTING SCHEDULE SYNC FROM SERVER")
print("=" * 70)

# Initialize schedule sync
schedule_sync = ScheduleSync(config)

if not schedule_sync.enabled:
    print("\n❌ Schedule sync is DISABLED")
    print("   Check Supabase URL and API key in .env")
    sys.exit(1)

print(f"\n1️⃣ Syncing schedules from Supabase...")
if schedule_sync.sync_schedules():
    print("   ✅ Schedules synced successfully")
else:
    print("   ❌ Schedule sync failed")
    sys.exit(1)

print(f"\n2️⃣ Fetching default schedule...")
schedule = schedule_sync.get_default_schedule()

if schedule:
    print(f"   ✅ Default schedule loaded:")
    print(f"      Name: {schedule['name']}")
    print(f"      Description: {schedule.get('description', 'N/A')}")
    print(f"\n   📅 MORNING SESSION:")
    print(f"      Class Time: {schedule['morning_start_time']} - {schedule['morning_end_time']}")
    print(
        f"      Login Window: {schedule['morning_login_window_start']} - {schedule['morning_login_window_end']}"
    )
    print(
        f"      Logout Window: {schedule['morning_logout_window_start']} - {schedule['morning_logout_window_end']}"
    )
    print(f"      Late Threshold: {schedule['morning_late_threshold_minutes']} minutes")
    print(f"\n   📅 AFTERNOON SESSION:")
    print(
        f"      Class Time: {schedule['afternoon_start_time']} - {schedule['afternoon_end_time']}"
    )
    print(
        f"      Login Window: {schedule['afternoon_login_window_start']} - {schedule['afternoon_login_window_end']}"
    )
    print(
        f"      Logout Window: {schedule['afternoon_logout_window_start']} - {schedule['afternoon_logout_window_end']}"
    )
    print(f"      Late Threshold: {schedule['afternoon_late_threshold_minutes']} minutes")
    print(f"\n   ⚙️  SETTINGS:")
    print(f"      Auto Detect Session: {schedule['auto_detect_session']}")
    print(f"      Allow Early Arrival: {schedule['allow_early_arrival']}")
    print(f"      Require Logout: {schedule['require_logout']}")
    print(f"      Cooldown: {schedule['duplicate_scan_cooldown_minutes']} minutes")
    print(f"      Status: {schedule['status']}")
    print(f"      Synced: {schedule['synced_at']}")
else:
    print("   ❌ No default schedule found")
    sys.exit(1)

print(f"\n3️⃣ Testing ScheduleManager with server schedule...")
from src.attendance.schedule_manager import ScheduleManager

manager = ScheduleManager(config, schedule)
print(f"   ✅ ScheduleManager initialized with server schedule")

# Get schedule info
from datetime import datetime

info = manager.get_schedule_info()
print(f"\n   📊 CURRENT SCHEDULE INFO:")
print(f"      Current Time: {info['current_time']}")
print(f"      Session: {info['current_session']}")
print(f"      Expected Scan: {info['expected_scan_type']}")
print(f"      Status: {info['attendance_status']}")
print(f"      In Login Window: {info['in_login_window']}")
print(f"      In Logout Window: {info['in_logout_window']}")

print("\n" + "=" * 70)
print("✅ SCHEDULE SYNC TEST COMPLETE")
print("=" * 70)
print("\nThe system will now use schedules from the server instead of config.json!")
print("To update schedules, modify them in Supabase and restart the system.")
print("=" * 70)
