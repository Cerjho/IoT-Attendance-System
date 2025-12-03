#!/usr/bin/env python3
"""
COMPLETE REAL SYSTEM SIMULATION
Runs the full attendance system with all components EXCEPT camera hardware
Uses real photos, real cloud sync, real SMS, real everything!
"""
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.face_quality import FaceQualityChecker
from src.attendance.schedule_manager import ScheduleManager
from src.utils.config_loader import load_config
from src.database.sync_queue import SyncQueueManager
from src.cloud.cloud_sync import CloudSyncManager
from src.network.connectivity import ConnectivityMonitor
from src.notifications.sms_notifier import SMSNotifier
from src.utils.logger_config import setup_logger
import cv2
import sqlite3
import json
import logging

# Setup logging
logger = setup_logger(__name__, "data/logs")

# Real student data from Supabase (ONLY students that actually exist)
REAL_STUDENTS = [
    {
        "student_number": "221566",
        "name": "John Paolo Gonzales",
        "photo": "data/photos/221566_20251202_215540.jpg",
        "qr_code": "221566",
        "parent_phone": "+639123456789"
    },
    {
        "student_number": "233294",
        "name": "Maria Santos",
        "photo": "data/photos/233294_20251202_215605.jpg",
        "qr_code": "233294",
        "parent_phone": "+639234567890"
    },
    {
        "student_number": "171770",
        "name": "Arabella Jarapa",
        "photo": "data/photos/221567_20251202_215606.jpg",  # Using available photo
        "qr_code": "171770",
        "parent_phone": "+639345678901"
    },
]

# Unknown students (should fail lookup)
UNKNOWN_STUDENTS = [
    {"name": "Unknown Student 1", "photo": "data/photos/221566_20251202_215951.jpg", "qr_code": "999001"},
    {"name": "Unknown Student 2", "photo": "data/photos/221567_20251202_215953.jpg", "qr_code": "999002"},
]


class CompleteSystemSimulator:
    """Full system simulation using ALL real components"""

    def __init__(self):
        print("\n" + "=" * 80)
        print("🚀 COMPLETE REAL SYSTEM SIMULATION")
        print("=" * 80)
        print("Using ALL real components: Quality Check, Schedule, Database,")
        print("Cloud Sync, SMS Notifications - Everything except camera hardware!")
        print("=" * 80 + "\n")

        # Load configuration
        self.config = load_config("config/config.json")
        self.db_path = "data/attendance.db"
        
        # Initialize database FIRST (before sync queue manager)
        self._init_database()
        
        # Initialize ALL real system components
        print("\n🔧 Initializing System Components...")
        self.quality_checker = FaceQualityChecker()
        print("   ✅ Face Quality Checker")
        
        self.schedule_manager = ScheduleManager(self.config)
        print("   ✅ Schedule Manager")
        
        self.connectivity = ConnectivityMonitor(self.config.get("network", {}))
        print("   ✅ Connectivity Monitor")
        
        self.sync_queue = SyncQueueManager(self.db_path)
        print("   ✅ Sync Queue Manager")
        
        # Cloud sync manager
        cloud_config = self.config.get("cloud", {})
        self.cloud_sync = CloudSyncManager(cloud_config, self.sync_queue, self.connectivity)
        print(f"   ✅ Cloud Sync Manager (enabled: {cloud_config.get('enabled', False)})")
        
        # SMS notifier
        sms_config = self.config.get("sms_notifications", {})
        self.sms_notifier = SMSNotifier(sms_config)
        print(f"   ✅ SMS Notifier (enabled: {sms_config.get('enabled', False)})")
        print()

    def _init_database(self):
        """Initialize database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create attendance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                photo_path TEXT,
                qr_data TEXT,
                scan_type TEXT,
                status TEXT
            )
        """)
        
        # Create sync_queue table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_type TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        
        # Load real students into roster
        for student in REAL_STUDENTS:
            cursor.execute(
                "INSERT OR IGNORE INTO students (student_number, name) VALUES (?, ?)",
                (student["student_number"], student["name"])
            )
        conn.commit()
        conn.close()
        
        print("✅ Database initialized")
        print(f"✅ Loaded {len(REAL_STUDENTS)} students into local roster")
        for student in REAL_STUDENTS:
            print(f"   - {student['student_number']}: {student['name']}")

    def process_attendance(self, student_data: dict, is_known: bool = True):
        """
        Process a single attendance scan through the COMPLETE system flow
        
        Steps:
        1. QR Code Validation
        2. Student Lookup (from local DB)
        3. Schedule Validation (determine scan type & status)
        4. Photo Quality Assessment
        5. Save Attendance Record (local DB)
        6. Queue for Cloud Sync
        7. Attempt Cloud Sync (if online)
        8. Send SMS Notification (if enabled)
        """
        
        print("\n" + "─" * 80)
        name = student_data.get("name", "Unknown")
        qr_code = student_data["qr_code"]
        photo_path = student_data["photo"]
        print(f"📸 Processing: {name} ({qr_code})")
        print(f"   Photo: {photo_path}")
        print("─" * 80)
        
        try:
            # Step 1: QR Code Validation
            print("\n[1/8] QR Code Validation")
            if not qr_code:
                print("   ❌ No QR code provided")
                return False
            print(f"   ✅ QR Scanned: {qr_code}")
            
            # Step 2: Student Lookup
            print("\n[2/8] Student Lookup (Local Database)")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, student_number, name FROM students WHERE student_number = ?",
                (qr_code,)
            )
            student_record = cursor.fetchone()
            
            if not student_record:
                print(f"   ❌ Student not found in roster: {qr_code}")
                conn.close()
                return False
            
            student_id, student_number, student_name = student_record
            print(f"   ✅ Found: {student_name} (DB ID: {student_id})")
            
            # Step 3: Schedule Validation
            print("\n[3/8] Schedule Validation")
            scan_type, session = self.schedule_manager.get_expected_scan_type()
            status = self.schedule_manager.determine_attendance_status(
                datetime.now(), session, scan_type
            )
            print(f"   ✅ Scan Type: {scan_type}")
            print(f"   ✅ Status: {status}")
            print(f"   ✅ Session: {session}")
            
            # Step 4: Photo Quality Assessment
            print("\n[4/8] Photo Quality Assessment")
            if not os.path.exists(photo_path):
                print(f"   ❌ Photo not found: {photo_path}")
                conn.close()
                return False
            
            frame = cv2.imread(photo_path)
            if frame is None:
                print(f"   ❌ Failed to load image")
                conn.close()
                return False
            
            quality_results = self.quality_checker.check_quality(
                frame, (0, 0, frame.shape[1], frame.shape[0])
            )
            
            # Parse quality results
            passed = quality_results.get("passed", False)
            score = quality_results.get("score", 0)
            checks = quality_results.get("checks", {})
            
            print(f"   Quality Score: {score:.1f}%")
            print(f"   Overall: {'✅ PASSED' if passed else '❌ FAILED'}")
            
            # Show individual checks
            if checks:
                for check_name, check_passed in checks.items():
                    symbol = "✅" if check_passed else "❌"
                    print(f"     {symbol} {check_name}")
            
            # Step 5: Save Attendance Record
            print("\n[5/8] Saving Attendance Record to Local Database")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            photo_filename = f"{student_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            saved_photo_path = f"data/photos/{photo_filename}"
            
            # Copy photo to attendance location
            import shutil
            shutil.copy2(photo_path, saved_photo_path)
            
            cursor.execute(
                """
                INSERT INTO attendance (student_id, timestamp, photo_path, qr_data, scan_type, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (student_number, timestamp, saved_photo_path, qr_code, scan_type.value, status.value)
            )
            attendance_id = cursor.lastrowid
            conn.commit()
            
            print(f"   ✅ Attendance ID: {attendance_id}")
            print(f"   ✅ Timestamp: {timestamp}")
            print(f"   ✅ Photo saved: {saved_photo_path}")
            
            # Step 6: Queue for Cloud Sync
            print("\n[6/8] Queueing for Cloud Sync")
            queue_data = {
                "student_number": student_number,
                "timestamp": timestamp,
                "scan_type": scan_type.value,
                "status": status.value,
                "photo_path": saved_photo_path,
                "quality_score": score,
                "quality_passed": passed
            }
            
            cursor.execute(
                "INSERT INTO sync_queue (record_type, record_id, data) VALUES (?, ?, ?)",
                ("attendance", attendance_id, json.dumps(queue_data))
            )
            conn.commit()
            print(f"   ✅ Added to sync queue")
            
            # Step 7: Attempt Cloud Sync
            print("\n[7/8] Cloud Sync")
            if self.cloud_sync.enabled and self.connectivity.is_online():
                print("   🌐 System is ONLINE - Attempting cloud sync...")
                try:
                    # Process sync queue
                    result = self.cloud_sync.process_sync_queue()
                    if result.get("success"):
                        synced = result.get("synced", 0)
                        failed = result.get("failed", 0)
                        print(f"   ✅ Cloud sync complete: {synced} synced, {failed} failed")
                    else:
                        print(f"   ⚠️  Cloud sync had issues: {result.get('message')}")
                except Exception as e:
                    print(f"   ❌ Cloud sync error: {e}")
            else:
                if not self.cloud_sync.enabled:
                    print("   ⏭️  Cloud sync disabled in config")
                else:
                    print("   📡 System OFFLINE - Will sync when connection restored")
            
            # Step 8: SMS Notification
            print("\n[8/8] SMS Notification")
            if self.sms_notifier.enabled:
                print("   📱 SMS notifications ENABLED")
                parent_phone = student_data.get("parent_phone")
                
                if parent_phone:
                    try:
                        # Prepare message based on scan type
                        if scan_type.value == "time_in":
                            message = f"Good day! {student_name} checked IN at {timestamp}."
                        else:
                            message = f"Good day! {student_name} checked OUT at {timestamp}."
                        
                        # Send SMS
                        print(f"   📞 Sending to: {parent_phone}")
                        print(f"   💬 Message: '{message}'")
                        
                        success = self.sms_notifier.send_sms(parent_phone, message)
                        
                        if success:
                            print("   ✅ SMS sent successfully!")
                        else:
                            print("   ⚠️  SMS send failed (check credentials/connectivity)")
                    except Exception as e:
                        print(f"   ❌ SMS error: {e}")
                else:
                    print("   ⚠️  No parent phone number available")
            else:
                print("   ⏭️  SMS notifications disabled in config")
            
            conn.close()
            
            # Success summary
            print("\n" + "=" * 80)
            print(f"✅ COMPLETE - {student_name} processed successfully")
            print("=" * 80)
            
            return True
            
        except Exception as e:
            print(f"\n❌ Processing failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_simulation(self):
        """Run the complete system simulation"""
        print("\n🚀 Starting Complete Real System Flow Simulation")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        results = {"successful": [], "failed": []}
        
        # Test with real students
        print("\n" + "=" * 80)
        print("TESTING WITH REAL STUDENTS (From Supabase)")
        print("=" * 80)
        
        for student in REAL_STUDENTS:
            success = self.process_attendance(student, is_known=True)
            if success:
                results["successful"].append(student["name"])
            else:
                results["failed"].append(student["name"])
            time.sleep(1)  # Brief pause between scans
        
        # Test with unknown students
        print("\n" + "=" * 80)
        print("TESTING WITH UNKNOWN STUDENTS (Should Fail Lookup)")
        print("=" * 80)
        
        for student in UNKNOWN_STUDENTS:
            success = self.process_attendance(student, is_known=False)
            if not success:  # Expected to fail
                results["failed"].append(student["name"])
        
        # Print summary
        self._print_summary(results)

    def _print_summary(self, results: dict):
        """Print final summary of simulation"""
        total = len(results["successful"]) + len(results["failed"])
        successful = len(results["successful"])
        failed = len(results["failed"])
        
        print("\n" + "=" * 80)
        print("📊 SIMULATION SUMMARY")
        print("=" * 80)
        print()
        print(f"✅ Successful: {successful}/{total}")
        print(f"❌ Failed: {failed}/{total}")
        print()
        
        if results["successful"]:
            print("Successful:")
            for name in results["successful"]:
                print(f"  ✅ {name}")
        
        if results["failed"]:
            print("\nFailed/Unknown:")
            for name in results["failed"]:
                print(f"  ❌ {name}")
        
        # Database status
        print("\n" + "=" * 80)
        print("📈 DATABASE STATUS")
        print("=" * 80)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM students")
        student_count = cursor.fetchone()[0]
        print(f"📚 Students in roster: {student_count}")
        
        cursor.execute("SELECT COUNT(*) FROM attendance")
        attendance_count = cursor.fetchone()[0]
        print(f"📝 Attendance records: {attendance_count}")
        
        cursor.execute("SELECT COUNT(*) FROM sync_queue")
        queue_count = cursor.fetchone()[0]
        print(f"☁️  Records in sync queue: {queue_count}")
        
        # Show recent attendance
        print("\n" + "=" * 80)
        print("📋 RECENT ATTENDANCE RECORDS")
        print("=" * 80)
        
        cursor.execute("""
            SELECT a.id, s.name, a.timestamp, a.scan_type, a.status
            FROM attendance a
            JOIN students s ON a.student_id = s.student_number
            ORDER BY a.id DESC
            LIMIT 10
        """)
        
        for row in cursor.fetchall():
            att_id, name, timestamp, scan_type, status = row
            print(f"ID {att_id:3} | {name:25} | {timestamp} | {scan_type:8} | {status}")
        
        conn.close()
        
        print("\n" + "=" * 80)
        print("🎉 COMPLETE SYSTEM SIMULATION FINISHED!")
        print("=" * 80)


def main():
    """Main entry point"""
    try:
        simulator = CompleteSystemSimulator()
        simulator.run_simulation()
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulation interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
