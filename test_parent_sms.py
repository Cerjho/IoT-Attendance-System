#!/usr/bin/env python3
"""
Test SMS to Parent Number
Quick test to verify SMS delivery to parent's phone
"""

import json
import os
import sys
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.notifications.sms_notifier import SMSNotifier

def test_sms_to_parent(phone_number, student_id="TEST001"):
    """Send a test SMS to parent"""
    
    print("=" * 70)
    print("SMS NOTIFICATION TEST TO PARENT")
    print("=" * 70)
    print(f"Target Phone: {phone_number}")
    print(f"Student ID: {student_id}")
    print("")
    
    # Load config
    with open("config/config.json", "r") as f:
        config = json.load(f)
    
    sms_config = config.get("sms_notifications", {})
    
    # Replace environment variable placeholders
    for key in ["username", "password", "device_id", "api_url"]:
        if key in sms_config and isinstance(sms_config[key], str):
            if sms_config[key].startswith("${") and sms_config[key].endswith("}"):
                env_var = sms_config[key][2:-1]
                sms_config[key] = os.getenv(env_var, sms_config[key])
    
    # Enable SMS for test
    sms_config["enabled"] = True
    
    print("📱 SMS Configuration:")
    print(f"   API URL: {sms_config.get('api_url', 'NOT SET')}")
    print(f"   Username: {sms_config.get('username', 'NOT SET')[:10]}...")
    print(f"   Device ID: {sms_config.get('device_id', 'NOT SET')}")
    print("")
    
    # Initialize SMS notifier
    notifier = SMSNotifier(sms_config)
    
    if not notifier.enabled:
        print("❌ SMS notifications are disabled!")
        return False
    
    # Create test student if not exists
    try:
        conn = sqlite3.connect("data/attendance.db")
        cursor = conn.cursor()
        
        # Check if student exists
        cursor.execute("SELECT student_id, name FROM students WHERE student_id = ?", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            print(f"📝 Creating test student: {student_id}")
            cursor.execute(
                "INSERT OR REPLACE INTO students (student_id, name, parent_phone) VALUES (?, ?, ?)",
                (student_id, "Test Student", phone_number)
            )
            conn.commit()
            student_name = "Test Student"
        else:
            student_name = student[1]
            # Update phone number
            cursor.execute(
                "UPDATE students SET parent_phone = ? WHERE student_id = ?",
                (phone_number, student_id)
            )
            conn.commit()
        
        conn.close()
        print(f"✅ Student ready: {student_name} ({student_id})")
        print(f"   Parent phone updated to: {phone_number}")
        print("")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    # Test 1: Time-in notification
    print("📤 Test 1: Sending TIME-IN notification...")
    print("-" * 70)
    
    result = notifier.send_attendance_notification(
        student_id=student_id,
        student_name=student_name,
        parent_phone=phone_number,
        timestamp=datetime.now(),
        scan_type="time_in",
        status="present"
    )
    
    if result:
        print(f"✅ SMS sent successfully!")
        print(f"   Time-in notification delivered to {phone_number}")
    else:
        print(f"❌ SMS failed!")
        print(f"   Check logs for details")
        return False
    
    print("")
    print("=" * 70)
    print("⏳ Waiting 10 seconds before next test...")
    print("=" * 70)
    print("")
    
    import time
    time.sleep(10)
    
    # Test 2: Time-out notification
    print("📤 Test 2: Sending TIME-OUT notification...")
    print("-" * 70)
    
    result = notifier.send_attendance_notification(
        student_id=student_id,
        student_name=student_name,
        parent_phone=phone_number,
        timestamp=datetime.now(),
        scan_type="time_out",
        status="present"
    )
    
    if result:
        print(f"✅ SMS sent successfully!")
        print(f"   Time-out notification delivered to {phone_number}")
    else:
        print(f"❌ SMS failed!")
        print(f"   Check logs for details")
        return False
    
    print("")
    print("=" * 70)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 70)
    print("")
    print("📱 Please check the phone number for SMS messages:")
    print(f"   {phone_number}")
    print("")
    
    return True

if __name__ == "__main__":
    # Target phone number
    PARENT_PHONE = "+639755269146"
    
    print("")
    print("🚀 Starting SMS test to parent...")
    print("")
    
    success = test_sms_to_parent(PARENT_PHONE)
    
    if success:
        print("🎉 Test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)
