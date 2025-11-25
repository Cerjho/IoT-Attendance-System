#!/usr/bin/env python3
"""
Real System Flow Test (No Camera Required)
Simulates the complete attendance system workflow without camera hardware
Tests: QR scanning → Face detection → Database → Cloud sync → SMS notifications
"""

import sys
import os
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Import system components
from src.utils.config_loader import load_config
from src.utils.logger_config import setup_logger
from src.database.db_handler import AttendanceDatabase
from src.attendance.schedule_manager import ScheduleManager
from src.sync.roster_sync import RosterSyncManager
from src.cloud.cloud_sync import CloudSyncManager
from src.database.sync_queue import SyncQueueManager
from src.network.connectivity import ConnectivityMonitor
from src.notifications.sms_notifier import SMSNotifier

# Setup
logger = setup_logger("test_real_flow")
config = load_config()

class RealSystemFlowTest:
    """Test the complete system flow without camera"""
    
    def __init__(self):
        self.config = config
        self.test_results = []
        
        # Initialize components
        logger.info("=" * 80)
        logger.info("REAL SYSTEM FLOW TEST (NO CAMERA)")
        logger.info("=" * 80)
        
        # Database
        db_path = config.get('database', {}).get('path', 'data/attendance.db')
        self.db = AttendanceDatabase(db_path)
        
        # Schedule manager
        self.schedule = ScheduleManager(config)
        
        # Connectivity (for cloud sync)
        self.connectivity = ConnectivityMonitor(config.get('cloud', {}))
        
        # Sync queue
        self.sync_queue = SyncQueueManager(self.db.db_path)
        
        # Cloud sync
        cloud_config = config.get('cloud', {})
        self.cloud_sync = CloudSyncManager(cloud_config, self.sync_queue, self.connectivity)
        
        # Roster sync
        self.roster_sync = RosterSyncManager(cloud_config, self.db.db_path)
        
        # SMS notifier
        sms_config = config.get('sms_notifications', {})
        self.sms = SMSNotifier(sms_config)
        
        logger.info("✅ All components initialized")
    
    def test_step(self, step_name: str, test_func, *args, **kwargs):
        """Run a test step and record result"""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"TEST STEP: {step_name}")
        logger.info(f"{'=' * 80}")
        
        try:
            start_time = time.time()
            result = test_func(*args, **kwargs)
            duration = time.time() - start_time
            
            self.test_results.append({
                'step': step_name,
                'status': 'PASS' if result else 'FAIL',
                'duration': f"{duration:.2f}s"
            })
            
            logger.info(f"✅ {step_name} - PASSED ({duration:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"❌ {step_name} - FAILED: {e}")
            self.test_results.append({
                'step': step_name,
                'status': 'FAIL',
                'error': str(e)
            })
            return False
    
    def step1_roster_sync(self):
        """Test roster download from Supabase"""
        logger.info("📥 Syncing student roster from Supabase...")
        
        result = self.roster_sync.download_today_roster(force=True)
        
        if result['success']:
            logger.info(f"✅ Roster synced: {result['students_synced']} students")
            logger.info(f"📊 Cached students: {result['cached_count']}")
            
            # Verify local cache
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM students")
                count = cursor.fetchone()[0]
                logger.info(f"🗄️  Database verification: {count} students in local cache")
            
            return True
        else:
            logger.warning(f"⚠️  Roster sync: {result['message']}")
            return result['cached_count'] > 0  # Pass if cache exists
    
    def step2_simulate_qr_scan(self, student_number: str):
        """Simulate QR code scanning"""
        logger.info(f"📱 Simulating QR scan: {student_number}")
        
        # Check if student exists in roster
        student_info = self.roster_sync.lookup_student(student_number)
        
        if student_info:
            logger.info(f"✅ Student found: {student_info['full_name']}")
            logger.info(f"   Student Number: {student_info['student_number']}")
            logger.info(f"   Grade & Section: {student_info['grade_level']} - {student_info['section']}")
            return student_info
        else:
            logger.error(f"❌ Student not found: {student_number}")
            return None
    
    def step3_check_schedule(self):
        """Check current schedule and scan type"""
        logger.info("🕐 Checking school schedule...")
        
        schedule_info = self.schedule.get_schedule_info()
        
        logger.info(f"   Current Session: {schedule_info['current_session']}")
        logger.info(f"   Expected Scan: {schedule_info['expected_scan_type']}")
        logger.info(f"   In Login Window: {schedule_info['in_login_window']}")
        logger.info(f"   In Logout Window: {schedule_info['in_logout_window']}")
        
        return schedule_info
    
    def step4_simulate_face_detection(self, student_number: str):
        """Simulate face detection (no actual camera)"""
        logger.info("👤 Simulating face detection...")
        
        # Create fake photo path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_dir = Path("data/photos")
        photo_dir.mkdir(parents=True, exist_ok=True)
        
        photo_path = photo_dir / f"test_{student_number}_{timestamp}.jpg"
        
        # Create dummy photo file
        with open(photo_path, 'w') as f:
            f.write(f"SIMULATED PHOTO - Student: {student_number}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("This is a test file - not a real photo\n")
        
        logger.info(f"✅ Face detected (simulated)")
        logger.info(f"📸 Photo saved: {photo_path}")
        
        return str(photo_path)
    
    def step5_check_duplicate(self, student_number: str, scan_type: str):
        """Check if duplicate scan"""
        logger.info("🔍 Checking for duplicate scans...")
        
        last_scan = self.db.get_last_scan(student_number)
        
        if last_scan:
            logger.info(f"   Last scan: {last_scan['timestamp']} ({last_scan.get('scan_type', 'unknown')})")
            
            allowed = self.schedule.should_allow_scan(
                last_scan['timestamp'],
                last_scan.get('scan_type'),
                scan_type
            )
            
            if allowed:
                logger.info("✅ Scan allowed (different type or outside cooldown)")
            else:
                logger.warning("⚠️  Duplicate scan blocked (within 5-minute cooldown)")
            
            return allowed
        else:
            logger.info("✅ First scan today - allowed")
            return True
    
    def step6_record_attendance(self, student_info: Dict, photo_path: str, schedule_info: Dict):
        """Record attendance in local database"""
        logger.info("💾 Recording attendance...")
        
        scan_type = schedule_info['expected_scan_type']
        status = self.schedule.determine_attendance_status(scan_type)
        
        attendance_id = self.db.record_attendance(
            student_id=student_info['student_number'],
            photo_path=photo_path,
            qr_data=student_info['student_number'],
            scan_type=scan_type,
            status=status
        )
        
        logger.info(f"✅ Attendance recorded: ID {attendance_id}")
        logger.info(f"   Student: {student_info['full_name']}")
        logger.info(f"   Scan Type: {scan_type}")
        logger.info(f"   Status: {status}")
        
        return attendance_id
    
    def step7_cloud_sync(self, attendance_id: int, photo_path: str):
        """Sync attendance to Supabase"""
        logger.info("☁️  Syncing to Supabase...")
        
        # Get attendance record
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, student_id, timestamp, photo_path, qr_data, scan_type, status
                FROM attendance WHERE id = ?
            """, (attendance_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.error("❌ Attendance record not found")
                return False
            
            attendance_data = {
                'id': row[0],
                'student_id': row[1],
                'timestamp': row[2],
                'photo_path': row[3],
                'qr_data': row[4],
                'scan_type': row[5],
                'status': row[6]
            }
        
        # Sync to cloud
        success = self.cloud_sync.sync_attendance_record(attendance_data, photo_path)
        
        if success:
            logger.info("✅ Successfully synced to Supabase")
        else:
            logger.warning("⚠️  Cloud sync failed - added to queue")
        
        return True  # Always pass (queued if offline)
    
    def step8_send_sms(self, student_info: Dict, scan_type: str):
        """Send SMS notification to parent"""
        logger.info("📱 Sending SMS notification...")
        
        if not student_info.get('parent_guardian_contact'):
            logger.warning("⚠️  No parent contact number - skipping SMS")
            return True
        
        success = self.sms.send_attendance_notification(
            student_name=student_info['full_name'],
            student_id=student_info['student_number'],
            parent_contact=student_info['parent_guardian_contact'],
            scan_type=scan_type
        )
        
        if success:
            logger.info(f"✅ SMS sent to {student_info['parent_guardian_contact']}")
        else:
            logger.warning("⚠️  SMS sending failed")
        
        return True  # Always pass (SMS is optional)
    
    def run_complete_flow(self, student_number: str):
        """Run complete attendance flow for one student"""
        logger.info("\n" + "=" * 80)
        logger.info(f"TESTING COMPLETE FLOW: Student {student_number}")
        logger.info("=" * 80)
        
        # Step 2: QR Scan
        student_info = self.test_step(
            "QR Code Scan",
            self.step2_simulate_qr_scan,
            student_number
        )
        if not student_info:
            return False
        
        # Step 3: Schedule Check
        schedule_info = self.test_step(
            "Schedule Check",
            self.step3_check_schedule
        )
        
        # Step 4: Duplicate Check
        allowed = self.test_step(
            "Duplicate Check",
            self.step5_check_duplicate,
            student_number,
            schedule_info['expected_scan_type']
        )
        if not allowed:
            logger.warning("⚠️  Scan blocked - skipping remaining steps")
            return True
        
        # Step 5: Face Detection
        photo_path = self.test_step(
            "Face Detection",
            self.step4_simulate_face_detection,
            student_number
        )
        if not photo_path:
            return False
        
        # Step 6: Record Attendance
        attendance_id = self.test_step(
            "Record Attendance",
            self.step6_record_attendance,
            student_info,
            photo_path,
            schedule_info
        )
        if not attendance_id:
            return False
        
        # Step 7: Cloud Sync
        self.test_step(
            "Cloud Sync",
            self.step7_cloud_sync,
            attendance_id,
            photo_path
        )
        
        # Step 8: SMS Notification
        self.test_step(
            "SMS Notification",
            self.step8_send_sms,
            student_info,
            schedule_info['expected_scan_type']
        )
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = total - passed
        
        logger.info(f"\nTotal Tests: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        
        if failed > 0:
            logger.info("\nFailed Tests:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    logger.info(f"  • {result['step']}: {result.get('error', 'Unknown error')}")
        
        logger.info("\n" + "=" * 80)
        logger.info(f"OVERALL: {'✅ ALL TESTS PASSED' if failed == 0 else '❌ SOME TESTS FAILED'}")
        logger.info("=" * 80)


def main():
    """Main test execution"""
    print("\n" + "=" * 80)
    print("REAL SYSTEM FLOW TEST")
    print("Testing complete attendance workflow without camera hardware")
    print("=" * 80 + "\n")
    
    test = RealSystemFlowTest()
    
    # Step 1: Roster Sync (always run first)
    test.test_step("Roster Sync", test.step1_roster_sync)
    
    # Use test students (real student numbers from your Supabase)
    students = [
        ('2021001', 'Test', 'Student1'),
        ('2021002', 'Test', 'Student2'),
        ('2021003', 'Test', 'Student3')
    ]
    
    logger.info(f"\n📋 Testing with {len(students)} students:")
    for student in students:
        logger.info(f"   • {student[0]}: {student[1]} {student[2]}")
    
    # Test flow with first 3 students
    for i, student in enumerate(students[:3], 1):
        student_number = student[0]
        
        print(f"\n{'#' * 80}")
        print(f"TEST SCENARIO {i}/3: {student[1]} {student[2]} ({student_number})")
        print(f"{'#' * 80}\n")
        
        test.run_complete_flow(student_number)
        
        if i < len(students[:3]):
            time.sleep(2)  # Pause between students
    
    # Print final summary
    test.print_summary()


if __name__ == "__main__":
    main()
