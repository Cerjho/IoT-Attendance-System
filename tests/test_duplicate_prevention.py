"""
Tests for duplicate attendance prevention per schedule session
"""

import os
import pytest
import sqlite3
from datetime import datetime
from src.database.db_handler import AttendanceDatabase


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing"""
    db_path = str(tmp_path / "test_attendance.db")
    db = AttendanceDatabase(db_path)
    yield db
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)


class TestDuplicatePrevention:
    """Test duplicate attendance prevention"""

    def test_no_duplicate_when_empty(self, temp_db):
        """Test that no duplicate is detected when no attendance exists"""
        result = temp_db.check_duplicate_for_session(
            student_id="2021001",
            scan_type="time_in",
            schedule_session="morning"
        )
        assert result is False

    def test_duplicate_detected_same_session_same_type(self, temp_db):
        """Test duplicate is detected for same session and scan type"""
        student_id = "2021001"
        
        # First login for morning session
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo1.jpg",
            qr_data="2021001",
            scan_type="time_in",
            status="present",
            schedule_session="morning"
        )
        
        # Try to login again for morning session - should be duplicate
        result = temp_db.check_duplicate_for_session(
            student_id=student_id,
            scan_type="time_in",
            schedule_session="morning"
        )
        assert result is True

    def test_no_duplicate_different_session(self, temp_db):
        """Test no duplicate for different session"""
        student_id = "2021001"
        
        # Login for morning session
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo1.jpg",
            qr_data="2021001",
            scan_type="time_in",
            status="present",
            schedule_session="morning"
        )
        
        # Login for afternoon session - should NOT be duplicate
        result = temp_db.check_duplicate_for_session(
            student_id=student_id,
            scan_type="time_in",
            schedule_session="afternoon"
        )
        assert result is False

    def test_no_duplicate_different_scan_type(self, temp_db):
        """Test no duplicate for different scan type in same session"""
        student_id = "2021001"
        
        # Login for morning session
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo1.jpg",
            qr_data="2021001",
            scan_type="time_in",
            status="present",
            schedule_session="morning"
        )
        
        # Logout for morning session - should NOT be duplicate
        result = temp_db.check_duplicate_for_session(
            student_id=student_id,
            scan_type="time_out",
            schedule_session="morning"
        )
        assert result is False

    def test_duplicate_logout_prevented(self, temp_db):
        """Test duplicate logout is prevented"""
        student_id = "2021001"
        
        # First logout for morning session
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo1.jpg",
            qr_data="2021001",
            scan_type="time_out",
            status="present",
            schedule_session="morning"
        )
        
        # Try to logout again for morning session - should be duplicate
        result = temp_db.check_duplicate_for_session(
            student_id=student_id,
            scan_type="time_out",
            schedule_session="morning"
        )
        assert result is True

    def test_complete_morning_then_afternoon(self, temp_db):
        """Test complete morning session then afternoon session"""
        student_id = "2021001"
        
        # Morning login
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo1.jpg",
            qr_data="2021001",
            scan_type="time_in",
            status="present",
            schedule_session="morning"
        )
        
        # Morning logout
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo2.jpg",
            qr_data="2021001",
            scan_type="time_out",
            status="present",
            schedule_session="morning"
        )
        
        # Afternoon login - should NOT be duplicate
        result = temp_db.check_duplicate_for_session(
            student_id=student_id,
            scan_type="time_in",
            schedule_session="afternoon"
        )
        assert result is False
        
        # Record afternoon login
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo3.jpg",
            qr_data="2021001",
            scan_type="time_in",
            status="present",
            schedule_session="afternoon"
        )
        
        # Try to login again for afternoon - should be duplicate
        result = temp_db.check_duplicate_for_session(
            student_id=student_id,
            scan_type="time_in",
            schedule_session="afternoon"
        )
        assert result is True

    def test_different_students_no_conflict(self, temp_db):
        """Test different students don't conflict"""
        # Student 1 login for morning
        temp_db.record_attendance(
            student_id="2021001",
            photo_path="photo1.jpg",
            qr_data="2021001",
            scan_type="time_in",
            status="present",
            schedule_session="morning"
        )
        
        # Student 2 login for morning - should NOT be duplicate
        result = temp_db.check_duplicate_for_session(
            student_id="2021002",
            scan_type="time_in",
            schedule_session="morning"
        )
        assert result is False

    def test_multiple_logins_prevented(self, temp_db):
        """Test multiple login attempts are all prevented after first"""
        student_id = "2021001"
        
        # First login - should succeed
        id1 = temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo1.jpg",
            qr_data="2021001",
            scan_type="time_in",
            status="present",
            schedule_session="morning"
        )
        assert id1 is not None
        
        # Second login attempt - should be duplicate
        is_dup = temp_db.check_duplicate_for_session(
            student_id=student_id,
            scan_type="time_in",
            schedule_session="morning"
        )
        assert is_dup is True
        
        # Third login attempt - should still be duplicate
        is_dup = temp_db.check_duplicate_for_session(
            student_id=student_id,
            scan_type="time_in",
            schedule_session="morning"
        )
        assert is_dup is True

    def test_both_sessions_independent(self, temp_db):
        """Test morning and afternoon sessions are independent"""
        student_id = "2021001"
        
        # Can login once for morning
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo1.jpg",
            qr_data="2021001",
            scan_type="time_in",
            status="present",
            schedule_session="morning"
        )
        
        # Can logout once for morning
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo2.jpg",
            qr_data="2021001",
            scan_type="time_out",
            status="present",
            schedule_session="morning"
        )
        
        # Can login once for afternoon
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo3.jpg",
            qr_data="2021001",
            scan_type="time_in",
            status="present",
            schedule_session="afternoon"
        )
        
        # Can logout once for afternoon
        temp_db.record_attendance(
            student_id=student_id,
            photo_path="photo4.jpg",
            qr_data="2021001",
            scan_type="time_out",
            status="present",
            schedule_session="afternoon"
        )
        
        # Now all should be duplicates
        assert temp_db.check_duplicate_for_session(student_id, "time_in", "morning") is True
        assert temp_db.check_duplicate_for_session(student_id, "time_out", "morning") is True
        assert temp_db.check_duplicate_for_session(student_id, "time_in", "afternoon") is True
        assert temp_db.check_duplicate_for_session(student_id, "time_out", "afternoon") is True
