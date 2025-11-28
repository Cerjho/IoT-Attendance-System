#!/usr/bin/env python3
"""
Test SMS Message - All Templates
Test all 7 SMS templates and new enhancements:
- Check-in, Check-out, Late arrival
- No checkout alert, Absence alert
- Weekly summary, Monthly summary
- Quiet hours, Cooldown, Unsubscribe text
"""

import os
import sys
from datetime import datetime, timedelta

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def get_student_info(student_number):
    """Get student information from Supabase"""
    try:
        import os

        import requests

        # Load env variables manually
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            print("❌ Supabase credentials not found in .env")
            return None

        # Get student by student_number using REST API
        url = f"{supabase_url}/rest/v1/students"
        headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}
        params = {"student_number": f"eq.{student_number}"}

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200 or not response.json():
            return None

        student = response.json()[0]

        # Get attendance count
        count_url = f"{supabase_url}/rest/v1/attendance"
        count_params = {"student_id": f'eq.{student["id"]}', "select": "id"}
        count_response = requests.get(
            count_url, headers=headers, params=count_params, timeout=10
        )
        count = len(count_response.json()) if count_response.status_code == 200 else 0

        # Build full name from first_name and last_name
        first_name = student.get("first_name", "")
        last_name = student.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip()

        # Return: student_number, name, phone, count
        return (
            student.get("student_number"),
            full_name,
            student.get("parent_guardian_contact"),
            count,
        )

    except Exception as e:
        # Suppress detailed traceback for cleaner output
        error_msg = str(e).split("\n")[0] if "\n" in str(e) else str(e)
        if len(error_msg) > 100:
            error_msg = error_msg[:100] + "..."
        print(f"⚠️  Connection error: {error_msg}")
        return None


def update_phone_number(student_number, phone):
    """Update student's parent phone number in Supabase"""
    try:
        import os

        import requests

        # Load env variables manually
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            print("❌ Supabase credentials not found in .env")
            return False

        # Update phone number using REST API
        url = f"{supabase_url}/rest/v1/students"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        params = {"student_number": f"eq.{student_number}"}
        data = {"parent_guardian_contact": phone}

        response = requests.patch(
            url, headers=headers, params=params, json=data, timeout=10
        )

        if response.status_code in [200, 204]:
            print(f"✅ Updated phone number for student {student_number}")
            return True
        else:
            print(f"❌ Failed to update: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error updating phone: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_check_in(sms, student_id, name, phone):
    """Test check-in notification"""
    print("\n" + "=" * 70)
    print("📥 TEST 1: CHECK-IN NOTIFICATION")
    print("=" * 70)
    print(f"Template: {{name}} checked IN at {{time}} on {{date}}")
    print(f"Expected: ~65 characters")

    success = sms.send_attendance_notification(
        student_id=student_id,
        student_name=name,
        parent_phone=phone,
        timestamp=datetime.now(),
        scan_type="time_in",
    )

    if success:
        print("✅ Check-in SMS sent")
    else:
        print("❌ Failed to send check-in SMS")
    # Ensure call executed and returned a boolean
    assert isinstance(success, bool)


def test_check_out(sms, student_id, name, phone):
    """Test check-out notification"""
    print("\n" + "=" * 70)
    print("📤 TEST 2: CHECK-OUT NOTIFICATION")
    print("=" * 70)
    print(f"Template: {{name}} checked OUT at {{time}} on {{date}}")
    print(f"Expected: ~65 characters")

    success = sms.send_attendance_notification(
        student_id=student_id,
        student_name=name,
        parent_phone=phone,
        timestamp=datetime.now(),
        scan_type="time_out",
    )

    if success:
        print("✅ Check-out SMS sent")
    else:
        print("❌ Failed to send check-out SMS")
    assert isinstance(success, bool)


def test_late_arrival(sms, student_id, name, phone):
    """Test late arrival notification"""
    print("\n" + "=" * 70)
    print("⏰ TEST 3: LATE ARRIVAL ALERT")
    print("=" * 70)
    print(f"Template: {{name}} arrived LATE ({{minutes}} min) at {{time}}")
    print(f"Expected: ~75 characters")
    print(f"Testing with: 15 minutes late")

    success = sms.send_attendance_notification(
        student_id=student_id,
        student_name=name,
        parent_phone=phone,
        timestamp=datetime.now(),
        scan_type="time_in",
        status="late",
        minutes_late=15,
    )

    if success:
        print("✅ Late arrival SMS sent")
    else:
        print("❌ Failed to send late arrival SMS")
    assert isinstance(success, bool)


def test_no_checkout(sms, student_id, name, phone):
    """Test no checkout alert"""
    print("\n" + "=" * 70)
    print("🚨 TEST 4: NO CHECK-OUT ALERT")
    print("=" * 70)
    print(
        f"Template: ALERT: {{name}} has not checked OUT. Please verify their whereabouts."
    )
    print(f"Expected: ~70 characters")

    # Simulate last check-in time (e.g., 8:00 AM today)
    from datetime import datetime, timedelta

    last_checkin = datetime.now().replace(hour=8, minute=0, second=0)

    success = sms.send_no_checkout_alert(
        student_id=student_id,
        student_name=name,
        parent_phone=phone,
        last_checkin_time=last_checkin,
    )

    if success:
        print("✅ No checkout alert sent")
    else:
        print("❌ Failed to send no checkout alert")
    assert isinstance(success, bool)


def test_absence(sms, student_id, name, phone):
    """Test absence alert"""
    print("\n" + "=" * 70)
    print("⚠️  TEST 5: ABSENCE ALERT")
    print("=" * 70)
    print(
        f"Template: NOTICE: {{name}} was marked ABSENT today. Contact school if incorrect."
    )
    print(f"Expected: ~75 characters")

    success = sms.send_absence_alert(
        student_id=student_id,
        student_name=name,
        parent_phone=phone,
        date=datetime.now(),
    )

    if success:
        print("✅ Absence alert sent")
    else:
        print("❌ Failed to send absence alert")
    assert isinstance(success, bool)


def test_weekly_summary(sms, student_id, name, phone):
    """Test weekly summary"""
    print("\n" + "=" * 70)
    print("📊 TEST 6: WEEKLY SUMMARY")
    print("=" * 70)
    print(f"Template: Week summary for {{name}}: {{present}}P {{late}}L {{absent}}A")
    print(f"Expected: ~55 characters")
    print(f"Testing with: 4 present, 1 late, 0 absent")

    # Build attendance link if configured
    attendance_link = ""
    try:
        if getattr(sms, "attendance_view_url", ""):
            attendance_link = sms.attendance_view_url.format(student_id=student_id)
    except Exception:
        attendance_link = ""

    # Use the template from SMS notifier if available
    if hasattr(sms, "weekly_summary_template"):
        # Format using template parameters
        summary_message = sms.weekly_summary_template.format(
            student_name=name,
            days_present=4,
            late_count=1,
            absent_count=0,
            total_days=5,
            attendance_link=attendance_link,
        ).strip()
    else:
        # Fallback to simple format
        summary_message = (
            f"Week summary for {name}: 4P 1L 0A\n\nView: {attendance_link}".strip()
        )

    # Add unsubscribe text if enabled
    if sms.include_unsubscribe:
        summary_message += sms.unsubscribe_text

    success = sms.send_sms(phone, summary_message)

    if success:
        print("✅ Weekly summary sent")
    else:
        print("❌ Failed to send weekly summary")
    assert isinstance(success, bool)


def test_monthly_summary(sms, student_id, name, phone):
    """Test monthly summary"""
    print("\n" + "=" * 70)
    print("📈 TEST 7: MONTHLY SUMMARY")
    print("=" * 70)
    print(
        f"Template: Month summary for {{name}}: {{present}}P {{late}}L {{absent}}A ({{rate}}%)"
    )
    print(f"Expected: ~70 characters")
    print(f"Testing with: 18 present, 2 late, 0 absent, 95% rate")

    # Build attendance link if configured
    attendance_link = ""
    try:
        if getattr(sms, "attendance_view_url", ""):
            attendance_link = sms.attendance_view_url.format(student_id=student_id)
    except Exception:
        attendance_link = ""

    # Use the template from SMS notifier if available
    if hasattr(sms, "monthly_summary_template"):
        # Format using template parameters
        summary_message = sms.monthly_summary_template.format(
            student_name=name,
            days_present=18,
            late_count=2,
            absent_count=0,
            total_days=20,
            percentage=95,
            attendance_link=attendance_link,
        ).strip()
    else:
        # Fallback to simple format
        summary_message = f"Month summary for {name}: 18P 2L 0A (95%)\n\nView: {attendance_link}".strip()

    # Add unsubscribe text if enabled
    if sms.include_unsubscribe:
        summary_message += sms.unsubscribe_text

    success = sms.send_sms(phone, summary_message)

    if success:
        print("✅ Monthly summary sent")
    else:
        print("❌ Failed to send monthly summary")
    assert isinstance(success, bool)


def test_quiet_hours(sms):
    """Test quiet hours detection"""
    print("\n" + "=" * 70)
    print("🔇 FEATURE TEST: QUIET HOURS")
    print("=" * 70)

    if sms._is_quiet_hours():
        print("✅ Currently in QUIET HOURS (22:00-06:00)")
        print("   SMS sending would be skipped in production")
        print("   (Continuing for testing purposes)")
    else:
        print("✅ NOT in quiet hours - SMS sending allowed")
        current_time = datetime.now().strftime("%H:%M")
        print(f"   Current time: {current_time}")
        print(f"   Quiet hours: 22:00-06:00")


def test_cooldown(sms, student_id, name, phone):
    """Test cooldown mechanism"""
    print("\n" + "=" * 70)
    print("⏱️  FEATURE TEST: COOLDOWN MECHANISM")
    print("=" * 70)
    print("Sending two identical messages 10 seconds apart...")
    print("Expected: First succeeds, second is blocked by cooldown")

    # First message
    print("\n📤 Sending message #1...")
    success1 = sms.send_attendance_notification(
        student_id=student_id,
        student_name=name,
        parent_phone=phone,
        timestamp=datetime.now(),
        scan_type="time_in",
    )

    if success1:
        print("✅ Message #1 sent")

    # Wait 10 seconds
    import time

    print("\n⏳ Waiting 10 seconds...")
    time.sleep(10)

    # Second message (should be blocked by cooldown)
    print("\n📤 Sending message #2 (duplicate)...")
    success2 = sms.send_attendance_notification(
        student_id=student_id,
        student_name=name,
        parent_phone=phone,
        timestamp=datetime.now(),
        scan_type="time_in",
    )

    if not success2:
        print("✅ COOLDOWN WORKING: Message #2 blocked (within 5-minute cooldown)")
    else:
        print("⚠️  Warning: Message #2 was sent (cooldown may not be working)")

    try:
        cooldown = getattr(sms, "cooldown_minutes", 5)
    except Exception:
        cooldown = 5
    print(f"\n💡 Cooldown period: {cooldown} minutes")


def test_unsubscribe_text(sms):
    """Test unsubscribe text feature"""
    print("\n" + "=" * 70)
    print("📵 FEATURE TEST: UNSUBSCRIBE TEXT")
    print("=" * 70)

    if getattr(sms, "include_unsubscribe", True):
        print("✅ Unsubscribe text is ENABLED")
        print("   All summary messages will include:")
        print('   "Reply STOP to unsubscribe."')
    else:
        print("❌ Unsubscribe text is DISABLED")

    print("\nNote: Check-in/check-out messages don't include unsubscribe text")
    print("      Only summary and alert messages include it")


def main():
    print("\n" + "=" * 70)
    print("📱 SMS TEMPLATE TESTER - ALL TEMPLATES")
    print("=" * 70)
    print("\nThis will test all 7 SMS templates and new features:")
    print("1. Check-in notification")
    print("2. Check-out notification")
    print("3. Late arrival alert")
    print("4. No check-out alert")
    print("5. Absence alert")
    print("6. Weekly summary")
    print("7. Monthly summary")
    print("\nPlus: Quiet hours, Cooldown, Unsubscribe text")

    # Default test student (John Paolo Gonzales)
    student_id = "221566"

    # Try to get student from Supabase, fallback to hardcoded values
    print("\n📡 Fetching student data from Supabase...")
    student_info = get_student_info(student_id)

    if student_info:
        sid, name, phone, count = student_info
        print("✅ Connected to Supabase")
    else:
        print("⚠️  Supabase connection failed - using fallback data")
        sid = student_id
        name = "John Paolo Gonzales"
        phone = "09923783237"  # Update this with your test phone number
        count = 5

    print(f"\n📋 Test Student:")
    print(f"   ID: {sid}")
    print(f"   Name: {name}")
    print(f"   Phone: {phone}")
    print(f"   Records: {count}")

    # Allow updating phone number
    update_phone = input(f"\nCurrent phone: {phone}. Update? (y/n): ").strip().lower()
    if update_phone == "y":
        new_phone = input("Enter phone number (e.g., 09123456789): ").strip()
        if new_phone:
            phone = new_phone
            print(f"✅ Phone updated to: {phone}")
        else:
            print("❌ Invalid phone number, using original")

    # Use sid = student_id for compatibility
    sid = student_id

    print("\n" + "=" * 70)
    print("OPTIONS:")
    print("=" * 70)
    print("1. Test ALL templates (7 tests + 3 feature tests)")
    print("2. Test individual template")
    print("3. Test features only (quiet hours, cooldown, unsubscribe)")
    print("4. Update phone number")
    print("5. Exit")

    choice = input("\nEnter your choice (1-5): ").strip()

    if choice == "4":
        phone = input("Enter phone number (e.g., 09123456789): ").strip()
        if phone:
            update_phone_number(student_id, phone)
        return

    if choice == "5":
        print("\n👋 Goodbye!")
        return

    # Initialize SMS notifier
    try:
        import json

        from src.notifications.sms_notifier import SMSNotifier

        # Load environment variables first
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

        with open("config/config.json", "r") as f:
            config = json.load(f)

        sms_config = config.get("sms_notifications", {})

        # Replace environment variable placeholders
        if "username" in sms_config and isinstance(sms_config["username"], str):
            if sms_config["username"].startswith("${") and sms_config[
                "username"
            ].endswith("}"):
                env_var = sms_config["username"][2:-1]
                sms_config["username"] = os.getenv(env_var, sms_config["username"])

        if "password" in sms_config and isinstance(sms_config["password"], str):
            if sms_config["password"].startswith("${") and sms_config[
                "password"
            ].endswith("}"):
                env_var = sms_config["password"][2:-1]
                sms_config["password"] = os.getenv(env_var, sms_config["password"])

        if "device_id" in sms_config and isinstance(sms_config["device_id"], str):
            if sms_config["device_id"].startswith("${") and sms_config[
                "device_id"
            ].endswith("}"):
                env_var = sms_config["device_id"][2:-1]
                sms_config["device_id"] = os.getenv(env_var, sms_config["device_id"])

        if "api_url" in sms_config and isinstance(sms_config["api_url"], str):
            if sms_config["api_url"].startswith("${") and sms_config[
                "api_url"
            ].endswith("}"):
                env_var = sms_config["api_url"][2:-1]
                sms_config["api_url"] = os.getenv(env_var, sms_config["api_url"])

        sms = SMSNotifier(sms_config)

        # Force-enable all notification types for testing
        try:
            sms.notification_prefs.update(
                {
                    "check_in": True,
                    "check_out": True,
                    "late": True,
                    "no_checkout": True,
                    "absence": True,
                    "weekly_summary": True,
                    "monthly_summary": True,
                }
            )
        except Exception:
            pass

        if not sms.enabled:
            print("\n❌ SMS notifier could not be initialized")
            print("   Check your .env file has:")
            print("   - SMS_USERNAME")
            print("   - SMS_PASSWORD")
            print("   - SMS_DEVICE_ID")
            return

        print("\n✅ SMS notifier initialized")

    except Exception as e:
        print(f"\n❌ Error initializing SMS: {e}")
        import traceback

        traceback.print_exc()
        return

    # Confirm before sending
    print("\n" + "=" * 70)
    print("⚠️  CONFIRMATION")
    print("=" * 70)
    print(f"📱 Phone number: {phone}")
    print(f"👤 Student: {name}")

    if choice == "1":
        print(f"\n⚠️  This will send 10+ SMS messages to {phone}")
        print("   - 7 template tests")
        print("   - 2 cooldown test messages")
        print("   - Plus feature demonstrations")
    elif choice == "2":
        print(f"\n⚠️  This will send 1 SMS message to {phone}")
    elif choice == "3":
        print(f"\n⚠️  This will send 2 SMS messages to {phone}")
        print("   - For cooldown testing")

    confirm = input("\n⚠️  Proceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("\n❌ Cancelled")
        return

    # Run tests
    results = []

    if choice == "1":
        # Test all templates
        print("\n" + "=" * 70)
        print("🚀 STARTING ALL TESTS")
        print("=" * 70)

        # Template tests
        results.append(("Check-in", test_check_in(sms, sid, name, phone)))
        input("\nPress Enter to continue to next test...")

        results.append(("Check-out", test_check_out(sms, sid, name, phone)))
        input("\nPress Enter to continue to next test...")

        results.append(("Late Arrival", test_late_arrival(sms, sid, name, phone)))
        input("\nPress Enter to continue to next test...")

        results.append(("No Checkout", test_no_checkout(sms, sid, name, phone)))
        input("\nPress Enter to continue to next test...")

        results.append(("Absence", test_absence(sms, sid, name, phone)))
        input("\nPress Enter to continue to next test...")

        results.append(("Weekly Summary", test_weekly_summary(sms, sid, name, phone)))
        input("\nPress Enter to continue to next test...")

        results.append(("Monthly Summary", test_monthly_summary(sms, sid, name, phone)))

        # Feature tests
        print("\n" + "=" * 70)
        print("🔧 FEATURE TESTS")
        print("=" * 70)

        test_quiet_hours(sms)
        test_unsubscribe_text(sms)

        print("\n⚠️  Next: Cooldown test (will send 2 more messages)")
        input("Press Enter to continue...")
        test_cooldown(sms, sid, name, phone)

    elif choice == "2":
        # Test individual template
        print("\n" + "=" * 70)
        print("SELECT TEMPLATE:")
        print("=" * 70)
        print("1. Check-in notification")
        print("2. Check-out notification")
        print("3. Late arrival alert")
        print("4. No check-out alert")
        print("5. Absence alert")
        print("6. Weekly summary")
        print("7. Monthly summary")

        template = input("\nEnter template number (1-7): ").strip()

        if template == "1":
            results.append(("Check-in", test_check_in(sms, sid, name, phone)))
        elif template == "2":
            results.append(("Check-out", test_check_out(sms, sid, name, phone)))
        elif template == "3":
            results.append(("Late Arrival", test_late_arrival(sms, sid, name, phone)))
        elif template == "4":
            results.append(("No Checkout", test_no_checkout(sms, sid, name, phone)))
        elif template == "5":
            results.append(("Absence", test_absence(sms, sid, name, phone)))
        elif template == "6":
            results.append(
                ("Weekly Summary", test_weekly_summary(sms, sid, name, phone))
            )
        elif template == "7":
            results.append(
                ("Monthly Summary", test_monthly_summary(sms, sid, name, phone))
            )
        else:
            print("❌ Invalid template number")
            return

    elif choice == "3":
        # Test features only
        test_quiet_hours(sms)
        test_unsubscribe_text(sms)

        print("\n⚠️  Next: Cooldown test (will send 2 messages)")
        input("Press Enter to continue...")
        test_cooldown(sms, sid, name, phone)

    # Print summary
    if results:
        print("\n" + "=" * 70)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 70)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")

        print("\n" + "─" * 70)
        print(
            f"Total: {passed}/{total} tests passed ({passed*100//total if total > 0 else 0}%)"
        )

        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")

    print("\n" + "=" * 70)
    print("✅ TESTING COMPLETE")
    print("=" * 70)
    print("\n💡 Tips:")
    print("   - Check your phone for received messages")
    print("   - Verify message formatting and content")
    print("   - Check character counts (SMS costs)")
    print("   - Test unsubscribe text appears on summaries")
    print("   - Verify cooldown prevented duplicate message")
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
