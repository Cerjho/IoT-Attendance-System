#!/usr/bin/env python3
"""
Real Flow Test - Simulates complete attendance system without camera hardware
Tests the actual workflow: QR scan → Face detection → Photo → Database → Cloud sync → SMS
"""

import sys
import os
import time
from datetime import datetime
import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.database.db_handler import AttendanceDatabase
from src.notifications.sms_notifier import SMSNotifier
from src.attendance.schedule_manager import ScheduleManager
from src.sync.roster_sync import RosterSyncManager
from src.utils.config_loader import load_config
from src.utils.logger_config import setup_logger

logger = setup_logger('test_real_flow')


class RealFlowSimulator:
    """Simulates real attendance flow without camera hardware"""
    
    def __init__(self):
        self.config = load_config()
        self.db = AttendanceDatabase()
        self.sms_notifier = SMSNotifier(self.config.get('sms_notifications', {}))
        self.schedule_mgr = ScheduleManager(self.config.get('school_schedule', {}))
        self.roster_sync = RosterSyncManager(self.config.get('cloud', {}))
        
        # Sync roster from cloud
        print("\n" + "="*70)
        print("INITIALIZING SYSTEM")
        print("="*70)
        self._sync_roster()
        
    def _sync_roster(self):
        """Sync student roster from Supabase"""
        print("\n📋 Syncing roster from Supabase...")
        try:
            result = self.roster_sync.sync_roster()
            if result['success']:
                print(f"✅ Roster synced: {result['students_synced']} students")
                
                # Show roster
                students = self.db.get_all_students()
                if students:
                    print("\n👥 STUDENT ROSTER:")
                    print("-" * 70)
                    for student in students[:10]:  # Show first 10
                        print(f"   {student['student_number']}: {student['first_name']} {student['last_name']}")
                    if len(students) > 10:
                        print(f"   ... and {len(students) - 10} more students")
                    print("-" * 70)
                else:
                    print("⚠️  No students in roster")
            else:
                print(f"⚠️  Roster sync failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"❌ Roster sync error: {e}")
    
    def _generate_fake_photo(self, student_id):
        """Generate a fake photo (colored image with student ID)"""
        # Create a 640x480 image with random color
        img = np.random.randint(50, 150, (480, 640, 3), dtype=np.uint8)
        
        # Add student ID text
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"Student: {student_id}"
        text_size = cv2.getTextSize(text, font, 1.5, 3)[0]
        text_x = (640 - text_size[0]) // 2
        text_y = (480 + text_size[1]) // 2
        
        # Draw text with background
        cv2.rectangle(img, (text_x - 10, text_y - text_size[1] - 10),
                     (text_x + text_size[0] + 10, text_y + 10),
                     (255, 255, 255), -1)
        cv2.putText(img, text, (text_x, text_y), font, 1.5, (0, 0, 0), 3)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(img, timestamp, (10, 450), font, 0.7, (255, 255, 255), 2)
        
        return img
    
    def _save_photo(self, student_id, img):
        """Save photo to disk"""
        os.makedirs("data/photos", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/photos/test_attendance_{student_id}_{timestamp}.jpg"
        cv2.imwrite(filename, img)
        return filename
    
    def _check_duplicate(self, student_id, current_scan_type):
        """Check if this is a duplicate scan"""
        last_scan = self.db.get_last_scan(student_id)
        
        if not last_scan:
            return False, None
        
        # Use schedule manager to check
        allowed = self.schedule_mgr.should_allow_scan(
            last_scan_time=last_scan.get('timestamp'),
            last_scan_type=last_scan.get('scan_type'),
            current_scan_type=current_scan_type
        )
        
        return not allowed, last_scan
    
    def simulate_attendance(self, student_id):
        """Simulate complete attendance workflow for one student"""
        print("\n" + "="*70)
        print(f"SIMULATING ATTENDANCE WORKFLOW")
        print("="*70)
        
        # Step 1: QR Code Scan
        print(f"\n📱 STEP 1: QR CODE SCANNED")
        print(f"   Student ID: {student_id}")
        time.sleep(0.5)
        
        # Get student info from database
        student = self.db.get_student_by_number(student_id)
        if not student:
            print(f"   ❌ Student {student_id} not found in roster!")
            print(f"   💡 Make sure the student exists in Supabase")
            return False
        
        student_name = f"{student['first_name']} {student['last_name']}"
        print(f"   ✅ Student found: {student_name}")
        
        # Step 2: Determine scan type
        print(f"\n⏰ STEP 2: SCHEDULE CHECK")
        schedule_info = self.schedule_mgr.get_schedule_info()
        scan_type = schedule_info['expected_scan_type']
        session = schedule_info['current_session']
        status = schedule_info['attendance_status']
        
        print(f"   Current time: {schedule_info['current_time']}")
        print(f"   Session: {session}")
        print(f"   Scan type: {scan_type}")
        print(f"   Status: {status}")
        time.sleep(0.5)
        
        # Step 3: Check for duplicates
        print(f"\n🔍 STEP 3: DUPLICATE CHECK")
        is_duplicate, last_scan = self._check_duplicate(student_id, scan_type)
        
        if is_duplicate:
            print(f"   ⚠️  DUPLICATE DETECTED!")
            print(f"   Last scan: {last_scan['timestamp']} ({last_scan['scan_type']})")
            print(f"   ❌ Scan blocked (within 5-minute cooldown)")
            return False
        else:
            print(f"   ✅ No duplicate - scan allowed")
        time.sleep(0.5)
        
        # Step 4: Face Detection (simulated)
        print(f"\n👤 STEP 4: FACE DETECTION")
        print(f"   Waiting for face... (simulated 2 second window)")
        time.sleep(1)
        print(f"   ✅ Face detected!")
        time.sleep(0.5)
        
        # Step 5: Photo Capture
        print(f"\n📸 STEP 5: PHOTO CAPTURE")
        print(f"   Generating simulated photo...")
        img = self._generate_fake_photo(student_id)
        photo_path = self._save_photo(student_id, img)
        print(f"   ✅ Photo saved: {photo_path}")
        time.sleep(0.5)
        
        # Step 6: Database Recording
        print(f"\n💾 STEP 6: DATABASE RECORDING")
        attendance_data = {
            'student_id': student_id,
            'qr_data': student_id,
            'photo_path': photo_path,
            'scan_type': scan_type,
            'status': status
        }
        
        try:
            self.db.record_attendance(attendance_data)
            print(f"   ✅ Attendance recorded in local database")
            print(f"      - Scan type: {scan_type}")
            print(f"      - Status: {status}")
        except Exception as e:
            print(f"   ❌ Database error: {e}")
            return False
        time.sleep(0.5)
        
        # Step 7: Cloud Sync
        print(f"\n☁️  STEP 7: CLOUD SYNC")
        print(f"   Syncing to Supabase...")
        try:
            # Use roster_sync to sync attendance data
            import requests
            
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                print(f"   ⚠️  Cloud credentials not configured")
            else:
                # Get the student's UUID
                response = requests.get(
                    f"{supabase_url}/rest/v1/students",
                    headers={
                        'apikey': supabase_key,
                        'Authorization': f'Bearer {supabase_key}',
                        'Content-Type': 'application/json'
                    },
                    params={'student_number': f'eq.{student_id}'}
                )
                
                if response.status_code == 200 and response.json():
                    student_uuid = response.json()[0]['id']
                    
                    # Prepare attendance data
                    cloud_data = {
                        'student_id': student_uuid,
                        'date': datetime.now().date().isoformat(),
                        'device_id': os.getenv('DEVICE_ID', 'device_001')
                    }
                    
                    if scan_type == 'time_in':
                        cloud_data['time_in'] = datetime.now().time().isoformat()
                    else:
                        cloud_data['time_out'] = datetime.now().time().isoformat()
                    
                    # Send to Supabase
                    sync_response = requests.post(
                        f"{supabase_url}/rest/v1/attendance",
                        headers={
                            'apikey': supabase_key,
                            'Authorization': f'Bearer {supabase_key}',
                            'Content-Type': 'application/json',
                            'Prefer': 'return=minimal'
                        },
                        json=cloud_data
                    )
                    
                    if sync_response.status_code in [200, 201]:
                        print(f"   ✅ Synced to cloud successfully")
                        # Update local record as synced
                        self.db.mark_as_synced(student_id)
                    else:
                        print(f"   ⚠️  Cloud sync failed: {sync_response.status_code}")
                else:
                    print(f"   ⚠️  Student UUID not found in cloud")
        except Exception as e:
            print(f"   ⚠️  Cloud sync error: {e}")
            print(f"   💡 Record saved locally, will sync later")
        time.sleep(0.5)
        
        # Step 8: SMS Notification
        print(f"\n📧 STEP 8: SMS NOTIFICATION")
        if student.get('parent_guardian_contact'):
            print(f"   Sending SMS to: {student['parent_guardian_contact']}")
            try:
                # Get the appropriate message template
                if scan_type == 'time_in':
                    template = self.sms_notifier.login_message_template
                    action = "checked IN"
                else:
                    template = self.sms_notifier.logout_message_template
                    action = "checked OUT"
                
                message = template.format(
                    student_name=student_name,
                    student_id=student_id,
                    time=datetime.now().strftime("%I:%M %p"),
                    date=datetime.now().strftime("%B %d, %Y")
                )
                
                print(f"\n   📱 SMS Preview:")
                print(f"   {'-'*66}")
                print(f"   To: {student['parent_guardian_contact']}")
                print(f"   Message: {message[:100]}...")
                print(f"   {'-'*66}")
                
                # Actually send SMS
                sms_result = self.sms_notifier.send_attendance_notification(
                    student_id=student_id,
                    student_name=student_name,
                    parent_contact=student['parent_guardian_contact'],
                    scan_type=scan_type
                )
                
                if sms_result['success']:
                    print(f"   ✅ SMS sent successfully!")
                else:
                    print(f"   ⚠️  SMS failed: {sms_result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"   ⚠️  SMS error: {e}")
        else:
            print(f"   ⚠️  No parent contact number in roster")
        
        # Step 9: Success
        print(f"\n✅ WORKFLOW COMPLETE")
        print(f"   Student: {student_name} ({student_id})")
        print(f"   Action: {scan_type.upper().replace('_', ' ')}")
        print(f"   Status: {status.upper()}")
        print(f"   Photo: {photo_path}")
        
        return True
    
    def show_statistics(self):
        """Show attendance statistics"""
        print("\n" + "="*70)
        print("ATTENDANCE STATISTICS")
        print("="*70)
        
        today_records = self.db.get_today_attendance()
        print(f"\n📊 Today's Records: {len(today_records)}")
        
        if today_records:
            time_in_count = sum(1 for r in today_records if r.get('scan_type') == 'time_in')
            time_out_count = sum(1 for r in today_records if r.get('scan_type') == 'time_out')
            present_count = sum(1 for r in today_records if r.get('status') == 'present')
            late_count = sum(1 for r in today_records if r.get('status') == 'late')
            
            print(f"\n   Time In:  {time_in_count}")
            print(f"   Time Out: {time_out_count}")
            print(f"   Present:  {present_count}")
            print(f"   Late:     {late_count}")
            
            print(f"\n📋 Recent Records:")
            print("-" * 70)
            for record in today_records[-5:]:  # Last 5 records
                timestamp = datetime.fromisoformat(record['timestamp']).strftime("%I:%M %p")
                scan_type = record.get('scan_type', 'N/A').replace('_', ' ').title()
                status = record.get('status', 'N/A').title()
                print(f"   {timestamp} - {record['student_id']} - {scan_type} - {status}")
            print("-" * 70)


def main():
    """Run real flow test"""
    print("\n" + "="*70)
    print("IoT ATTENDANCE SYSTEM - REAL FLOW TEST")
    print("Camera Hardware: DISABLED (using simulation)")
    print("="*70)
    
    simulator = RealFlowSimulator()
    
    # Interactive mode
    print("\n" + "="*70)
    print("INTERACTIVE TEST MODE")
    print("="*70)
    print("\nOptions:")
    print("  1. Enter student ID to simulate scan")
    print("  2. Type 'stats' to view statistics")
    print("  3. Type 'auto' for automatic demo")
    print("  4. Type 'quit' to exit")
    print("\nExample student IDs from your roster will be shown above")
    
    while True:
        try:
            print("\n" + "-"*70)
            user_input = input("\n👉 Enter command or student ID: ").strip()
            
            if user_input.lower() == 'quit':
                print("\n👋 Exiting test mode")
                break
            
            elif user_input.lower() == 'stats':
                simulator.show_statistics()
            
            elif user_input.lower() == 'auto':
                print("\n🤖 AUTOMATIC DEMO MODE")
                students = simulator.db.get_all_students()
                if not students:
                    print("❌ No students in roster!")
                    continue
                
                # Test with first 3 students
                for i, student in enumerate(students[:3], 1):
                    print(f"\n[Demo {i}/3]")
                    simulator.simulate_attendance(student['student_number'])
                    if i < 3:
                        print("\n⏳ Waiting 2 seconds...")
                        time.sleep(2)
                
                simulator.show_statistics()
            
            elif user_input:
                # Treat as student ID
                simulator.simulate_attendance(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            logger.exception("Test error")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
