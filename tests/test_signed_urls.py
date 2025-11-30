#!/usr/bin/env python3
"""
Test Script for Signed URL Implementation
Tests URL generation, verification, expiry, and tamper detection.
"""

import os
import sys
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth.url_signer import URLSigner, generate_secret_key
from src.notifications.sms_notifier import SMSNotifier


def test_url_signing():
    """Test URL signing and verification."""
    print("=" * 80)
    print("TEST 1: URL Signing and Verification")
    print("=" * 80)
    
    # Generate test secret
    secret = generate_secret_key()
    signer = URLSigner(secret)
    
    # Test URL generation
    base_url = "https://cerjho.github.io/IoT-Attendance-System/view-attendance.html"
    student_id = "2021001"
    
    signed_url = signer.sign_url(base_url, student_id, expiry_hours=24)
    print(f"\n✅ Generated signed URL:")
    print(f"   {signed_url}")
    
    # Test verification
    is_valid, verified_id, error = signer.verify_url(signed_url)
    
    if is_valid:
        print(f"\n✅ Verification PASSED")
        print(f"   Student ID: {verified_id}")
    else:
        print(f"\n❌ Verification FAILED: {error}")
        return False
    
    return True


def test_expiry():
    """Test URL expiry."""
    print("\n" + "=" * 80)
    print("TEST 2: URL Expiry Detection")
    print("=" * 80)
    
    secret = generate_secret_key()
    signer = URLSigner(secret)
    
    # Generate URL that expires in 1 second
    base_url = "https://example.com"
    student_id = "2021001"
    
    # Create URL with 0 hours expiry (already expired)
    import hmac
    import hashlib
    from urllib.parse import urlencode
    
    # Manually create expired URL
    expires_at = int((datetime.now() - timedelta(hours=1)).timestamp())
    params = {'student_id': student_id, 'expires': str(expires_at)}
    message = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    params['sig'] = signature
    expired_url = f"{base_url}?{urlencode(params)}"
    
    print(f"\n📅 Testing expired URL (expired 1 hour ago)...")
    is_valid, verified_id, error = signer.verify_url(expired_url)
    
    if not is_valid and "expired" in error.lower():
        print(f"✅ Expiry detection PASSED")
        print(f"   Error: {error}")
        return True
    else:
        print(f"❌ Expiry detection FAILED")
        print(f"   Expected expired error, got: {error}")
        return False


def test_tampering():
    """Test tamper detection."""
    print("\n" + "=" * 80)
    print("TEST 3: Tamper Detection")
    print("=" * 80)
    
    secret = generate_secret_key()
    signer = URLSigner(secret)
    
    # Generate valid URL
    base_url = "https://example.com"
    original_id = "2021001"
    signed_url = signer.sign_url(base_url, original_id, expiry_hours=24)
    
    # Tamper with student ID
    tampered_url = signed_url.replace("2021001", "2021999")
    
    print(f"\n🔧 Original URL: ...student_id=2021001...")
    print(f"🔧 Tampered URL: ...student_id=2021999...")
    
    is_valid, verified_id, error = signer.verify_url(tampered_url)
    
    if not is_valid and "signature" in error.lower():
        print(f"\n✅ Tamper detection PASSED")
        print(f"   Error: {error}")
        return True
    else:
        print(f"\n❌ Tamper detection FAILED")
        print(f"   Tampered URL was accepted! Security issue!")
        return False


def test_sms_integration():
    """Test SMS notifier with signed URLs."""
    print("\n" + "=" * 80)
    print("TEST 4: SMS Notifier Integration")
    print("=" * 80)
    
    # Set up test environment
    test_secret = generate_secret_key()
    os.environ['URL_SIGNING_SECRET'] = test_secret
    
    # Create test config
    config = {
        'enabled': False,  # Don't actually send SMS
        'username': 'test_user',
        'password': 'test_pass',
        'device_id': 'test_device',
        'attendance_view_url': 'https://example.com/view?student_id={student_id}',
        'use_signed_urls': True,
        'signed_url_expiry_hours': 48,
        'login_message_template': 'Student: {student_name}\nLink: {attendance_link}',
        'notification_preferences': {},
        'quiet_hours': {'enabled': False}
    }
    
    notifier = SMSNotifier(config)
    
    # Check if URL signer was initialized
    if notifier.url_signer is None:
        print("❌ URL signer not initialized in SMSNotifier")
        return False
    
    print("✅ URL signer initialized")
    
    # Generate attendance link
    student_id = "2021001"
    link = notifier._generate_attendance_link(student_id)
    
    print(f"\n📧 Generated attendance link:")
    print(f"   {link}")
    
    # Verify the link
    if 'sig=' in link and 'expires=' in link:
        print("\n✅ Link contains signature and expiry")
        
        # Verify signature
        is_valid, verified_id, error = notifier.url_signer.verify_url(link)
        
        if is_valid:
            print(f"✅ Signature verification PASSED")
            print(f"   Student ID: {verified_id}")
            return True
        else:
            print(f"❌ Signature verification FAILED: {error}")
            return False
    else:
        print("❌ Link missing signature or expiry")
        return False


def test_config_fallback():
    """Test fallback to unsigned URLs when signing disabled."""
    print("\n" + "=" * 80)
    print("TEST 5: Fallback to Unsigned URLs")
    print("=" * 80)
    
    # Config with signing disabled
    config = {
        'enabled': False,
        'username': 'test',
        'password': 'test',
        'device_id': 'test',
        'attendance_view_url': 'https://example.com/view?student_id={student_id}',
        'use_signed_urls': False,  # Disabled
        'notification_preferences': {},
        'quiet_hours': {'enabled': False}
    }
    
    notifier = SMSNotifier(config)
    
    # Generate link
    link = notifier._generate_attendance_link("2021001")
    
    print(f"\n📧 Generated link (signing disabled):")
    print(f"   {link}")
    
    if 'sig=' not in link:
        print("\n✅ Unsigned URL generated (as expected)")
        return True
    else:
        print("\n❌ URL contains signature when signing disabled")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("SIGNED URL IMPLEMENTATION - TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = []
    
    # Run tests
    results.append(("URL Signing & Verification", test_url_signing()))
    results.append(("Expiry Detection", test_expiry()))
    results.append(("Tamper Detection", test_tampering()))
    results.append(("SMS Integration", test_sms_integration()))
    results.append(("Unsigned Fallback", test_config_fallback()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! Implementation ready for production.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) FAILED. Please review.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
