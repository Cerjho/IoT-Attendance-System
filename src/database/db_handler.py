#!/usr/bin/env python3
"""
Database Handler for Attendance System
Uses SQLite for local storage
"""
import json
import logging
import os
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AttendanceDatabase:
    """Handle attendance database operations"""

    def __init__(self, db_path: str = "data/attendance.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self._lock = threading.Lock()  # Thread safety for concurrent access

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize database
        self._init_database()
        logger.info(f"Database initialized: {db_path}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False

    def _init_database(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Students table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                uuid TEXT,
                name TEXT,
                email TEXT,
                parent_phone TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Attendance records table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                photo_path TEXT,
                qr_data TEXT,
                scan_type TEXT DEFAULT 'time_in',
                status TEXT DEFAULT 'present',
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            )
        """
        )

        # Sessions table (for grouping attendance by session/class)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT,
                start_time TEXT,
                end_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

        logger.info("Database tables initialized")

    def add_student(
        self,
        student_id: str,
        name: str = None,
        email: str = None,
        parent_phone: str = None,
    ) -> bool:
        """Add or update student record"""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO students (student_id, name, email, parent_phone)
                    VALUES (?, ?, ?, ?)
                """,
                    (student_id, name, email, parent_phone),
                )

                conn.commit()
                conn.close()

                logger.debug(f"Student added/updated: {student_id}")
                return True

            except Exception as e:
                logger.error(f"Error adding student: {str(e)}")
                return False

    def record_attendance(
        self,
        student_id: str,
        photo_path: str,
        qr_data: str = None,
        scan_type: str = "time_in",
        status: str = "present",
    ) -> Optional[int]:
        """
        Record attendance entry
        Args:
            student_id: Student identifier
            photo_path: Path to captured photo
            qr_data: QR code data
            scan_type: 'time_in' for login or 'time_out' for logout
            status: 'present', 'late', 'absent', 'excused'
        Returns: attendance record ID or None on failure
        """
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                timestamp = datetime.now().isoformat()

                cursor.execute(
                    """
                    INSERT INTO attendance (student_id, timestamp, photo_path, qr_data, scan_type, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (student_id, timestamp, photo_path, qr_data, scan_type, status),
                )

                record_id = cursor.lastrowid

                conn.commit()
                conn.close()

                logger.info(
                    f"Attendance recorded: {student_id} (ID: {record_id}, type: {scan_type}, status: {status})"
                )
                return record_id

            except Exception as e:
                logger.error(f"Error recording attendance: {str(e)}")
                return None

    def get_student(self, student_id: str) -> Optional[Dict]:
        """Get student information"""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM students WHERE student_id = ?
                """,
                    (student_id,),
                )

                row = cursor.fetchone()
                conn.close()

                if row:
                    return dict(row)
                return None

            except Exception as e:
                logger.error(f"Error getting student: {str(e)}")
                return None

    def get_today_attendance(self) -> List[Dict]:
        """Get all attendance records for today"""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                today = datetime.now().date().isoformat()

                cursor.execute(
                    """
                    SELECT a.*, s.name 
                    FROM attendance a
                    LEFT JOIN students s ON a.student_id = s.student_id
                    WHERE date(a.timestamp) = ?
                    ORDER BY a.timestamp DESC
                """,
                    (today,),
                )

                rows = cursor.fetchall()
                conn.close()

                return [dict(row) for row in rows]

            except Exception as e:
                logger.error(f"Error getting today's attendance: {str(e)}")
                return []

    def check_already_scanned_today(
        self, student_id: str, scan_type: str = None
    ) -> bool:
        """Check if student already scanned today for specific scan type"""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                today = datetime.now().date().isoformat()

                if scan_type:
                    # Check for specific scan type
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM attendance
                        WHERE student_id = ? AND date(timestamp) = ? AND scan_type = ?
                    """,
                        (student_id, today, scan_type),
                    )
                else:
                    # Check any scan today
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM attendance
                        WHERE student_id = ? AND date(timestamp) = ?
                    """,
                        (student_id, today),
                    )

                count = cursor.fetchone()[0]
                conn.close()

                return count > 0

            except Exception as e:
                logger.error(f"Error checking attendance: {str(e)}")
                return False

    def get_last_scan(self, student_id: str) -> Optional[Dict]:
        """Get student's last scan record for today"""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                today = datetime.now().date().isoformat()

                cursor.execute(
                    """
                    SELECT * FROM attendance
                    WHERE student_id = ? AND date(timestamp) = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """,
                    (student_id, today),
                )

                row = cursor.fetchone()
                conn.close()

                if row:
                    return dict(row)
                return None

            except Exception as e:
                logger.error(f"Error getting last scan: {str(e)}")
                return None

    def get_statistics(self) -> Dict:
        """Get attendance statistics"""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Total students
                cursor.execute("SELECT COUNT(*) FROM students")
                total_students = cursor.fetchone()[0]

                # Total attendance records
                cursor.execute("SELECT COUNT(*) FROM attendance")
                total_records = cursor.fetchone()[0]

                # Today's attendance
                today = datetime.now().date().isoformat()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM attendance
                    WHERE date(timestamp) = ?
                """,
                    (today,),
                )
                today_count = cursor.fetchone()[0]

                conn.close()

                return {
                    "total_students": total_students,
                    "total_records": total_records,
                    "today_attendance": today_count,
                }

            except Exception as e:
                logger.error(f"Error getting statistics: {str(e)}")
                return {}

    def export_to_json(self, output_path: str = None) -> str:
        """Export all data to JSON file"""
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"data/attendance_export_{timestamp}.json"

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get all data
            cursor.execute("SELECT * FROM students")
            students = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT * FROM attendance ORDER BY timestamp DESC")
            attendance = [dict(row) for row in cursor.fetchall()]

            conn.close()

            data = {
                "export_date": datetime.now().isoformat(),
                "statistics": self.get_statistics(),
                "students": students,
                "attendance": attendance,
            }

            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Data exported to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            return None

    def close(self):
        """Close database connection (for cleanup)"""
        logger.info("Database handler closed")
