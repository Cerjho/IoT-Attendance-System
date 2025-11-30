"""
Queue Data Validation
Validates sync queue data using JSON schema
"""
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class QueueDataValidator:
    """Validates queue data against expected schema"""

    # Schema for attendance records in queue
    ATTENDANCE_SCHEMA = {
        "required": ["status"],  # student_number OR student_id required, date OR timestamp required (checked separately)
        "optional": ["student_number", "student_id", "date", "time_in", "time_out", "photo_path", "device_id", "qr_data", "remarks", "timestamp", "scan_type", "id"],
        "types": {
            "student_number": (str, type(None)),
            "student_id": (str, type(None)),
            "date": (str, type(None)),
            "timestamp": (str, type(None)),
            "time_in": (str, type(None)),
            "time_out": (str, type(None)),
            "status": str,
            "scan_type": (str, type(None)),
            "photo_path": (str, type(None)),
            "device_id": (str, type(None)),
            "qr_data": (str, type(None)),
            "remarks": (str, type(None)),
            "id": (int, type(None)),
        },
        "status_values": ["present", "late", "absent", "excused"],
    }

    @staticmethod
    def validate_attendance(data: Any) -> tuple[bool, Optional[str]]:
        """
        Validate attendance data from queue

        Args:
            data: Data to validate (typically JSON string or dict)

        Returns:
            (is_valid, error_message)
        """
        try:
            # Parse JSON if string
            if isinstance(data, str):
                try:
                    data_dict = json.loads(data)
                except json.JSONDecodeError as e:
                    return False, f"Invalid JSON: {e}"
            elif isinstance(data, dict):
                data_dict = data
            else:
                return False, f"Data must be dict or JSON string, got {type(data)}"

            # Check required fields
            for field in QueueDataValidator.ATTENDANCE_SCHEMA["required"]:
                if field not in data_dict:
                    return False, f"Missing required field: {field}"
            
            # Either student_number or student_id must be present
            if "student_number" not in data_dict and "student_id" not in data_dict:
                return False, "Missing student identifier (student_number or student_id)"
            
            # Either date or timestamp must be present
            if "date" not in data_dict and "timestamp" not in data_dict:
                return False, "Missing date/time information (date or timestamp required)"

            # Check types
            for field, expected_type in QueueDataValidator.ATTENDANCE_SCHEMA["types"].items():
                if field in data_dict and data_dict[field] is not None:
                    if not isinstance(data_dict[field], expected_type):
                        return False, f"Field '{field}' has wrong type: expected {expected_type}, got {type(data_dict[field])}"

            # Validate status value
            status = data_dict.get("status")
            if status not in QueueDataValidator.ATTENDANCE_SCHEMA["status_values"]:
                return False, f"Invalid status value: {status}"

            # Validate date format (basic check) - allow None for timestamp-based records
            date = data_dict.get("date", "")
            if date and not (len(date) == 10 and date[4] == "-" and date[7] == "-"):
                return False, f"Invalid date format (expected YYYY-MM-DD): {date}"

            # Validate time format if present
            for time_field in ["time_in", "time_out"]:
                time_val = data_dict.get(time_field)
                if time_val and not QueueDataValidator._is_valid_time(time_val):
                    return False, f"Invalid time format for {time_field} (expected HH:MM:SS): {time_val}"

            return True, None

        except Exception as e:
            return False, f"Validation error: {e}"

    @staticmethod
    def _is_valid_time(time_str: str) -> bool:
        """Check if time string is in HH:MM:SS format"""
        if not isinstance(time_str, str):
            return False
        parts = time_str.split(":")
        if len(parts) != 3:
            return False
        try:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return 0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59
        except ValueError:
            return False

    @staticmethod
    def sanitize_attendance(data: Dict) -> Dict:
        """
        Sanitize attendance data by removing invalid fields

        Args:
            data: Raw attendance data

        Returns:
            Sanitized data with only valid fields
        """
        sanitized = {}
        all_fields = (
            QueueDataValidator.ATTENDANCE_SCHEMA["required"]
            + QueueDataValidator.ATTENDANCE_SCHEMA["optional"]
        )

        for field in all_fields:
            if field in data:
                sanitized[field] = data[field]

        return sanitized

    @staticmethod
    def validate_and_fix(data: Any) -> tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate and attempt to fix common issues

        Args:
            data: Data to validate

        Returns:
            (is_valid, fixed_data, error_message)
        """
        # Parse data first
        if isinstance(data, str):
            try:
                data_dict = json.loads(data)
            except json.JSONDecodeError:
                return False, None, "Invalid JSON"
        else:
            data_dict = dict(data)
        
        # Always sanitize to remove invalid fields
        data_dict = QueueDataValidator.sanitize_attendance(data_dict)
        
        # Try validation on sanitized data
        is_valid, error = QueueDataValidator.validate_attendance(data_dict)
        if is_valid:
            return True, data_dict, None

        # Try to fix common issues (data_dict already sanitized above)
        try:
            # Fix missing required fields with defaults
            if "student_number" not in data_dict and "student_id" not in data_dict:
                return False, None, "Cannot fix: missing student identifier"
            # date field is optional if timestamp is present
            if "status" not in data_dict:
                # Default to 'present'
                data_dict["status"] = "present"
                logger.warning("Fixed missing status, defaulting to 'present'")

            # Validate again
            is_valid, error = QueueDataValidator.validate_attendance(data_dict)
            if is_valid:
                return True, data_dict, None
            else:
                return False, None, f"Could not fix: {error}"

        except Exception as e:
            return False, None, f"Fix attempt failed: {e}"
