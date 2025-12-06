#!/usr/bin/env python3
"""
Test Script: Student Schedule Validation
Tests the complete schedule validation workflow
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from src.attendance.schedule_validator import ScheduleValidator, ValidationResult
from src.attendance.schedule_manager import ScheduleManager
from src.utils.config_loader import load_config


def print_header(title):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_result(label, value, color="white"):
    """Print formatted result"""
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "white": "\033[0m",
    }
    reset = "\033[0m"
    c = colors.get(color, colors["white"])
    print(f"{label:30} {c}{value}{reset}")


def create_test_students(db_path):
    """Create test students with different schedules"""
    print_header("Creating Test Students")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop and recreate table to ensure correct schema
    cursor.execute("DROP TABLE IF EXISTS students")
    cursor.execute("""
        CREATE TABLE students (
            student_id TEXT PRIMARY KEY,
            uuid TEXT,
            name TEXT,
            email TEXT,
            parent_phone TEXT,
            section_id TEXT,
            schedule_id TEXT,
            allowed_session TEXT,
            created_at TEXT
        )
    """)
    
    test_students = [
        ("2021001", "Morning Student", "morning"),
        ("2021002", "Afternoon Student", "afternoon"),
        ("2021003", "Both Sessions Student", "both"),
        ("2021004", "No Schedule Student", None),
    ]
    
    for student_id, name, allowed_session in test_students:
        cursor.execute("""
            INSERT OR REPLACE INTO students 
            (student_id, uuid, name, email, parent_phone, section_id, schedule_id, allowed_session, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student_id,
            f"uuid-{student_id}",
            name,
            f"{student_id}@example.com",
            "+639123456789",
            "section-01" if allowed_session else None,
            "schedule-01" if allowed_session else None,
            allowed_session,
            datetime.now().isoformat()
        ))
        
        print_result(f"Created: {student_id}", name, "green")
    
    conn.commit()
    conn.close()
    print(f"\n✅ Created {len(test_students)} test students")


def test_schedule_validation(db_path):
    """Test schedule validation logic"""
    print_header("Testing Schedule Validation")
    
    validator = ScheduleValidator(db_path)
    
    # Test scenarios
    test_cases = [
        # (student_id, current_session, expected_result)
        ("2021001", "morning", ValidationResult.VALID, "Morning student in morning"),
        ("2021001", "afternoon", ValidationResult.WRONG_SESSION, "Morning student in afternoon (REJECT)"),
        ("2021002", "morning", ValidationResult.WRONG_SESSION, "Afternoon student in morning (REJECT)"),
        ("2021002", "afternoon", ValidationResult.VALID, "Afternoon student in afternoon"),
        ("2021003", "morning", ValidationResult.VALID, "Both-session student in morning"),
        ("2021003", "afternoon", ValidationResult.VALID, "Both-session student in afternoon"),
        ("2021004", "morning", ValidationResult.VALID, "No schedule in morning (allowed)"),
        ("2021004", "afternoon", ValidationResult.VALID, "No schedule in afternoon (allowed)"),
        ("9999999", "morning", ValidationResult.NOT_FOUND, "Non-existent student"),
    ]
    
    passed = 0
    failed = 0
    
    for student_id, session, expected, description in test_cases:
        result, details = validator.validate_student_schedule(student_id, session)
        
        if result == expected:
            print_result(f"✓ {description}", f"PASS ({result.value})", "green")
            passed += 1
        else:
            print_result(f"✗ {description}", f"FAIL (expected {expected.value}, got {result.value})", "red")
            failed += 1
        
        # Show details for rejected scans
        if result == ValidationResult.WRONG_SESSION:
            print(f"   → {details.get('message', '')}")
    
    print(f"\n{'='*70}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'='*70}")
    
    return failed == 0


def test_schedule_stats(db_path):
    """Test schedule statistics"""
    print_header("Schedule Statistics")
    
    validator = ScheduleValidator(db_path)
    stats = validator.get_schedule_stats()
    
    print_result("Total Students:", stats.get("total", 0), "blue")
    print_result("Morning Only:", stats.get("morning", 0), "yellow")
    print_result("Afternoon Only:", stats.get("afternoon", 0), "yellow")
    print_result("Both Sessions:", stats.get("both", 0), "yellow")
    print_result("No Schedule:", stats.get("none", 0), "yellow")


def test_current_schedule_detection(config):
    """Test schedule manager integration"""
    print_header("Current Schedule Detection")
    
    schedule_manager = ScheduleManager(config)
    schedule_info = schedule_manager.get_schedule_info()
    
    print_result("Current Session:", schedule_info["current_session"].upper(), "blue")
    print_result("Expected Scan Type:", schedule_info["expected_scan_type"].upper(), "blue")
    print_result("Is Login Window:", str(schedule_info.get("is_login_window", False)), "yellow")
    print_result("Is Logout Window:", str(schedule_info.get("is_logout_window", False)), "yellow")


def test_validation_integration(db_path, config):
    """Test complete validation workflow"""
    print_header("Integration Test: Complete Workflow")
    
    validator = ScheduleValidator(db_path)
    schedule_manager = ScheduleManager(config)
    
    # Get current schedule info
    schedule_info = schedule_manager.get_schedule_info()
    current_session = schedule_info["current_session"]
    
    print(f"\n🕐 Current Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📅 Current Session: {current_session.upper()}")
    print()
    
    # Test each student in current session
    test_students = [
        ("2021001", "Morning Student"),
        ("2021002", "Afternoon Student"),
        ("2021003", "Both Sessions Student"),
    ]
    
    for student_id, name in test_students:
        result, details = validator.validate_student_schedule(student_id, current_session)
        
        if result == ValidationResult.VALID:
            print(f"✅ {name} ({student_id}): {details['message']}")
        elif result == ValidationResult.WRONG_SESSION:
            print(f"❌ {name} ({student_id}): {details['message']}")
        else:
            print(f"⚠️  {name} ({student_id}): {details['message']}")


def main():
    """Run all tests"""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║          STUDENT SCHEDULE VALIDATION TEST SUITE                  ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    
    # Configuration
    db_path = "data/attendance.db"
    config_file = "config/config.json"
    
    try:
        # Load config
        config = load_config(config_file)
        
        # Create test data
        create_test_students(db_path)
        
        # Run tests
        test_schedule_stats(db_path)
        test_current_schedule_detection(config)
        validation_passed = test_schedule_validation(db_path)
        test_validation_integration(db_path, config)
        
        # Summary
        print_header("Test Summary")
        if validation_passed:
            print("✅ All validation tests PASSED")
            print("✅ Schedule validation is working correctly")
            print()
            print("Next Steps:")
            print("1. Ensure roster sync fetches schedule data from Supabase")
            print("2. Deploy sections with schedule_id assignments")
            print("3. Test with real student scans")
        else:
            print("❌ Some validation tests FAILED")
            print("⚠️  Please review the errors above")
        
        print()
        
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
