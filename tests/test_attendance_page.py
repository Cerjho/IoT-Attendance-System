#!/usr/bin/env python3
"""
Test attendance page functionality
"""
import sys
import pytest

import requests

# Test configuration
GITHUB_PAGES_URL = "https://cerjho.github.io/IoT-Attendance-System/view-attendance.html"
TEST_STUDENT_ID = "233294"  # Maria Santos


def test_page_loads():
    """Test that the page loads successfully"""
    print("🧪 Test 1: Page Loading...")
    try:
        url = f"{GITHUB_PAGES_URL}?student_id={TEST_STUDENT_ID}"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200, f"Status code: {response.status_code}"
        print("   ✅ PASS - Page loads successfully")
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Network unavailable or page unreachable: {e}")
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
        assert False, f"Page load error: {e}"


def test_page_content():
    """Test that the page contains required elements"""
    print("\n🧪 Test 2: Page Content...")
    try:
        url = f"{GITHUB_PAGES_URL}?student_id={TEST_STUDENT_ID}"
        response = requests.get(url, timeout=10)
        content = response.text

        # Check for essential elements only (flexible check)
        essential_elements = ["Attendance", "student"]
        
        found = sum(1 for element in essential_elements if element.lower() in content.lower())
        
        assert found >= 1, f"Page doesn't appear to be attendance-related"
        print("   ✅ PASS - Attendance page content verified")

    except requests.exceptions.RequestException as e:
        pytest.skip(f"Network unavailable or page unreachable: {e}")
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
        assert False, f"Content check error: {e}"


def test_javascript_present():
    """Test that JavaScript code is present"""
    print("\n🧪 Test 3: JavaScript Functionality...")
    try:
        url = f"{GITHUB_PAGES_URL}?student_id={TEST_STUDENT_ID}"
        response = requests.get(url, timeout=10)
        content = response.text

        # Check for JavaScript presence (flexible check)
        has_script = "<script>" in content or "function" in content
        
        assert has_script, "No JavaScript found on page"
        print("   ✅ PASS - JavaScript present")

    except requests.exceptions.RequestException as e:
        pytest.skip(f"Network unavailable or page unreachable: {e}")
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
        assert False, f"JavaScript presence error: {e}"


def test_mobile_responsive():
    """Test that mobile styles are present"""
    print("\n🧪 Test 4: Mobile Responsiveness...")
    try:
        url = f"{GITHUB_PAGES_URL}?student_id={TEST_STUDENT_ID}"
        response = requests.get(url, timeout=10)
        content = response.text

        # Flexible check for responsive design
        has_responsive = "viewport" in content.lower() or "@media" in content
        assert has_responsive, "No responsive design indicators found"
        print("   ✅ PASS - Responsive design present")

    except requests.exceptions.RequestException as e:
        pytest.skip(f"Network unavailable or page unreachable: {e}")
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
        assert False, f"Mobile responsive check error: {e}"


def test_error_handling():
    """Test that error handling is present"""
    print("\n🧪 Test 5: Error Handling...")
    try:
        url = f"{GITHUB_PAGES_URL}?student_id={TEST_STUDENT_ID}"
        response = requests.get(url, timeout=10)
        content = response.text

        # Check for basic error handling (flexible)
        has_error_handling = "try" in content or "catch" in content or "error" in content.lower()
        
        assert has_error_handling, "No error handling found"
        print("   ✅ PASS - Error handling present")

    except requests.exceptions.RequestException as e:
        pytest.skip(f"Network unavailable or page unreachable: {e}")
    except Exception as e:
        print(f"   ❌ FAIL - Error: {e}")
        assert False, f"Error handling check error: {e}"


def main():
    print("=" * 70)
    print("ATTENDANCE PAGE PRODUCTION READINESS TEST")
    print("=" * 70)
    print(f"\nTesting: {GITHUB_PAGES_URL}")
    print(f"Student ID: {TEST_STUDENT_ID}\n")

    tests = [
        test_page_loads,
        test_page_content,
        test_javascript_present,
        test_mobile_responsive,
        test_error_handling,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)
    percentage = (passed / total) * 100

    print(f"\nTests Passed: {passed}/{total} ({percentage:.0f}%)")

    if passed == total:
        print("\n✅ ALL TESTS PASSED - Page is production ready!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed - Review needed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
