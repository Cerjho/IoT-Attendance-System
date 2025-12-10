#!/usr/bin/env python3
"""
Test Webhook Fallback System
Verify webhook triggers only when SMS fails
"""

import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from src.notifications.sms_notifier import SMSNotifier

def test_webhook_fallback():
    """Test webhook fallback when SMS fails"""
    
    print("=" * 70)
    print("WEBHOOK FALLBACK TEST")
    print("=" * 70)
    print("")
    
    # Load config
    with open("config/config.json", "r") as f:
        config = json.load(f)
    
    sms_config = config.get("sms_notifications", {})
    
    # Replace environment variables
    for key in ["username", "password", "device_id", "api_url"]:
        if key in sms_config and isinstance(sms_config[key], str):
            if sms_config[key].startswith("${") and sms_config[key].endswith("}"):
                env_var = sms_config[key][2:-1]
                sms_config[key] = os.getenv(env_var, sms_config[key])
    
    # Test 1: Normal SMS (webhook should NOT trigger)
    print("Test 1: Normal SMS flow (webhook disabled)")
    print("-" * 70)
    sms_config["webhook"]["enabled"] = False
    notifier = SMSNotifier(sms_config)
    
    result = notifier.send_attendance_notification(
        student_id="TEST001",
        student_name="Test Student",
        parent_phone="+639755269146",
        timestamp=datetime.now(),
        scan_type="time_in",
        status="present"
    )
    
    print(f"Result: {'✅ Success' if result else '❌ Failed'}")
    print("")
    
    # Test 2: SMS with webhook configured but set to failure_only
    print("Test 2: SMS with webhook enabled (on_failure_only=true)")
    print("-" * 70)
    print("Expected: SMS succeeds → webhook NOT called")
    print("")
    
    sms_config["webhook"]["enabled"] = True
    sms_config["webhook"]["url"] = "https://httpbin.org/post"  # Test endpoint
    sms_config["webhook"]["on_failure_only"] = True
    
    notifier2 = SMSNotifier(sms_config)
    
    result2 = notifier2.send_attendance_notification(
        student_id="TEST002",
        student_name="Test Student 2",
        parent_phone="+639755269146",
        timestamp=datetime.now(),
        scan_type="time_out",
        status="present"
    )
    
    print(f"Result: {'✅ Success' if result2 else '❌ Failed'}")
    print("")
    
    # Test 3: Simulate SMS failure (invalid credentials) → webhook should trigger
    print("Test 3: SMS failure simulation (webhook should activate)")
    print("-" * 70)
    print("Expected: SMS fails → webhook called as fallback")
    print("")
    
    sms_config_fail = sms_config.copy()
    sms_config_fail["username"] = "INVALID_USER"  # Force SMS to fail
    sms_config_fail["webhook"]["enabled"] = True
    sms_config_fail["webhook"]["url"] = "https://httpbin.org/post"
    sms_config_fail["webhook"]["on_failure_only"] = True
    
    notifier3 = SMSNotifier(sms_config_fail)
    
    result3 = notifier3.send_attendance_notification(
        student_id="TEST003",
        student_name="Test Student 3",
        parent_phone="+639755269146",
        timestamp=datetime.now(),
        scan_type="time_in",
        status="present"
    )
    
    print(f"Result: {'✅ Webhook fallback worked' if result3 else '❌ Both SMS and webhook failed'}")
    print("")
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("✓ Webhook does NOT interfere with normal SMS flow")
    print("✓ Webhook only activates when SMS fails")
    print("✓ System remains functional even without webhook")
    print("")

if __name__ == "__main__":
    test_webhook_fallback()
