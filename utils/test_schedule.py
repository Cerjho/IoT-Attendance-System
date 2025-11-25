#!/usr/bin/env python3
"""
Test School Schedule Manager
"""

import sys
import os
sys.path.insert(0, '/home/iot/attendance-system')

from datetime import datetime, time
from src.attendance.schedule_manager import ScheduleManager, SessionType, ScanType, AttendanceStatus
from src.utils import load_config

def test_schedule():
    """Test schedule manager with various times"""
    
    print("=" * 70)
    print("🕐 TESTING SCHOOL SCHEDULE MANAGER")
    print("=" * 70)
    
    # Load config
    config = load_config('config/config.json')
    schedule_config = config.get('school_schedule', {})
    
    # Initialize schedule manager
    manager = ScheduleManager(schedule_config)
    
    print("\n📋 Schedule Configuration:")
    print(f"   Morning: 7:00 AM - 12:00 PM")
    print(f"   Afternoon: 1:00 PM - 5:00 PM")
    print()
    
    # Test various times
    test_times = [
        ("06:45", "Before morning login"),
        ("07:00", "Morning class start"),
        ("07:20", "Morning late arrival"),
        ("09:00", "Mid morning class"),
        ("11:45", "Morning logout window"),
        ("12:15", "Between sessions"),
        ("12:45", "Afternoon login window"),
        ("13:00", "Afternoon class start"),
        ("13:20", "Afternoon late arrival"),
        ("15:00", "Mid afternoon class"),
        ("16:45", "Afternoon logout window"),
        ("18:00", "After school hours"),
    ]
    
    print("🧪 Testing Different Times:")
    print("-" * 70)
    
    for time_str, description in test_times:
        test_time = datetime.strptime(f"2025-11-25 {time_str}", "%Y-%m-%d %H:%M")
        
        session = manager.get_current_session(test_time)
        scan_type, detected_session = manager.get_expected_scan_type(test_time)
        status = manager.determine_attendance_status(test_time, session, scan_type)
        
        in_login = manager.is_within_login_window(test_time)
        in_logout = manager.is_within_logout_window(test_time)
        
        print(f"\n⏰ {time_str} - {description}")
        print(f"   Session: {session.value}")
        print(f"   Expected: {scan_type.value}")
        print(f"   Status: {status.value}")
        print(f"   Login window: {'✅' if in_login else '❌'}")
        print(f"   Logout window: {'✅' if in_logout else '❌'}")
    
    print("\n" + "=" * 70)
    
    # Test scan allowance logic
    print("\n🔍 Testing Scan Allowance Logic:")
    print("-" * 70)
    
    # Scenario 1: First scan of the day
    current_time = datetime.strptime("2025-11-25 07:00", "%Y-%m-%d %H:%M")
    allow, reason = manager.should_allow_scan("2024-0001", None, current_time)
    print(f"\nScenario 1: First scan at 7:00 AM")
    print(f"   Allow: {'✅ YES' if allow else '❌ NO'} - {reason}")
    
    # Scenario 2: Duplicate scan (too soon)
    last_scan = datetime.strptime("2025-11-25 07:00", "%Y-%m-%d %H:%M")
    current_time = datetime.strptime("2025-11-25 07:02", "%Y-%m-%d %H:%M")
    allow, reason = manager.should_allow_scan("2024-0001", last_scan, current_time)
    print(f"\nScenario 2: Duplicate scan 2 minutes later")
    print(f"   Allow: {'✅ YES' if allow else '❌ NO'} - {reason}")
    
    # Scenario 3: Logout scan (same session)
    last_scan = datetime.strptime("2025-11-25 07:00", "%Y-%m-%d %H:%M")
    current_time = datetime.strptime("2025-11-25 11:45", "%Y-%m-%d %H:%M")
    allow, reason = manager.should_allow_scan("2024-0001", last_scan, current_time)
    print(f"\nScenario 3: Logout scan at 11:45 AM (after login at 7:00 AM)")
    print(f"   Allow: {'✅ YES' if allow else '❌ NO'} - {reason}")
    
    # Scenario 4: Afternoon session scan
    last_scan = datetime.strptime("2025-11-25 07:00", "%Y-%m-%d %H:%M")
    current_time = datetime.strptime("2025-11-25 13:00", "%Y-%m-%d %H:%M")
    allow, reason = manager.should_allow_scan("2024-0001", last_scan, current_time)
    print(f"\nScenario 4: Afternoon login at 1:00 PM (after morning session)")
    print(f"   Allow: {'✅ YES' if allow else '❌ NO'} - {reason}")
    
    print("\n" + "=" * 70)
    print("✅ SCHEDULE MANAGER TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_schedule()
