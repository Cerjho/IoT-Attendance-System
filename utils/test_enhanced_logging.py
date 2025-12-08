#!/usr/bin/env python3
"""
Test script to demonstrate enhanced logging for SMS and Cloud Sync
"""
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.utils.config_loader import load_config
from src.utils.logger_config import setup_logger
from src.cloud.cloud_sync import CloudSyncManager
from src.database.sync_queue import SyncQueueManager
from src.network.connectivity import ConnectivityMonitor
from src.notifications.sms_notifier import SMSNotifier

def test_cloud_sync_logging():
    """Test cloud sync logging with sample data"""
    print("\n" + "="*60)
    print("Testing Cloud Sync Logging")
    print("="*60)
    
    # Setup
    config = load_config()
    logger = setup_logger("test_cloud_sync")
    
    sync_queue = SyncQueueManager(db_path="data/attendance.db")
    connectivity = ConnectivityMonitor(config)
    cloud_sync = CloudSyncManager(config, sync_queue, connectivity)
    
    # Create sample attendance data
    attendance_data = {
        "id": 999,
        "student_id": "2021001",
        "timestamp": datetime.now().isoformat(),
        "status": "present",
        "scan_type": "time_in",
        "qr_data": "TEST_QR"
    }
    
    print("\n📝 Sample attendance data:")
    print(f"   ID: {attendance_data['id']}")
    print(f"   Student: {attendance_data['student_id']}")
    print(f"   Status: {attendance_data['status']}")
    print(f"   Scan Type: {attendance_data['scan_type']}")
    
    print("\n🔄 Attempting cloud sync (check logs for detailed output)...")
    result = cloud_sync.sync_attendance_record(attendance_data, photo_path=None)
    
    print(f"\n✅ Result: {'Success' if result else 'Queued/Failed'}")
    print("\n💡 Enhanced logging includes:")
    print("   - Operation start with student ID and photo status")
    print("   - Queue status (disabled/offline)")
    print("   - Photo upload progress and results")
    print("   - Student UUID lookup")
    print("   - Cloud persistence confirmation with IDs")
    print("   - Detailed error messages with truncated info")
    
    return result

def test_sms_logging():
    """Test SMS notification logging"""
    print("\n" + "="*60)
    print("Testing SMS Notification Logging")
    print("="*60)
    
    # Setup
    config = load_config()
    logger = setup_logger("test_sms")
    
    sms_notifier = SMSNotifier(config)
    
    # Test data
    phone = "09123456789"
    message = "Test SMS notification for enhanced logging demonstration"
    
    print("\n📝 Sample SMS data:")
    print(f"   Phone: {phone}")
    print(f"   Message: {message[:50]}...")
    print(f"   Length: {len(message)} chars")
    
    print("\n📱 Attempting SMS send (check logs for detailed output)...")
    print("   Note: SMS sending disabled in config - will show logging format only")
    
    # This will log but not actually send since SMS is typically disabled
    result = sms_notifier.send_sms(phone, message)
    
    print(f"\n✅ Result: {'Sent' if result else 'Failed/Disabled'}")
    print("\n💡 Enhanced logging includes:")
    print("   - Send started with phone, length, and message preview")
    print("   - Phone number formatting (original → formatted)")
    print("   - Retry attempts with attempt number")
    print("   - Success with message ID and attempt count")
    print("   - HTTP errors with status code and response preview")
    print("   - SSL/Timeout/Connection errors with details")
    print("   - Final failure summary with exhausted attempts")
    
    return result

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Enhanced Logging Test Suite")
    print("="*60)
    print("\nThis script demonstrates the enhanced logging added for:")
    print("1. SMS Notifications (send_sms)")
    print("2. Cloud Sync Operations (sync_attendance_record)")
    print("3. Queue Processing (process_sync_queue)")
    print("\nLogs are written to:")
    print("- journalctl (when running as service)")
    print("- data/logs/attendance_system_YYYYMMDD.log")
    
    # Run tests
    try:
        test_cloud_sync_logging()
        test_sms_logging()
        
        print("\n" + "="*60)
        print("Test Complete!")
        print("="*60)
        print("\n📊 To view actual logs:")
        print("   sudo journalctl -u attendance-system.service -n 100")
        print("   tail -f data/logs/attendance_system_$(date +%Y%m%d).log")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
