#!/usr/bin/env python3
"""
Test SMS Message with Real Student Data
This script allows you to test the SMS notification system with a real phone number.
"""

import sqlite3
import sys
from datetime import datetime

def update_phone_number(student_id, phone_number):
    """Update student's parent phone number"""
    conn = sqlite3.connect('data/attendance.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE students 
        SET parent_phone = ? 
        WHERE student_id = ?
    """, (phone_number, student_id))
    
    conn.commit()
    conn.close()
    print(f"✅ Updated phone number for student {student_id} to {phone_number}")

def get_student_info(student_id):
    """Get student information"""
    conn = sqlite3.connect('data/attendance.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT student_id, name, parent_phone, 
               (SELECT COUNT(*) FROM attendance WHERE student_id = ?) as attendance_count
        FROM students 
        WHERE student_id = ?
    """, (student_id, student_id))
    
    result = cursor.fetchone()
    conn.close()
    return result

def send_test_sms(student_id):
    """Send test SMS notification"""
    try:
        from src.notifications.sms_notifier import SMSNotifier
        import json
        import os
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        with open('config/config.json', 'r') as f:
            config = json.load(f)
        
        sms_config = config.get('sms_notifications', {})
        
        # Replace environment variable placeholders
        if 'username' in sms_config and isinstance(sms_config['username'], str):
            if sms_config['username'].startswith('${') and sms_config['username'].endswith('}'):
                env_var = sms_config['username'][2:-1]
                sms_config['username'] = os.getenv(env_var, sms_config['username'])
        
        if 'password' in sms_config and isinstance(sms_config['password'], str):
            if sms_config['password'].startswith('${') and sms_config['password'].endswith('}'):
                env_var = sms_config['password'][2:-1]
                sms_config['password'] = os.getenv(env_var, sms_config['password'])
        
        if 'device_id' in sms_config and isinstance(sms_config['device_id'], str):
            if sms_config['device_id'].startswith('${') and sms_config['device_id'].endswith('}'):
                env_var = sms_config['device_id'][2:-1]
                sms_config['device_id'] = os.getenv(env_var, sms_config['device_id'])
        
        if 'api_url' in sms_config and isinstance(sms_config['api_url'], str):
            if sms_config['api_url'].startswith('${') and sms_config['api_url'].endswith('}'):
                env_var = sms_config['api_url'][2:-1]
                sms_config['api_url'] = os.getenv(env_var, sms_config['api_url'])
        
        if not sms_config.get('enabled', False):
            print("❌ SMS notifications are disabled in config.json")
            print("   Enable SMS in config/config.json: 'sms' -> 'enabled': true")
            return False
        
        # Get student info
        student_info = get_student_info(student_id)
        if not student_info:
            print(f"❌ Student {student_id} not found")
            return False
        
        sid, name, phone, count = student_info
        
        if not phone:
            print(f"❌ No phone number set for student {student_id}")
            return False
        
        print(f"\n📱 Preparing to send SMS...")
        print(f"   Student: {name} ({sid})")
        print(f"   Phone: {phone}")
        print(f"   Records: {count}")
        
        # Initialize SMS notifier with config
        sms = SMSNotifier(sms_config)
        
        if not sms.enabled:
            print("\n❌ SMS notifier could not be initialized")
            print("   Check your .env file has:")
            print("   - SMS_USERNAME")
            print("   - SMS_PASSWORD") 
            print("   - SMS_DEVICE_ID")
            return False
        
        # Send notification using the proper method
        success = sms.send_attendance_notification(
            student_id=sid,
            student_name=name,
            parent_phone=phone,
            timestamp=datetime.now(),
            scan_type='time_in'
        )
        
        if success:
            print("\n✅ SMS sent successfully!")
            
            # Get attendance URL
            public_url = config.get('public_attendance_url', 'https://cerjho.github.io/IoT-Attendance-System/view-attendance.html')
            attendance_url = f"{public_url}?student_id={sid}"
            
            print(f"\n📱 Message content:")
            print("─" * 70)
            time_str = datetime.now().strftime('%I:%M %p')
            date_str = datetime.now().strftime('%B %d, %Y')
            print(f"Good day! {name} (ID: {sid}) checked IN at {time_str} on {date_str}.")
            if attendance_url:
                print(f"\nView attendance: {attendance_url}")
            print("─" * 70)
        else:
            print("\n❌ Failed to send SMS")
            print("   Possible issues:")
            print("   1. Check SMS gateway credentials in .env")
            print("   2. Check device_id is correct")
            print("   3. Check internet connection")
            print("   4. Check SMS gateway service is running")
        
        return success
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 70)
    print("📱 SMS MESSAGE TESTER")
    print("=" * 70)
    
    # Default test student
    student_id = '2021001'
    
    # Check current student info
    student_info = get_student_info(student_id)
    
    if student_info:
        sid, name, phone, count = student_info
        print(f"\n📋 Current Student Info:")
        print(f"  Student ID: {sid}")
        print(f"  Name: {name}")
        print(f"  Parent Phone: {phone or '(not set)'}")
        print(f"  Attendance Records: {count}")
    else:
        print(f"❌ Student {student_id} not found")
        return
    
    print("\n" + "=" * 70)
    print("OPTIONS:")
    print("=" * 70)
    print("1. Update phone number")
    print("2. Send test SMS (requires configured SMS gateway)")
    print("3. Show SMS message preview")
    print("4. View attendance page URL")
    print("5. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            phone = input("Enter phone number (e.g., 09123456789): ").strip()
            if phone:
                update_phone_number(student_id, phone)
                student_info = get_student_info(student_id)
                if student_info:
                    print(f"✅ Phone updated. Current: {student_info[2]}")
            else:
                print("❌ Invalid phone number")
        
        elif choice == '2':
            student_info = get_student_info(student_id)
            if student_info and student_info[2]:
                confirm = input(f"Send SMS to {student_info[2]}? (y/n): ").strip().lower()
                if confirm == 'y':
                    send_test_sms(student_id)
            else:
                print("❌ Please set a phone number first (Option 1)")
        
        elif choice == '3':
            import json
            with open('config/config.json', 'r') as f:
                config = json.load(f)
            
            url = config.get('public_attendance_url', 'https://cerjho.github.io/IoT-Attendance-System/view-attendance.html')
            attendance_url = f"{url}?student_id={student_id}"
            
            student_info = get_student_info(student_id)
            if student_info:
                name = student_info[1]
                time_str = datetime.now().strftime('%I:%M %p')
                
                message = f"""Good morning! {name} has arrived at school at {time_str}.

View attendance: {attendance_url}"""
                
                print("\n" + "=" * 70)
                print("📱 SMS MESSAGE PREVIEW:")
                print("=" * 70)
                print(message)
        
        elif choice == '4':
            import json
            with open('config/config.json', 'r') as f:
                config = json.load(f)
            
            url = config.get('public_attendance_url', 'https://cerjho.github.io/IoT-Attendance-System/view-attendance.html')
            attendance_url = f"{url}?student_id={student_id}"
            
            print("\n" + "=" * 70)
            print("🔗 ATTENDANCE PAGE URL:")
            print("=" * 70)
            print(attendance_url)
            print("\n💡 You can open this URL in your browser to test the page")
            print("   (GitHub Pages must be enabled first)")
        
        elif choice == '5':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-5.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
