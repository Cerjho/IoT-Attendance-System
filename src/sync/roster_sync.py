#!/usr/bin/env python3
"""
Daily Roster Sync Module
Downloads student roster from Supabase and caches locally for fast offline scanning
Works with new Supabase schema (students table with student_number, first_name, last_name, etc.)
Implements lightning-fast lookup (< 100ms) with 100% offline capability
"""

import json
import logging
import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class RosterSyncManager:
    """
    Manages daily roster synchronization from Supabase to local SQLite cache

    Architecture:
    - Supabase = Primary database (source of truth)
    - SQLite = Temporary cache (wiped daily)
    - Downloads only today's roster (30-100 students)
    - Ultra-fast local lookups during scanning
    - 100% offline capability after initial sync
    """

    def __init__(self, config: Dict, db_path: str = "data/attendance.db"):
        """
        Initialize roster sync manager

        Args:
            config: Configuration dictionary with cloud settings
            db_path: Path to local SQLite database
        """
        self.config = config
        self.db_path = db_path

        # Supabase configuration
        self.enabled = config.get("enabled", False)
        self.supabase_url = config.get("url")
        self.supabase_key = config.get("api_key")
        self.device_id = config.get("device_id", "device_001")

        # Roster settings
        roster_config = config.get("roster_sync", {})
        self.auto_sync_on_boot = roster_config.get("auto_sync_on_boot", True)
        self.sync_time = roster_config.get("sync_time", "06:00")  # Daily sync time
        self.cache_expiry_hours = roster_config.get("cache_expiry_hours", 24)
        self.auto_wipe_after_class = roster_config.get("auto_wipe_after_class", False)
        self.class_end_time = roster_config.get("class_end_time", "18:00")

        # State tracking
        self.last_sync_date = None
        self.cached_student_count = 0
        self.sync_in_progress = False

        if self.enabled and not (self.supabase_url and self.supabase_key):
            logger.warning("Supabase credentials not configured - roster sync disabled")
            self.enabled = False

        logger.info(f"Roster sync manager initialized (enabled={self.enabled})")

    def download_today_roster(self, force: bool = False) -> Dict:
        """
        Download today's student roster from Supabase

        Args:
            force: Force sync even if already synced today

        Returns:
            Dictionary with sync results:
                - success: bool
                - students_synced: int
                - message: str
                - cached_count: int
        """
        if not self.enabled:
            return {
                "success": False,
                "students_synced": 0,
                "message": "Roster sync disabled",
                "cached_count": 0,
            }

        if self.sync_in_progress:
            return {
                "success": False,
                "students_synced": 0,
                "message": "Sync already in progress",
                "cached_count": self.cached_student_count,
            }

        # Check if already synced today
        today = date.today().isoformat()
        if not force and self.last_sync_date == today:
            logger.info(
                f"Roster already synced today ({self.cached_student_count} students)"
            )
            return {
                "success": True,
                "students_synced": self.cached_student_count,
                "message": f"Already synced today ({self.cached_student_count} students cached)",
                "cached_count": self.cached_student_count,
            }

        self.sync_in_progress = True
        logger.info("📥 Starting daily roster sync from Supabase...")

        try:
            # Download student roster from Supabase
            students = self._fetch_roster_from_supabase()

            if students is None:
                raise Exception("Failed to fetch roster from Supabase")

            # Clear old cache
            self._clear_student_cache()

            # Load students into local cache
            synced_count = self._cache_students_locally(students)

            # Update sync state
            self.last_sync_date = today
            self.cached_student_count = synced_count
            self._update_sync_metadata(today, synced_count)

            logger.info(
                f"✅ Roster sync complete: {synced_count} students cached for today"
            )

            return {
                "success": True,
                "students_synced": synced_count,
                "message": f"Successfully synced {synced_count} students for today",
                "cached_count": synced_count,
            }

        except Exception as e:
            logger.error(f"Roster sync failed: {e}")
            return {
                "success": False,
                "students_synced": 0,
                "message": f"Sync failed: {str(e)}",
                "cached_count": self.cached_student_count,
            }

        finally:
            self.sync_in_progress = False

    def _fetch_roster_from_supabase(self) -> Optional[List[Dict]]:
        """
        Fetch student roster from Supabase (NEW SCHEMA)

        New schema fields:
        - student_number (primary identifier)
        - first_name, middle_name, last_name
        - parent_guardian_contact (phone)
        - email, grade_level, section
        - status (active/inactive)

        Returns:
            List of student dictionaries or None on failure
        """
        try:
            # Query students table from Supabase
            url = f"{self.supabase_url}/rest/v1/students"
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
            }

            # Fetch active students with all needed fields (including id for UUID)
            # Note: Only fetch fields needed for local validation and display
            # Context fields (section_id, subject_id, teaching_load_id) are determined by backend
            # Now includes schedule data via sections left join (students without sections still included)
            params = {
                "select": "id,student_number,first_name,middle_name,last_name,email,parent_guardian_contact,grade_level,section,section_id,sections(schedule_id,school_schedules(morning_start_time,afternoon_start_time)),status",
                "status": "eq.active",  # Only active students
            }

            logger.debug(f"Fetching roster from: {url}")
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                try:
                    students = response.json()
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response from roster sync: {response.text[:200]}")
                    return None
                    
                logger.info(
                    f"📥 Downloaded {len(students)} active students from new Supabase server"
                )
                return students
            else:
                logger.error(
                    f"Supabase API error: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error fetching roster from Supabase: {e}")
            return None

    def _clear_student_cache(self):
        """Clear old student cache (wipe before fresh sync)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Delete all students (cache only)
            cursor.execute("DELETE FROM students")

            conn.commit()
            conn.close()

            logger.info("🗑️  Student cache cleared")

        except Exception as e:
            logger.error(f"Error clearing student cache: {e}")

    def _cache_students_locally(self, students: List[Dict]) -> int:
        """
        Cache downloaded students in local SQLite (adapted for new schema)

        Maps new schema fields to local cache:
        - student_number → student_id (local cache uses student_id)
        - first_name + middle_name + last_name → name
        - parent_guardian_contact → parent_phone

        Args:
            students: List of student dictionaries from Supabase

        Returns:
            Number of students cached
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            synced_count = 0
            for student in students:
                # Map new schema to local cache fields
                student_uuid = student.get("id")  # UUID from Supabase
                student_number = student.get("student_number")
                first_name = student.get("first_name", "")
                middle_name = student.get("middle_name", "")
                last_name = student.get("last_name", "")
                email = student.get("email")
                parent_phone = student.get("parent_guardian_contact")

                if not student_number:
                    continue

                # Build full name
                name_parts = [first_name, middle_name, last_name]
                full_name = " ".join([part for part in name_parts if part]).strip()

                # Extract schedule information from joined sections table
                section_id = student.get("section_id")
                schedule_id = None
                allowed_session = "both"  # Default: allow both sessions if no schedule
                
                # Parse nested sections data
                sections_data = student.get("sections")
                if sections_data and isinstance(sections_data, dict):
                    schedule_id = sections_data.get("schedule_id")
                    schedules_data = sections_data.get("school_schedules")
                    
                    if schedules_data and isinstance(schedules_data, dict):
                        # Determine allowed session based on schedule times
                        morning_start = schedules_data.get("morning_start_time")
                        afternoon_start = schedules_data.get("afternoon_start_time")
                        
                        # If both times exist, student can attend both sessions
                        # If only one exists, restrict to that session
                        if morning_start and afternoon_start:
                            allowed_session = "both"
                        elif morning_start:
                            allowed_session = "morning"
                        elif afternoon_start:
                            allowed_session = "afternoon"

                # Store in local cache with UUID (using student_id field for compatibility)
                # First ensure columns exist
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS students (
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
                    """
                )
                
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO students (student_id, uuid, name, email, parent_phone, section_id, schedule_id, allowed_session, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        student_number,
                        student_uuid,
                        full_name,
                        email,
                        parent_phone,
                        section_id,
                        schedule_id,
                        allowed_session,
                        datetime.now().isoformat(),
                    ),
                )

                synced_count += 1

            conn.commit()
            conn.close()

            logger.info(f"💾 Cached {synced_count} students locally")
            return synced_count

        except Exception as e:
            logger.error(f"Error caching students: {e}")
            return 0

    def _update_sync_metadata(self, sync_date: str, student_count: int):
        """Update sync metadata in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create metadata table if not exists
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS roster_sync_metadata (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_sync_date TEXT,
                    last_sync_timestamp TEXT,
                    student_count INTEGER,
                    device_id TEXT
                )
            """
            )

            # Insert or update metadata
            cursor.execute(
                """
                INSERT OR REPLACE INTO roster_sync_metadata (id, last_sync_date, last_sync_timestamp, student_count, device_id)
                VALUES (1, ?, ?, ?, ?)
            """,
                (sync_date, datetime.now().isoformat(), student_count, self.device_id),
            )

            conn.commit()
            conn.close()

            logger.debug(
                f"Sync metadata updated: {sync_date}, {student_count} students"
            )

        except Exception as e:
            logger.error(f"Error updating sync metadata: {e}")

    def get_cached_student(self, student_id: str) -> Optional[Dict]:
        """
        Fast lookup of student from local cache

        Args:
            student_id: Student ID to lookup

        Returns:
            Student dictionary or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT student_id, uuid, name, email, parent_phone, created_at
                FROM students 
                WHERE student_id = ?
            """,
                (student_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Error getting cached student: {e}")
            return None

    def is_student_in_roster(self, student_id: str) -> bool:
        """
        Fast check if student is in today's roster (cached)

        Args:
            student_id: Student ID to check

        Returns:
            True if student in roster, False otherwise
        """
        student = self.get_cached_student(student_id)
        return student is not None

    def get_cache_info(self) -> Dict:
        """
        Get information about current cache state

        Returns:
            Dictionary with cache info
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get cached student count
            cursor.execute("SELECT COUNT(*) FROM students")
            student_count = cursor.fetchone()[0]

            # Get sync metadata
            cursor.execute(
                """
                SELECT last_sync_date, last_sync_timestamp, device_id
                FROM roster_sync_metadata
                WHERE id = 1
            """
            )

            metadata = cursor.fetchone()
            conn.close()

            if metadata:
                last_sync_date, last_sync_timestamp, device_id = metadata
            else:
                last_sync_date = None
                last_sync_timestamp = None
                device_id = self.device_id

            # Check if sync needed
            today = date.today().isoformat()
            sync_needed = last_sync_date != today

            return {
                "enabled": self.enabled,
                "cached_students": student_count,
                "last_sync_date": last_sync_date,
                "last_sync_timestamp": last_sync_timestamp,
                "sync_needed": sync_needed,
                "device_id": device_id,
                "supabase_url": self.supabase_url,
            }

        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            return {"enabled": self.enabled, "cached_students": 0, "sync_needed": True}

    def wipe_roster_cache(self) -> bool:
        """
        Wipe student roster cache (for privacy/security)
        Called after class ends or on demand

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("🗑️  Wiping student roster cache for privacy compliance...")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Delete all cached students
            cursor.execute("DELETE FROM students")
            deleted_count = cursor.rowcount

            # Update metadata
            cursor.execute(
                """
                UPDATE roster_sync_metadata 
                SET student_count = 0
                WHERE id = 1
            """
            )

            conn.commit()
            conn.close()

            self.cached_student_count = 0

            logger.info(
                f"✅ Roster cache wiped: {deleted_count} students removed for privacy"
            )
            return True

        except Exception as e:
            logger.error(f"Error wiping roster cache: {e}")
            return False

    def should_sync_now(self) -> bool:
        """
        Check if roster should be synced now

        Returns:
            True if sync is needed
        """
        # Always need sync if never synced
        if self.last_sync_date is None:
            return True

        # Check if date changed
        today = date.today().isoformat()
        if self.last_sync_date != today:
            return True

        return False

    def auto_sync_on_startup(self) -> Dict:
        """
        Automatically sync roster when system starts

        Returns:
            Sync results dictionary
        """
        if not self.auto_sync_on_boot:
            logger.info("Auto-sync on boot disabled")
            return {"success": False, "message": "Auto-sync disabled"}

        logger.info("🚀 Auto-syncing roster on system startup...")
        return self.download_today_roster(force=False)

    def schedule_daily_wipe(self):
        """
        Schedule automatic roster wipe after class ends
        (To be called from a scheduler/timer)
        """
        if not self.auto_wipe_after_class:
            return

        # Check if it's past class end time
        now = datetime.now().time()
        class_end = datetime.strptime(self.class_end_time, "%H:%M").time()

        if now >= class_end:
            logger.info("Class ended - auto-wiping roster cache")
            self.wipe_roster_cache()
