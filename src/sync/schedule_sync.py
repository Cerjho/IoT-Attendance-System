#!/usr/bin/env python3
"""
Schedule Sync Module
Fetches school schedules from Supabase server
"""

import logging
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

import requests

from src.utils.logging_factory import get_logger

logger = get_logger(__name__)


class ScheduleSync:
    """
    Syncs school schedules from Supabase server to local cache
    """

    def __init__(self, config: Dict, db_path: str = "data/attendance.db"):
        """
        Initialize schedule sync

        Args:
            config: Configuration dictionary with Supabase credentials
            db_path: Path to local SQLite database
        """
        self.config = config
        self.db_path = db_path
        
        # Get Supabase credentials - try cloud config first, then cloud.supabase
        cloud_config = config.get("cloud", {})
        
        # Support both config.cloud.url and config.cloud.supabase.url structures
        if "url" in cloud_config:
            self.supabase_url = cloud_config.get("url", "")
            self.supabase_key = cloud_config.get("api_key", "")
        else:
            supabase_config = cloud_config.get("supabase", {})
            self.supabase_url = supabase_config.get("url", "")
            self.supabase_key = supabase_config.get("api_key", "")
        
        # Validate credentials
        if not self.supabase_url or self.supabase_url.startswith("${"):
            logger.warning("Supabase URL not configured for schedule sync")
            self.enabled = False
        elif not self.supabase_key or self.supabase_key.startswith("${"):
            logger.warning("Supabase API key not configured for schedule sync")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Schedule sync enabled with URL: {self.supabase_url[:30]}...")
            
        # Initialize local database
        self._init_local_db()

    def _init_local_db(self):
        """Initialize local cache table for schedules"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS school_schedules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    morning_start_time TEXT NOT NULL,
                    morning_end_time TEXT NOT NULL,
                    morning_login_window_start TEXT NOT NULL,
                    morning_login_window_end TEXT NOT NULL,
                    morning_logout_window_start TEXT NOT NULL,
                    morning_logout_window_end TEXT NOT NULL,
                    morning_late_threshold_minutes INTEGER NOT NULL,
                    afternoon_start_time TEXT NOT NULL,
                    afternoon_end_time TEXT NOT NULL,
                    afternoon_login_window_start TEXT NOT NULL,
                    afternoon_login_window_end TEXT NOT NULL,
                    afternoon_logout_window_start TEXT NOT NULL,
                    afternoon_logout_window_end TEXT NOT NULL,
                    afternoon_late_threshold_minutes INTEGER NOT NULL,
                    auto_detect_session INTEGER NOT NULL,
                    allow_early_arrival INTEGER NOT NULL,
                    require_logout INTEGER NOT NULL,
                    duplicate_scan_cooldown_minutes INTEGER NOT NULL,
                    is_default INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    synced_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
            conn.close()
            logger.debug("School schedules cache table initialized")
            
        except Exception as e:
            logger.error(f"Error initializing schedules cache: {e}")

    def sync_schedules(self) -> bool:
        """
        Fetch schedules from Supabase and cache locally

        Returns:
            bool: True if sync successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Schedule sync disabled")
            return False

        try:
            # Fetch active schedules from Supabase
            url = f"{self.supabase_url}/rest/v1/school_schedules"
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
            }
            params = {
                "status": "eq.active",
                "select": "*",
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code != 200:
                logger.error(
                    f"Failed to fetch schedules from Supabase: {response.status_code}"
                )
                return False

            schedules = response.json()

            if not schedules:
                logger.warning("No active schedules found in Supabase")
                return False

            # Cache schedules locally
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Clear old schedules
            cursor.execute("DELETE FROM school_schedules")

            # Insert new schedules
            for schedule in schedules:
                cursor.execute(
                    """
                    INSERT INTO school_schedules (
                        id, name, description,
                        morning_start_time, morning_end_time,
                        morning_login_window_start, morning_login_window_end,
                        morning_logout_window_start, morning_logout_window_end,
                        morning_late_threshold_minutes,
                        afternoon_start_time, afternoon_end_time,
                        afternoon_login_window_start, afternoon_login_window_end,
                        afternoon_logout_window_start, afternoon_logout_window_end,
                        afternoon_late_threshold_minutes,
                        auto_detect_session, allow_early_arrival, require_logout,
                        duplicate_scan_cooldown_minutes,
                        is_default, status, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        schedule["id"],
                        schedule["name"],
                        schedule.get("description"),
                        schedule["morning_start_time"],
                        schedule["morning_end_time"],
                        schedule["morning_login_window_start"],
                        schedule["morning_login_window_end"],
                        schedule["morning_logout_window_start"],
                        schedule["morning_logout_window_end"],
                        schedule["morning_late_threshold_minutes"],
                        schedule["afternoon_start_time"],
                        schedule["afternoon_end_time"],
                        schedule["afternoon_login_window_start"],
                        schedule["afternoon_login_window_end"],
                        schedule["afternoon_logout_window_start"],
                        schedule["afternoon_logout_window_end"],
                        schedule["afternoon_late_threshold_minutes"],
                        1 if schedule["auto_detect_session"] else 0,
                        1 if schedule["allow_early_arrival"] else 0,
                        1 if schedule["require_logout"] else 0,
                        schedule["duplicate_scan_cooldown_minutes"],
                        1 if schedule["is_default"] else 0,
                        schedule["status"],
                        datetime.now().isoformat(),
                    ),
                )

            conn.commit()
            conn.close()

            logger.info(f"✅ Schedules synced: {len(schedules)} schedule(s) cached")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error syncing schedules: {e}")
            return False
        except Exception as e:
            logger.error(f"Error syncing schedules: {e}")
            return False

    def get_default_schedule(self) -> Optional[Dict]:
        """
        Get the default schedule from local cache

        Returns:
            dict: Schedule configuration or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM school_schedules 
                WHERE is_default = 1 AND status = 'active'
                LIMIT 1
            """
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                logger.warning("No default schedule found in cache")
                return None

            # Convert row to dict
            columns = [
                "id",
                "name",
                "description",
                "morning_start_time",
                "morning_end_time",
                "morning_login_window_start",
                "morning_login_window_end",
                "morning_logout_window_start",
                "morning_logout_window_end",
                "morning_late_threshold_minutes",
                "afternoon_start_time",
                "afternoon_end_time",
                "afternoon_login_window_start",
                "afternoon_login_window_end",
                "afternoon_logout_window_start",
                "afternoon_logout_window_end",
                "afternoon_late_threshold_minutes",
                "auto_detect_session",
                "allow_early_arrival",
                "require_logout",
                "duplicate_scan_cooldown_minutes",
                "is_default",
                "status",
                "synced_at",
            ]

            schedule = dict(zip(columns, row))

            # Convert boolean fields
            schedule["auto_detect_session"] = bool(schedule["auto_detect_session"])
            schedule["allow_early_arrival"] = bool(schedule["allow_early_arrival"])
            schedule["require_logout"] = bool(schedule["require_logout"])
            schedule["is_default"] = bool(schedule["is_default"])

            return schedule

        except Exception as e:
            logger.error(f"Error getting default schedule: {e}")
            return None

    def get_schedule_by_section(self, section_id: str) -> Optional[Dict]:
        """
        Get schedule for a specific section (future enhancement)

        Args:
            section_id: Section UUID

        Returns:
            dict: Schedule configuration or default schedule
        """
        # For now, return default schedule
        # Future: Query Supabase for section-specific schedule
        return self.get_default_schedule()
