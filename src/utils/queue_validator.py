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
        "optional": ["student_number", "student_id", "date", "time_in", "time_out", "photo_path", "photo_url", "device_id", "qr_data", "remarks", "timestamp", "scan_type", "id", "section_id", "subject_id", "teaching_load_id", "recorded_by"],
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
            "photo_url": (str, type(None)),
            "device_id": (str, type(None)),
            "qr_data": (str, type(None)),
            "remarks": (str, type(None)),
            "id": (int, type(None)),
            "section_id": (str, type(None)),
            "subject_id": (str, type(None)),
            "teaching_load_id": (str, type(None)),
            "recorded_by": (str, type(None)),
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
            
            # Validate UUID format for UUID fields (but skip student_id as it can be student_number)
            # Note: Local queue uses student_id field to store student_number (not UUID)
            # The cloud sync converts student_number to UUID during sync
            uuid_fields = ["section_id", "subject_id", "teaching_load_id", "recorded_by"]
            for uuid_field in uuid_fields:
                uuid_val = data_dict.get(uuid_field)
                if uuid_val and not QueueDataValidator._is_valid_uuid(uuid_val):
                    return False, f"Invalid UUID format for {uuid_field}: {uuid_val}"
            
            # Validate device_id format (alphanumeric + hyphens/underscores)
            device_id = data_dict.get("device_id")
            if device_id and not QueueDataValidator._is_valid_device_id(device_id):
                return False, f"Invalid device_id format (alphanumeric + hyphens/underscores only): {device_id}"

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
    def _is_valid_uuid(uuid_str: str) -> bool:
        """Check if string is valid UUID format (8-4-4-4-12 hex digits)"""
        if not isinstance(uuid_str, str):
            return False
        import re
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        return bool(re.match(uuid_pattern, uuid_str))
    
    @staticmethod
    def _is_valid_device_id(device_id: str) -> bool:
        """Check if device_id contains only alphanumeric characters, hyphens, and underscores"""
        if not isinstance(device_id, str) or len(device_id) == 0:
            return False
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', device_id))

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
