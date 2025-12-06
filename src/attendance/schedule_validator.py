#!/usr/bin/env python3
"""
Student Schedule Validator
Validates student attendance scans against their assigned schedules
Prevents students from scanning during wrong sessions (e.g., afternoon student scanning in morning)
"""

import logging
import sqlite3
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Schedule validation results"""
    VALID = "valid"  # Student allowed in this session
    WRONG_SESSION = "wrong_session"  # Student assigned to different session
    NO_SCHEDULE = "no_schedule"  # Student has no schedule assigned
    NOT_FOUND = "not_found"  # Student not found in roster
    ERROR = "error"  # Validation error


class ScheduleValidator:
    """
    Validates student scans against their assigned schedules
    
    Rules:
    - Students with "morning" schedule can only scan during morning sessions
    - Students with "afternoon" schedule can only scan during afternoon sessions
    - Students with "both" schedule can scan anytime
    - Students with no schedule are allowed (backward compatibility)
    """

    def __init__(self, db_path: str = "data/attendance.db"):
        """
        Initialize schedule validator

        Args:
            db_path: Path to local SQLite database with student cache
        """
        self.db_path = db_path
        logger.info("Schedule validator initialized")

    def validate_student_schedule(
        self, 
        student_id: str, 
        current_session: str
    ) -> Tuple[ValidationResult, Optional[Dict]]:
        """
        Validate if student is allowed to scan in current session

        Args:
            student_id: Student number (e.g., "2021001")
            current_session: Current detected session ("morning", "afternoon", "unknown")

        Returns:
            Tuple of (ValidationResult, details_dict)
            details_dict contains:
                - student_name: Student's full name
                - allowed_session: Student's assigned session
                - current_session: Current detected session
                - message: Human-readable validation message
        """
        try:
            # Lookup student schedule from local cache
            student_data = self._get_student_schedule(student_id)

            if not student_data:
                return (
                    ValidationResult.NOT_FOUND,
                    {
                        "student_id": student_id,
                        "current_session": current_session,
                        "message": f"Student {student_id} not found in roster cache",
                    },
                )

            student_name = student_data.get("name", "Unknown")
            allowed_session = student_data.get("allowed_session", "both")
            section_id = student_data.get("section_id")
            schedule_id = student_data.get("schedule_id")

            # If current session is unknown (outside schedule windows), reject
            if current_session == "unknown":
                return (
                    ValidationResult.WRONG_SESSION,
                    {
                        "student_id": student_id,
                        "student_name": student_name,
                        "allowed_session": allowed_session,
                        "current_session": current_session,
                        "message": f"⏰ Outside scheduled class hours",
                    },
                )

            # Handle students without schedule assignment
            if not allowed_session or allowed_session == "both":
                logger.debug(
                    f"Student {student_id} ({student_name}) has no schedule restriction - allowing scan"
                )
                return (
                    ValidationResult.VALID,
                    {
                        "student_id": student_id,
                        "student_name": student_name,
                        "allowed_session": "both",
                        "current_session": current_session,
                        "section_id": section_id,
                        "schedule_id": schedule_id,
                        "message": "✅ Valid scan (no schedule restriction)",
                    },
                )

            # Check if student's session matches current session
            if allowed_session.lower() != current_session.lower():
                # SCHEDULE MISMATCH - REJECT
                session_name = allowed_session.upper()
                logger.warning(
                    f"❌ SCHEDULE VIOLATION: Student {student_id} ({student_name}) "
                    f"assigned to {session_name} class tried to scan during {current_session.upper()} session"
                )
                return (
                    ValidationResult.WRONG_SESSION,
                    {
                        "student_id": student_id,
                        "student_name": student_name,
                        "allowed_session": allowed_session,
                        "current_session": current_session,
                        "section_id": section_id,
                        "schedule_id": schedule_id,
                        "message": f"❌ Wrong schedule! Student assigned to {session_name} class",
                    },
                )

            # VALID - Session matches
            logger.info(
                f"✅ Schedule validated: {student_id} ({student_name}) - {current_session.upper()} session"
            )
            return (
                ValidationResult.VALID,
                {
                    "student_id": student_id,
                    "student_name": student_name,
                    "allowed_session": allowed_session,
                    "current_session": current_session,
                    "section_id": section_id,
                    "schedule_id": schedule_id,
                    "message": f"✅ Valid {current_session.upper()} session scan",
                },
            )

        except Exception as e:
            logger.error(f"Schedule validation error for {student_id}: {e}")
            return (
                ValidationResult.ERROR,
                {
                    "student_id": student_id,
                    "current_session": current_session,
                    "message": f"Validation error: {str(e)}",
                },
            )

    def _get_student_schedule(self, student_id: str) -> Optional[Dict]:
        """
        Lookup student schedule from local cache

        Args:
            student_id: Student number

        Returns:
            Dictionary with student data or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT student_id, uuid, name, email, parent_phone, 
                       section_id, schedule_id, allowed_session
                FROM students
                WHERE student_id = ?
                """,
                (student_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "student_id": row["student_id"],
                    "uuid": row["uuid"],
                    "name": row["name"],
                    "email": row["email"],
                    "parent_phone": row["parent_phone"],
                    "section_id": row["section_id"],
                    "schedule_id": row["schedule_id"],
                    "allowed_session": row["allowed_session"],
                }

            return None

        except Exception as e:
            logger.error(f"Error fetching student schedule from cache: {e}")
            return None

    def get_schedule_stats(self) -> Dict:
        """
        Get statistics about cached student schedules

        Returns:
            Dictionary with schedule distribution stats
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Count students by allowed_session
            cursor.execute(
                """
                SELECT 
                    COALESCE(allowed_session, 'none') as session,
                    COUNT(*) as count
                FROM students
                GROUP BY allowed_session
                """
            )

            rows = cursor.fetchall()
            conn.close()

            stats = {
                "total": 0,
                "morning": 0,
                "afternoon": 0,
                "both": 0,
                "none": 0,
            }

            for row in rows:
                session = row[0] or "none"
                count = row[1]
                stats["total"] += count
                if session in stats:
                    stats[session] = count

            return stats

        except Exception as e:
            logger.error(f"Error fetching schedule stats: {e}")
            return {"total": 0, "error": str(e)}


def validate_schedule(
    student_id: str, 
    current_session: str, 
    db_path: str = "data/attendance.db"
) -> Tuple[ValidationResult, Dict]:
    """
    Convenience function for quick schedule validation

    Args:
        student_id: Student number
        current_session: Current session ("morning", "afternoon", "unknown")
        db_path: Path to database

    Returns:
        Tuple of (ValidationResult, details_dict)
    """
    validator = ScheduleValidator(db_path)
    return validator.validate_student_schedule(student_id, current_session)
