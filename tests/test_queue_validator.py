"""
Tests for Queue Data Validation
"""
import json

import pytest

from src.utils.queue_validator import QueueDataValidator


def test_valid_attendance_data():
    """Test validation passes for valid data"""
    data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "time_in": "07:30:00",
        "status": "present",
    }

    is_valid, error = QueueDataValidator.validate_attendance(data)
    assert is_valid
    assert error is None


def test_valid_attendance_json_string():
    """Test validation works with JSON string"""
    data = json.dumps({
        "student_number": "2021001",
        "date": "2025-01-01",
        "time_in": "07:30:00",
        "status": "present",
    })

    is_valid, error = QueueDataValidator.validate_attendance(data)
    assert is_valid
    assert error is None


def test_missing_required_field():
    """Test validation fails for missing required field"""
    data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        # Missing status
    }

    is_valid, error = QueueDataValidator.validate_attendance(data)
    assert not is_valid
    assert "status" in error


def test_invalid_status_value():
    """Test validation fails for invalid status"""
    data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "status": "invalid_status",
    }

    is_valid, error = QueueDataValidator.validate_attendance(data)
    assert not is_valid
    assert "status" in error.lower()


def test_invalid_date_format():
    """Test validation fails for invalid date format"""
    data = {
        "student_number": "2021001",
        "date": "01/01/2025",  # Wrong format
        "status": "present",
    }

    is_valid, error = QueueDataValidator.validate_attendance(data)
    assert not is_valid
    assert "date" in error.lower()


def test_invalid_time_format():
    """Test validation fails for invalid time format"""
    data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "time_in": "7:30",  # Missing seconds
        "status": "present",
    }

    is_valid, error = QueueDataValidator.validate_attendance(data)
    assert not is_valid
    assert "time" in error.lower()


def test_wrong_field_type():
    """Test validation fails for wrong field type"""
    data = {
        "student_number": 2021001,  # Should be string
        "date": "2025-01-01",
        "status": "present",
    }

    is_valid, error = QueueDataValidator.validate_attendance(data)
    assert not is_valid
    assert "type" in error.lower()


def test_invalid_json():
    """Test validation fails for invalid JSON"""
    data = "{not valid json}"

    is_valid, error = QueueDataValidator.validate_attendance(data)
    assert not is_valid
    assert "JSON" in error


def test_sanitize_attendance():
    """Test sanitization removes invalid fields"""
    data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "status": "present",
        "invalid_field": "should be removed",
        "another_invalid": 123,
    }

    sanitized = QueueDataValidator.sanitize_attendance(data)

    assert "student_number" in sanitized
    assert "date" in sanitized
    assert "status" in sanitized
    assert "invalid_field" not in sanitized
    assert "another_invalid" not in sanitized


def test_validate_and_fix_valid():
    """Test validate_and_fix returns valid data unchanged"""
    data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "status": "present",
    }

    is_valid, fixed, error = QueueDataValidator.validate_and_fix(data)
    assert is_valid
    assert fixed == data
    assert error is None


def test_validate_and_fix_missing_status():
    """Test validate_and_fix adds default status"""
    data = {
        "student_number": "2021001",
        "date": "2025-01-01",
    }

    is_valid, fixed, error = QueueDataValidator.validate_and_fix(data)
    assert is_valid
    assert fixed["status"] == "present"
    assert error is None


def test_validate_and_fix_removes_invalid_fields():
    """Test validate_and_fix removes invalid fields"""
    data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "status": "present",
        "bad_field": "remove me",
    }

    is_valid, fixed, error = QueueDataValidator.validate_and_fix(data)
    assert is_valid
    assert "bad_field" not in fixed


def test_validate_and_fix_cannot_fix():
    """Test validate_and_fix fails when data cannot be fixed"""
    data = {
        "date": "2025-01-01",  # Missing student_number/student_id
        "status": "present",
    }

    is_valid, fixed, error = QueueDataValidator.validate_and_fix(data)
    assert not is_valid
    assert fixed is None
    assert "student" in error.lower()  # Should mention student identifier


def test_optional_fields():
    """Test optional fields are accepted"""
    data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "status": "present",
        "time_in": "07:30:00",
        "time_out": None,
        "photo_path": "/path/to/photo.jpg",
        "device_id": "pi-lab-01",
        "qr_data": "QR:2021001",
        "remarks": "Test remark",
    }

    is_valid, error = QueueDataValidator.validate_attendance(data)
    assert is_valid
    assert error is None


def test_all_status_values():
    """Test all valid status values"""
    statuses = ["present", "late", "absent", "excused"]

    for status in statuses:
        data = {
            "student_number": "2021001",
            "date": "2025-01-01",
            "status": status,
        }
        is_valid, error = QueueDataValidator.validate_attendance(data)
        assert is_valid, f"Status '{status}' should be valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
