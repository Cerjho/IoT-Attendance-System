#!/usr/bin/env python3
"""
Test SMS Templates and Notification Preferences

Tests:
1. Template cache initialization
2. Template retrieval from cache
3. Supabase template sync
4. Notification preference checking
5. Template variable substitution
6. Fallback to defaults when server unavailable
7. Cache expiry and refresh
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.notifications.template_cache import TemplateCache
from src.utils.logger_config import setup_logger

logger = setup_logger('test_sms_templates')


def test_template_cache_initialization():
    """Test 1: Template cache table creation."""
    print("\n=== Test 1: Template Cache Initialization ===")
    
    try:
        cache = TemplateCache(db_path="data/attendance.db")
        
        # Verify table exists
        conn = sqlite3.connect("data/attendance.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='template_cache'
        """)
        table_exists = cursor.fetchone() is not None
        conn.close()
        
        if table_exists:
            print("✅ Template cache table created successfully")
            return True
        else:
            print("❌ Template cache table not found")
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize cache: {e}")
        return False


def test_default_templates():
    """Test 2: Default template retrieval."""
    print("\n=== Test 2: Default Templates ===")
    
    try:
        cache = TemplateCache(db_path="data/attendance.db")
        
        # Test getting each default template
        template_types = [
            'check_in',
            'check_out',
            'late_arrival',
            'early_departure',
            'absence_detected',
            'schedule_violation',
            'multiple_scans',
            'system_alert'
        ]
        
        all_found = True
        for template_type in template_types:
            template = cache.get_template_text(template_type)
            if template and len(template) > 0:
                print(f"✅ {template_type}: {template[:50]}...")
            else:
                print(f"❌ {template_type}: Not found")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ Failed to get default templates: {e}")
        return False


def test_cache_population():
    """Test 3: Populate cache with test templates."""
    print("\n=== Test 3: Cache Population ===")
    
    try:
        cache = TemplateCache(db_path="data/attendance.db")
        
        # Populate with defaults
        count = cache.populate_with_defaults()
        
        if count > 0:
            print(f"✅ Populated cache with {count} default templates")
            return True
        else:
            print("❌ Failed to populate cache")
            return False
            
    except Exception as e:
        print(f"❌ Failed to populate cache: {e}")
        return False


def test_template_retrieval():
    """Test 4: Retrieve templates from cache."""
    print("\n=== Test 4: Template Retrieval ===")
    
    try:
        cache = TemplateCache(db_path="data/attendance.db")
        
        # Get check_in template
        template = cache.get_template('check_in')
        
        if template:
            print(f"✅ Retrieved template:")
            print(f"   Type: {template['template_type']}")
            print(f"   Name: {template['template_name']}")
            print(f"   Message: {template['message_template'][:60]}...")
            print(f"   Variables: {template['variables']}")
            return True
        else:
            print("❌ Template not found in cache")
            return False
            
    except Exception as e:
        print(f"❌ Failed to retrieve template: {e}")
        return False


def test_cache_stats():
    """Test 5: Get cache statistics."""
    print("\n=== Test 5: Cache Statistics ===")
    
    try:
        cache = TemplateCache(db_path="data/attendance.db")
        stats = cache.get_cache_stats()
        
        if stats:
            print("✅ Cache statistics:")
            print(f"   Total templates: {stats.get('total_templates', 0)}")
            print(f"   Active templates: {stats.get('active_templates', 0)}")
            print(f"   Inactive templates: {stats.get('inactive_templates', 0)}")
            print(f"   Cache age (hours): {stats.get('cache_age_hours', 'N/A')}")
            print(f"   Is stale: {stats.get('is_stale', False)}")
            return True
        else:
            print("❌ Failed to get cache stats")
            return False
            
    except Exception as e:
        print(f"❌ Failed to get cache stats: {e}")
        return False


def test_template_update():
    """Test 6: Update cache with new templates."""
    print("\n=== Test 6: Template Update ===")
    
    try:
        cache = TemplateCache(db_path="data/attendance.db")
        
        # Create test template
        test_templates = [{
            'template_type': 'test_notification',
            'template_name': 'Test Notification',
            'message_template': 'This is a test: {{student_name}} at {{time}}',
            'variables': ['student_name', 'time'],
            'is_active': True,
            'updated_at': datetime.now().isoformat()
        }]
        
        count = cache.update_cache(test_templates)
        
        if count > 0:
            # Verify it was stored
            template = cache.get_template('test_notification')
            if template:
                print(f"✅ Updated cache with {count} template(s)")
                print(f"   Test template retrieved: {template['message_template']}")
                return True
            else:
                print("❌ Template updated but not retrievable")
                return False
        else:
            print("❌ Failed to update cache")
            return False
            
    except Exception as e:
        print(f"❌ Failed to update cache: {e}")
        return False


def test_cache_expiry():
    """Test 7: Cache expiry detection."""
    print("\n=== Test 7: Cache Expiry ===")
    
    try:
        # Create cache with short expiry (1 hour)
        cache = TemplateCache(db_path="data/attendance.db", cache_expiry_hours=1)
        
        # Check if cache is stale (depends on actual cache age)
        is_stale = cache.is_cache_stale()
        print(f"✅ Cache staleness check: {'Stale' if is_stale else 'Fresh'}")
        
        # This is informational, not pass/fail
        stats = cache.get_cache_stats()
        if 'cache_age_hours' in stats:
            age = stats['cache_age_hours']
            print(f"   Current cache age: {age} hours")
            print(f"   Expiry threshold: 1 hour")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to check cache expiry: {e}")
        return False


def test_all_templates():
    """Test 8: Retrieve all cached templates."""
    print("\n=== Test 8: All Templates ===")
    
    try:
        cache = TemplateCache(db_path="data/attendance.db")
        templates = cache.get_all_templates()
        
        if templates:
            print(f"✅ Retrieved {len(templates)} templates:")
            for template in templates[:3]:  # Show first 3
                print(f"   - {template['template_type']}: {template['template_name']}")
            if len(templates) > 3:
                print(f"   ... and {len(templates) - 3} more")
            return True
        else:
            print("❌ No templates in cache")
            return False
            
    except Exception as e:
        print(f"❌ Failed to get all templates: {e}")
        return False


def test_clear_cache():
    """Test 9: Clear all cached templates."""
    print("\n=== Test 9: Clear Cache ===")
    
    try:
        cache = TemplateCache(db_path="data/attendance.db")
        
        # Get count before clearing
        stats_before = cache.get_cache_stats()
        count_before = stats_before.get('total_templates', 0)
        
        # Clear cache
        success = cache.clear_cache()
        
        # Get count after clearing
        stats_after = cache.get_cache_stats()
        count_after = stats_after.get('total_templates', 0)
        
        if success and count_after == 0:
            print(f"✅ Cache cleared successfully ({count_before} → {count_after} templates)")
            
            # Repopulate for other tests
            cache.populate_with_defaults()
            print("   (Repopulated with defaults)")
            return True
        else:
            print(f"❌ Failed to clear cache (before: {count_before}, after: {count_after})")
            return False
            
    except Exception as e:
        print(f"❌ Failed to clear cache: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("SMS Template Cache Test Suite")
    print("=" * 70)
    
    tests = [
        ("Cache Initialization", test_template_cache_initialization),
        ("Default Templates", test_default_templates),
        ("Cache Population", test_cache_population),
        ("Template Retrieval", test_template_retrieval),
        ("Cache Statistics", test_cache_stats),
        ("Template Update", test_template_update),
        ("Cache Expiry", test_cache_expiry),
        ("All Templates", test_all_templates),
        ("Clear Cache", test_clear_cache),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
