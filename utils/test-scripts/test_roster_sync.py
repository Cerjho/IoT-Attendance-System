#!/usr/bin/env python3
"""
Test script for Roster Sync functionality
Tests downloading student roster from Supabase and caching locally
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.sync import RosterSyncManager
from src.utils import load_config
import json


def main():
    print("\n" + "="*70)
    print("🧪 Roster Sync Test")
    print("="*70)
    
    # Load configuration
    print("\n[1] Loading configuration...")
    config = load_config('config/config.json')
    cloud_config = config.get('cloud', {})
    
    print(f"   Supabase URL: {cloud_config.get('url', 'Not configured')}")
    print(f"   Device ID: {cloud_config.get('device_id', 'Not configured')}")
    print(f"   Roster sync enabled: {cloud_config.get('enabled', False)}")
    
    # Initialize roster sync manager
    print("\n[2] Initializing roster sync manager...")
    roster_sync = RosterSyncManager(cloud_config)
    
    if not roster_sync.enabled:
        print("   ❌ Roster sync is disabled in configuration")
        return
    
    # Get current cache info
    print("\n[3] Current cache status:")
    cache_info = roster_sync.get_cache_info()
    print(f"   Cached students: {cache_info['cached_students']}")
    print(f"   Last sync date: {cache_info.get('last_sync_date', 'Never')}")
    print(f"   Last sync time: {cache_info.get('last_sync_timestamp', 'Never')}")
    print(f"   Sync needed: {cache_info.get('sync_needed', True)}")
    
    # Download roster
    print("\n[4] Downloading today's roster from Supabase...")
    result = roster_sync.download_today_roster(force=True)
    
    if result['success']:
        print(f"   ✅ SUCCESS: {result['message']}")
        print(f"   Students synced: {result['students_synced']}")
    else:
        print(f"   ❌ FAILED: {result['message']}")
        return
    
    # Test student lookup
    print("\n[5] Testing student lookup from cache...")
    
    # Get updated cache info
    cache_info = roster_sync.get_cache_info()
    cached_count = cache_info['cached_students']
    
    if cached_count > 0:
        print(f"   Cache contains {cached_count} students")
        
        # Test with a sample student ID (you can change this)
        test_ids = ["2021001", "STU001", "TEST123"]
        
        for test_id in test_ids:
            student = roster_sync.get_cached_student(test_id)
            if student:
                print(f"   ✓ Found student {test_id}:")
                print(f"     Name: {student.get('name', 'Unknown')}")
                print(f"     Email: {student.get('email', 'N/A')}")
                print(f"     Parent Phone: {student.get('parent_phone', 'N/A')}")
            else:
                print(f"   ✗ Student {test_id} not found in roster")
    else:
        print("   No students in cache")
    
    # Test roster check
    print("\n[6] Testing roster membership check...")
    test_id = "2021001"
    is_in_roster = roster_sync.is_student_in_roster(test_id)
    print(f"   Is {test_id} in roster? {is_in_roster}")
    
    # Display final cache info
    print("\n[7] Final cache information:")
    cache_info = roster_sync.get_cache_info()
    print(f"   Cached students: {cache_info['cached_students']}")
    print(f"   Last sync: {cache_info.get('last_sync_timestamp', 'Unknown')}")
    print(f"   Device ID: {cache_info.get('device_id', 'Unknown')}")
    
    # Optional: Test cache wipe
    print("\n[8] Testing cache wipe (optional)...")
    user_input = input("   Do you want to test cache wipe? (y/N): ").strip().lower()
    
    if user_input == 'y':
        print("   Wiping roster cache...")
        if roster_sync.wipe_roster_cache():
            print("   ✅ Cache wiped successfully")
            cache_info = roster_sync.get_cache_info()
            print(f"   Remaining students: {cache_info['cached_students']}")
        else:
            print("   ❌ Failed to wipe cache")
    else:
        print("   Skipping cache wipe test")
    
    print("\n" + "="*70)
    print("✅ Test complete!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
