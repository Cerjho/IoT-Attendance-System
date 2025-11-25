#!/usr/bin/env python3
"""
System Integration Test
Tests all components without hardware dependencies
"""
import os
import sys
from datetime import datetime

# Load environment variables
print("Loading environment variables...")
with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

print("="*70)
print("IoT ATTENDANCE SYSTEM - INTEGRATION TEST")
print("="*70)
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Python: {sys.version.split()[0]}")
print()

# Track results
results = []

def test_module(name, test_func):
    """Run a test and track result"""
    try:
        test_func()
        results.append((name, True, None))
        return True
    except Exception as e:
        results.append((name, False, str(e)))
        return False

# Test 1: Configuration System
def test_config():
    from src.utils.config_loader import load_config
    config = load_config('config/config.json')
    
    # Verify env var resolution
    cloud_url = config.get('cloud.url')
    cloud_key = config.get('cloud.api_key')
    device_id = config.get('cloud.device_id')
    sms_user = config.get('sms_notifications.username')
    
    assert cloud_url and not cloud_url.startswith('${'), "Cloud URL not resolved"
    assert cloud_key and not cloud_key.startswith('${'), "Cloud key not resolved"
    assert device_id and not device_id.startswith('${'), "Device ID not resolved"
    assert sms_user and not sms_user.startswith('${'), "SMS username not resolved"
    
    print(f"  ✓ Config loaded: {len(config.get_all())} sections")
    print(f"  ✓ Environment variables resolved")
    print(f"  ✓ Cloud URL: {cloud_url[:40]}...")
    print(f"  ✓ Device ID: {device_id}")

# Test 2: Database
def test_database():
    from src.database.db_handler import AttendanceDatabase
    import sqlite3
    
    db = AttendanceDatabase('data/attendance.db')
    
    # Check tables
    conn = sqlite3.connect('data/attendance.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Check attendance count
    cursor.execute("SELECT COUNT(*) FROM attendance")
    attendance_count = cursor.fetchone()[0]
    
    # Check student count
    cursor.execute("SELECT COUNT(*) FROM students")
    student_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"  ✓ Database connected")
    print(f"  ✓ Tables: {len(tables)} ({', '.join(tables[:4])}...)")
    print(f"  ✓ Attendance records: {attendance_count}")
    print(f"  ✓ Students: {student_count}")

# Test 3: Cloud Sync
def test_cloud_sync():
    from src.utils.config_loader import load_config
    from src.database.db_handler import AttendanceDatabase
    from src.cloud.cloud_sync import CloudSyncManager
    from src.database.sync_queue import SyncQueueManager
    
    config = load_config('config/config.json')
    db = AttendanceDatabase('data/attendance.db')
    sync_queue = SyncQueueManager('data/attendance.db')
    
    cloud_sync = CloudSyncManager(config.get_all()['cloud'], db, sync_queue)
    status = cloud_sync.get_sync_status()
    
    print(f"  ✓ Cloud sync initialized")
    print(f"  ✓ Enabled: {status['enabled']}")
    print(f"  ✓ Online: {status['online']}")
    print(f"  ✓ Device ID: {status['device_id']}")
    print(f"  ✓ Unsynced records: {status['unsynced_records']}")

# Test 4: SMS Notifier
def test_sms():
    from src.utils.config_loader import load_config
    from src.notifications.sms_notifier import SMSNotifier
    
    config = load_config('config/config.json')
    sms_config = config.get_all()['sms_notifications']
    
    notifier = SMSNotifier(sms_config)
    
    print(f"  ✓ SMS notifier initialized")
    print(f"  ✓ Enabled: {sms_config.get('enabled')}")
    print(f"  ✓ API URL: {sms_config.get('api_url')}")

# Test 5: Roster Sync
def test_roster_sync():
    from src.utils.config_loader import load_config
    from src.sync.roster_sync import RosterSyncManager
    
    config = load_config('config/config.json')
    roster_sync = RosterSyncManager(config.get_all()['cloud'])
    
    cache_info = roster_sync.get_cache_info()
    
    print(f"  ✓ Roster sync initialized")
    print(f"  ✓ Enabled: {roster_sync.enabled}")
    print(f"  ✓ Cached students: {cache_info['cached_students']}")
    print(f"  ✓ Last sync: {cache_info.get('last_sync_date', 'Never')}")

# Test 6: File Structure
def test_file_structure():
    required_dirs = [
        'data/photos',
        'data/logs',
        'data/qr_codes',
        'docs/user-guides',
        'docs/technical',
        'docs/archived',
        'utils',
        'utils/test-scripts',
        'src/database',
        'src/cloud',
        'src/sync',
        'src/notifications'
    ]
    
    missing = []
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            missing.append(dir_path)
    
    assert len(missing) == 0, f"Missing directories: {missing}"
    
    print(f"  ✓ All {len(required_dirs)} required directories exist")
    
    # Check important files
    files = [
        'config/config.json',
        '.env',
        '.env.example',
        '.gitignore',
        'README.md',
        'attendance_system.py',
        'start_attendance.sh'
    ]
    
    for file_path in files:
        assert os.path.exists(file_path), f"Missing file: {file_path}"
    
    print(f"  ✓ All critical files present")

# Test 7: Environment Security
def test_security():
    import json
    
    # Check config.json doesn't have secrets
    with open('config/config.json', 'r') as f:
        config_text = f.read()
    
    # Should have placeholders
    assert '${SUPABASE_URL}' in config_text, "Missing SUPABASE_URL placeholder"
    assert '${SUPABASE_KEY}' in config_text, "Missing SUPABASE_KEY placeholder"
    assert '${SMS_USERNAME}' in config_text, "Missing SMS_USERNAME placeholder"
    
    # Should NOT have actual values
    assert 'eyJhbGciOiJIUzI1NiIs' not in config_text, "API key found in config!"
    assert 'ufckpgswkziojwoqosxw' not in config_text, "Supabase project ID in config!"
    
    print(f"  ✓ No credentials in config.json")
    print(f"  ✓ Environment variable placeholders present")
    print(f"  ✓ .env file exists and is gitignored")
    
    # Verify .env is gitignored
    with open('.gitignore', 'r') as f:
        gitignore = f.read()
    
    assert '.env' in gitignore, ".env not in .gitignore!"
    print(f"  ✓ .env properly gitignored")

# Run all tests
print("\n[1] Configuration System")
test_module("Configuration", test_config)

print("\n[2] Database System")
test_module("Database", test_database)

print("\n[3] Cloud Sync Manager")
test_module("Cloud Sync", test_cloud_sync)

print("\n[4] SMS Notification System")
test_module("SMS Notifier", test_sms)

print("\n[5] Roster Sync Manager")
test_module("Roster Sync", test_roster_sync)

print("\n[6] File Structure")
test_module("File Structure", test_file_structure)

print("\n[7] Security Configuration")
test_module("Security", test_security)

# Summary
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)

passed = sum(1 for _, success, _ in results if success)
failed = sum(1 for _, success, _ in results if not success)

for name, success, error in results:
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {name}")
    if error:
        print(f"       Error: {error[:60]}...")

print("\n" + "-"*70)
print(f"Total: {passed}/{len(results)} tests passed")

if failed == 0:
    print("\n🎉 ALL TESTS PASSED!")
    print("System is ready for deployment (hardware not tested)")
    sys.exit(0)
else:
    print(f"\n⚠️  {failed} test(s) failed")
    sys.exit(1)
