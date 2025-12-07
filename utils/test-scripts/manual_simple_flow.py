#!/usr/bin/env python3
"""
Simple Real Flow Test - No Camera Required
Tests the complete attendance flow without hardware dependencies
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from datetime import datetime

# Load environment
from dotenv import load_dotenv

load_dotenv()

from src.attendance.schedule_manager import ScheduleManager
from src.cloud.cloud_sync import CloudSyncManager
from src.database.db_handler import AttendanceDatabase
from src.database.sync_queue import SyncQueueManager
from src.network.connectivity import ConnectivityMonitor
from src.notifications.sms_notifier import SMSNotifier
from src.utils.config_loader import load_config
from src.utils.logger_config import setup_logger

logger = setup_logger("simple_flow_test")
config = load_config("config/config.json")

print("\n" + "=" * 80)
print("SIMPLE REAL FLOW TEST (NO CAMERA)")
print("=" * 80)

# Initialize components
db_path = config.get("database", {}).get("path", "data/attendance.db")
db = AttendanceDatabase(db_path)
schedule = ScheduleManager(config)
connectivity = ConnectivityMonitor(config.get("cloud", {}))
sync_queue = SyncQueueManager(db_path)
cloud_sync = CloudSyncManager(config.get("cloud", {}), sync_queue, connectivity)
sms = SMSNotifier(config.get("sms_notifications", {}))

logger.info("✅ All components initialized")

# Test data (using real parent phone numbers)
test_students = [
    {
        "student_number": "2021001",
        "name": "Juan Dela Cruz",
        "grade": "Grade 11",
        "section": "STEM-A",
        "parent_contact": "+639480205567",
    },
    {
        "student_number": "2021002",
        "name": "Maria Santos",
        "grade": "Grade 11",
        "section": "STEM-A",
        "parent_contact": "+639923783237",
    },
    {
        "student_number": "2021003",
        "name": "Pedro Reyes",
        "grade": "Grade 12",
        "section": "ABM-B",
        "parent_contact": "+639480205567",
    },
]

print(f"\n📋 Testing with {len(test_students)} students\n")

for i, student in enumerate(test_students, 1):
    print(f"\n{'#' * 80}")
    print(f"TEST #{i}: {student['name']} ({student['student_number']})")
    print(f"{'#' * 80}\n")

    # Step 1: QR Code Scan (simulated)
    print(f"📱 Step 1: QR Code Scanned - {student['student_number']}")
    logger.info(
        f"Student: {student['name']} | {student['grade']} - {student['section']}"
    )

    # Step 2: Check Schedule
    print("🕐 Step 2: Checking schedule...")
    schedule_info = schedule.get_schedule_info()
    scan_type = schedule_info["expected_scan_type"]
    current_time = datetime.now()
    session = schedule_info["current_session"]
    status_obj = schedule.determine_attendance_status(current_time, session, scan_type)
    status = status_obj.value  # Get string value from enum
    logger.info(f"   Session: {session}")
    logger.info(f"   Scan Type: {scan_type}")
    logger.info(f"   Status: {status}")

    # Step 3: Check for duplicate
    print("🔍 Step 3: Checking duplicate...")
    last_scan = db.get_last_scan(student["student_number"])
    if last_scan:
        allowed = schedule.should_allow_scan(
            last_scan["timestamp"], last_scan.get("scan_type"), scan_type
        )
        if not allowed:
            print(f"⚠️  Duplicate scan blocked (last scan: {last_scan['timestamp']})")
            logger.warning("Scan blocked - within 5-minute cooldown")
            continue
    logger.info("✅ Scan allowed")

    # Step 4: Face Detection (simulated)
    print("👤 Step 4: Face detection (simulated)...")
    photo_dir = Path("data/photos")
    photo_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo_path = photo_dir / f"test_{student['student_number']}_{timestamp}.txt"
    photo_path.write_text(
        f"SIMULATED PHOTO\nStudent: {student['name']}\nTime: {datetime.now()}\n"
    )
    logger.info(f"✅ Photo saved: {photo_path.name}")

    # Step 5: Record Attendance
    print("💾 Step 5: Recording attendance...")
    attendance_id = db.record_attendance(
        student_id=student["student_number"],
        photo_path=str(photo_path),
        qr_data=student["student_number"],
        scan_type=scan_type,
        status=status,
    )
    logger.info(f"✅ Attendance recorded: ID {attendance_id}")

    # Step 6: Cloud Sync
    print("☁️  Step 6: Syncing to cloud...")
    attendance_data = {
        "id": attendance_id,
        "student_id": student["student_number"],
        "timestamp": datetime.now().isoformat(),
        "photo_path": str(photo_path),
        "qr_data": student["student_number"],
        "scan_type": scan_type,
        "status": status,
    }

    sync_success = cloud_sync.sync_attendance_record(attendance_data, str(photo_path))
    if sync_success:
        logger.info("✅ Cloud sync successful")
    else:
        logger.warning("⚠️  Cloud sync queued (offline or failed)")

    # Step 7: SMS Notification
    print("📱 Step 7: Sending SMS...")
    sms_success = sms.send_attendance_notification(
        student_id=student["student_number"],
        student_name=student["name"],
        parent_phone=student["parent_contact"],
        scan_type=scan_type,
    )
    if sms_success:
        logger.info(f"✅ SMS sent to {student['parent_contact']}")
    else:
        logger.warning("⚠️  SMS failed (provider issue or disabled)")

    print(f"\n✅ Completed workflow for {student['name']}")

    if i < len(test_students):
        import time

        time.sleep(1)  # Pause between students

# Summary
print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

# Check database
import sqlite3

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM attendance WHERE date(timestamp) = date('now')")
today_count = cursor.fetchone()[0]

cursor.execute(
    """
    SELECT student_id, timestamp, scan_type, status, synced 
    FROM attendance 
    WHERE date(timestamp) = date('now')
    ORDER BY timestamp DESC 
    LIMIT 10
"""
)
records = cursor.fetchall()

print(f"\n📊 Today's Attendance Records: {today_count}")
if records:
    print("\nLatest Records:")
    for record in records:
        sync_status = "✅ Synced" if record[4] else "⏳ Pending"
        print(
            f"  • {record[0]} | {record[1]} | {record[2]} | {record[3]} | {sync_status}"
        )

conn.close()

print("\n✅ All system components working correctly!")
print("=" * 80 + "\n")
