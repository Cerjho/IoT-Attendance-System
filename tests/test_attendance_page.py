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

        required_elements = [
            "Student Attendance",
            "Mabini High School",
            "statsContainer",
            "filtersContainer",
            "attendanceContainer",
            "photoModal",
        ]

        missing = []
        for element in required_elements:
            if element not in content:
                missing.append(element)

        assert not missing, f"Missing elements: {', '.join(missing)}"
        print("   ✅ PASS - All required elements present")

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

        required_functions = [
            "loadAttendance",
            "calculateStats",
            "filterRecords",
            "displayAttendance",
            "openPhotoModal",
            "closePhotoModal",
        ]

        missing = []
        for func in required_functions:
            if f"function {func}" not in content and f"const {func}" not in content:
                missing.append(func)

        assert not missing, f"Missing functions: {', '.join(missing)}"
        print("   ✅ PASS - All JavaScript functions present")

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

        assert "@media (max-width: 600px)" in content, "No mobile styles found"
        print("   ✅ PASS - Mobile responsive styles present")

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

        error_features = ["showError", "try {", "catch", "navigator.onLine"]

        missing = []
        for feature in error_features:
            if feature not in content:
                missing.append(feature)

        assert not missing, f"Missing error handling: {', '.join(missing)}"
        print("   ✅ PASS - Error handling implemented")

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
