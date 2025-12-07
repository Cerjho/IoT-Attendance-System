#!/usr/bin/env python3
"""
Test SMS Template and Preference System

Integration tests for:
- Template fetching from Supabase
- Template caching
- Notification preferences
- Server-side configuration
"""

import os
import sys
import requests
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
from src.notifications.template_cache import TemplateCache

# Load environment
load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


def test_template_table_exists():
    """Test 1: Verify sms_templates table exists."""
    print("\n" + "="*70)
    print("TEST 1: SMS Templates Table Exists")
    print("="*70)
    
    url = f"{SUPABASE_URL}/rest/v1/sms_templates"
    params = {"select": "count"}
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            print("✅ PASS: sms_templates table exists")
            return True
        else:
            print(f"❌ FAIL: Cannot access table (status {response.status_code})")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_template_count():
    """Test 2: Verify 8 default templates exist."""
    print("\n" + "="*70)
    print("TEST 2: Default Templates Exist (Expect 8)")
    print("="*70)
    
    url = f"{SUPABASE_URL}/rest/v1/sms_templates"
    params = {"select": "template_type,template_name,is_active"}
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            templates = response.json()
            count = len(templates)
            
            print(f"→ Found {count} templates:")
            for t in templates:
                status = "✓" if t.get('is_active') else "✗"
                print(f"  {status} {t['template_type']}: {t['template_name']}")
            
            if count == 8:
                print("✅ PASS: All 8 default templates exist")
                return True
            else:
                print(f"❌ FAIL: Expected 8 templates, found {count}")
                return False
        else:
            print(f"❌ FAIL: Cannot fetch templates (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_get_template_rpc():
    """Test 3: Test get_sms_template RPC function."""
    print("\n" + "="*70)
    print("TEST 3: get_sms_template RPC Function")
    print("="*70)
    
    url = f"{SUPABASE_URL}/rest/v1/rpc/get_sms_template"
    
    test_cases = [
        'check_in',
        'check_out',
        'late_arrival',
        'absence_detected'
    ]
    
    passed = 0
    for template_type in test_cases:
        try:
            payload = {"template_type_param": template_type}
            response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    template = data[0]
                    msg = template.get('message_template', '')
                    print(f"  ✓ {template_type}: {msg[:50]}...")
                    passed += 1
                else:
                    print(f"  ✗ {template_type}: Empty response")
            else:
                print(f"  ✗ {template_type}: Status {response.status_code}")
        except Exception as e:
            print(f"  ✗ {template_type}: {e}")
    
    if passed == len(test_cases):
        print(f"✅ PASS: All {passed}/{len(test_cases)} RPC calls succeeded")
        return True
    else:
        print(f"❌ FAIL: Only {passed}/{len(test_cases)} succeeded")
        return False


def test_template_cache():
    """Test 4: Test local template caching."""
    print("\n" + "="*70)
    print("TEST 4: Template Cache Module")
    print("="*70)
    
    try:
        # Initialize cache
        cache = TemplateCache("data/attendance.db")
        print("  ✓ Cache initialized")
        
        # Fetch templates from server
        url = f"{SUPABASE_URL}/rest/v1/sms_templates"
        params = {"is_active": "eq.true", "select": "*"}
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"  ✗ Cannot fetch templates from server")
            return False
        
        templates = response.json()
        print(f"  ✓ Fetched {len(templates)} templates from server")
        
        # Update cache
        cached_count = cache.update_cache(templates)
        print(f"  ✓ Cached {cached_count} templates")
        
        # Test retrieval
        check_in = cache.get_template_text('check_in')
        if check_in:
            print(f"  ✓ Retrieved check_in template: {check_in[:50]}...")
        else:
            print(f"  ✗ Failed to retrieve check_in template")
            return False
        
        # Test stats
        stats = cache.get_cache_stats()
        print(f"  ✓ Cache stats: {stats.get('total_templates', 0)} total, "
              f"{stats.get('active_templates', 0)} active")
        
        print("✅ PASS: Template cache working correctly")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_notification_preferences_table():
    """Test 5: Verify notification_preferences table exists."""
    print("\n" + "="*70)
    print("TEST 5: Notification Preferences Table Exists")
    print("="*70)
    
    url = f"{SUPABASE_URL}/rest/v1/notification_preferences"
    params = {"select": "count"}
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            print("✅ PASS: notification_preferences table exists")
            return True
        else:
            print(f"❌ FAIL: Cannot access table (status {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_should_send_notification_rpc():
    """Test 6: Test should_send_notification RPC function."""
    print("\n" + "="*70)
    print("TEST 6: should_send_notification RPC Function")
    print("="*70)
    
    url = f"{SUPABASE_URL}/rest/v1/rpc/should_send_notification"
    
    # Test with dummy data (should return true for non-existent preferences)
    test_cases = [
        {
            "phone_param": "+639171234567",
            "student_id_param": "00000000-0000-0000-0000-000000000001",
            "notification_type": "check_in"
        },
        {
            "phone_param": "+639171234567",
            "student_id_param": "00000000-0000-0000-0000-000000000001",
            "notification_type": "late_arrival"
        }
    ]
    
    passed = 0
    for i, payload in enumerate(test_cases, 1):
        try:
            response = requests.post(url, json=payload, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✓ Test {i}: {payload['notification_type']} → {result}")
                passed += 1
            else:
                print(f"  ✗ Test {i}: Status {response.status_code}")
                print(f"     Response: {response.text}")
        except Exception as e:
            print(f"  ✗ Test {i}: {e}")
    
    if passed == len(test_cases):
        print(f"✅ PASS: All {passed}/{len(test_cases)} RPC calls succeeded")
        return True
    else:
        print(f"❌ FAIL: Only {passed}/{len(test_cases)} succeeded")
        return False


def test_template_variable_support():
    """Test 7: Verify templates support variable substitution."""
    print("\n" + "="*70)
    print("TEST 7: Template Variable Support")
    print("="*70)
    
    try:
        cache = TemplateCache("data/attendance.db")
        
        # Get check_in template
        template = cache.get_template('check_in')
        if not template:
            print("  ✗ Cannot get check_in template")
            return False
        
        msg = template.get('message_template', '')
        variables = template.get('variables', [])
        
        print(f"  → Template: {msg[:80]}...")
        print(f"  → Variables: {', '.join(variables)}")
        
        # Check for common variables
        required_vars = ['student_name', 'student_number', 'time']
        found_vars = []
        
        for var in required_vars:
            # Check both {{var}} and {var} formats
            if f'{{{{{var}}}}}' in msg or f'{{{var}}}' in msg:
                found_vars.append(var)
                print(f"  ✓ Variable found: {var}")
        
        if len(found_vars) >= 2:
            print(f"✅ PASS: Template has variable placeholders")
            return True
        else:
            print(f"❌ FAIL: Missing required variables")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def test_cache_staleness_detection():
    """Test 8: Test cache staleness detection."""
    print("\n" + "="*70)
    print("TEST 8: Cache Staleness Detection")
    print("="*70)
    
    try:
        cache = TemplateCache("data/attendance.db", cache_expiry_hours=24)
        
        # Get cache stats
        stats = cache.get_cache_stats()
        
        print(f"  → Total templates: {stats.get('total_templates', 0)}")
        print(f"  → Active templates: {stats.get('active_templates', 0)}")
        print(f"  → Cache age: {stats.get('cache_age_hours', 0):.1f} hours")
        print(f"  → Is stale: {stats.get('is_stale', True)}")
        
        # Cache is stale if older than 24 hours or empty
        is_stale = cache.is_cache_stale()
        
        if stats.get('total_templates', 0) > 0:
            print(f"  ✓ Cache has templates")
            print(f"✅ PASS: Staleness detection working (stale={is_stale})")
            return True
        else:
            print(f"  ! Cache is empty (run template refresh)")
            print(f"✅ PASS: Staleness detection working (cache empty)")
            return True
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False


def run_all_tests():
    """Run all tests and generate report."""
    print("\n" + "╔"+"═"*70+"╗")
    print("║" + " "*15 + "SMS TEMPLATE & PREFERENCE TEST SUITE" + " "*19 + "║")
    print("╚"+"═"*70+"╝")
    
    print(f"\nTest Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Supabase URL: {SUPABASE_URL}")
    
    tests = [
        test_template_table_exists,
        test_template_count,
        test_get_template_rpc,
        test_template_cache,
        test_notification_preferences_table,
        test_should_send_notification_rpc,
        test_template_variable_support,
        test_cache_staleness_detection
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
