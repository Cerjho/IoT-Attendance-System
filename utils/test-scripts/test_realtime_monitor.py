#!/usr/bin/env python3
"""
Test Real-time Monitoring System
Simulates events and verifies monitoring functionality
"""

import json
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/home/iot/attendance-system')

from src.utils.realtime_monitor import get_monitor

def test_monitor():
    """Test monitoring system"""
    print("=" * 70)
    print("REAL-TIME MONITORING SYSTEM TEST")
    print("=" * 70)
    print()
    
    # Initialize monitor
    print("[1/6] 📊 Initializing monitor...")
    monitor = get_monitor()
    monitor.start()
    print("✅ Monitor started")
    time.sleep(1)
    
    # Test event logging
    print("\n[2/6] 📝 Testing event logging...")
    monitor.log_event("scan", "Test attendance scan", {
        "student_id": "TEST001",
        "scan_type": "time_in"
    })
    monitor.log_event("sync", "Test cloud sync", {
        "record_id": 999
    })
    monitor.log_event("sms", "Test SMS notification", {
        "phone": "+1234567890"
    })
    print("✅ Logged 3 test events")
    time.sleep(1)
    
    # Test system state updates
    print("\n[3/6] 🔄 Testing system state updates...")
    monitor.update_system_state("camera", "online", "640x480")
    monitor.update_system_state("cloud", "online", "Connected")
    monitor.update_system_state("sms", "online", "Ready")
    print("✅ Updated 3 component states")
    time.sleep(1)
    
    # Get metrics
    print("\n[4/6] 📈 Fetching metrics...")
    metrics = monitor.get_metrics()
    print(f"  • Scans today: {metrics['scans_today']}")
    print(f"  • Queue size: {metrics['queue_size']}")
    print(f"  • Success rate: {metrics['success_rate']:.1f}%")
    print(f"  • Uptime: {metrics['uptime_seconds']}s")
    print("✅ Metrics retrieved")
    time.sleep(1)
    
    # Get system state
    print("\n[5/6] 🖥️  Checking system state...")
    state = monitor.get_system_state()
    print(f"  • Overall status: {state['status']}")
    print(f"  • Camera: {state['camera_status']}")
    print(f"  • Cloud: {state['cloud_status']}")
    print(f"  • SMS: {state['sms_status']}")
    print("✅ System state retrieved")
    time.sleep(1)
    
    # Get dashboard data
    print("\n[6/6] 📋 Getting complete dashboard data...")
    data = monitor.get_dashboard_data()
    print(f"  • Timestamp: {data['timestamp']}")
    print(f"  • Recent events: {len(data['recent_events'])}")
    print(f"  • Recent alerts: {len(data['recent_alerts'])}")
    print(f"  • Uptime: {data['uptime']}")
    print("✅ Dashboard data retrieved")
    time.sleep(1)
    
    # Export metrics
    print("\n[BONUS] 💾 Exporting metrics...")
    filepath = monitor.export_metrics()
    print(f"✅ Metrics exported to: {filepath}")
    
    # Display recent events
    print("\n" + "=" * 70)
    print("RECENT EVENTS")
    print("=" * 70)
    events = monitor.get_recent_events(5)
    for event in events[-5:]:
        timestamp = datetime.fromisoformat(event['timestamp']).strftime('%H:%M:%S')
        print(f"[{timestamp}] {event['type'].upper()}: {event['message']}")
    
    # Stop monitor
    print("\n" + "=" * 70)
    print("Stopping monitor...")
    monitor.stop()
    print("✅ Test complete!")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    try:
        success = test_monitor()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
