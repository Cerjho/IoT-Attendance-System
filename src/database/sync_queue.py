"""
Sync Queue Manager
Manages offline queue for cloud synchronization
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Dict, List, Optional

from src.utils.queue_validator import QueueDataValidator

logger = logging.getLogger(__name__)


class SyncQueueManager:
    """Manages sync queue for offline operation"""

    def __init__(self, db_path: str = "data/attendance.db"):
        """Initialize sync queue manager"""
        self.db_path = db_path
        self._lock = threading.Lock()  # Thread safety for concurrent access
        self._init_sync_tables()
        logger.info("Sync queue manager initialized")

    def _init_sync_tables(self):
        """Create sync-related tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Add sync columns to attendance table if they don't exist
        cursor.execute("PRAGMA table_info(attendance)")
        columns = [col[1] for col in cursor.fetchall()]

        if "synced" not in columns:
            cursor.execute("ALTER TABLE attendance ADD COLUMN synced INTEGER DEFAULT 0")
            logger.info("Added 'synced' column to attendance table")

        if "sync_timestamp" not in columns:
            cursor.execute("ALTER TABLE attendance ADD COLUMN sync_timestamp TEXT")
            logger.info("Added 'sync_timestamp' column to attendance table")

        if "cloud_record_id" not in columns:
            cursor.execute("ALTER TABLE attendance ADD COLUMN cloud_record_id TEXT")
            logger.info("Added 'cloud_record_id' column to attendance table")

        # Create sync_queue table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_type TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_attempt TEXT,
                error_message TEXT
            )
        """
        )

        # Create device_status table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS device_status (
                id INTEGER PRIMARY KEY DEFAULT 1,
                device_id TEXT,
                last_sync TEXT,
                sync_count INTEGER DEFAULT 0,
                pending_records INTEGER DEFAULT 0,
                CHECK (id = 1)
            )
        """
        )

        # Initialize device_status if empty
        cursor.execute("SELECT COUNT(*) FROM device_status")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT INTO device_status (id, device_id, last_sync, sync_count, pending_records)
                VALUES (1, NULL, NULL, 0, 0)
            """
            )

        conn.commit()
        conn.close()
        logger.info("Sync tables initialized")

    def add_to_queue(
        self, record_type: str, record_id: int, data: Dict, priority: int = 0
    ) -> bool:
        """
        Add record to sync queue with validation

        Args:
            record_type: Type of record ('attendance', 'student', 'photo')
            record_id: ID of the record
            data: Dictionary containing record data
            priority: Priority level (higher = more urgent)

        Returns:
            True if successful
        """
        try:
            # Validate data before adding to queue
            if record_type == "attendance":
                # Extract attendance data if wrapped
                attendance_data = data.get("attendance", data)
                
                is_valid, error = QueueDataValidator.validate_attendance(attendance_data)
                if not is_valid:
                    logger.error(f"Invalid queue data: {error}")
                    # Try to fix and retry
                    is_valid, fixed_data, error = QueueDataValidator.validate_and_fix(attendance_data)
                    if is_valid:
                        # Update the wrapped structure if data was wrapped
                        if "attendance" in data:
                            data["attendance"] = fixed_data
                        else:
                            data = fixed_data
                        logger.warning(f"Fixed invalid queue data for record {record_id}")
                    else:
                        logger.error(f"Cannot fix queue data: {error}")
                        return False

            conn = None
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                cursor = conn.cursor()

                data_json = json.dumps(data)

                cursor.execute(
                    """
                    INSERT INTO sync_queue (record_type, record_id, data, priority, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        record_type,
                        record_id,
                        data_json,
                        priority,
                        datetime.now().isoformat(),
                    ),
                )

                conn.commit()
                conn.close()

                logger.debug(f"Added to sync queue: {record_type} ID {record_id}")
                return True

            except sqlite3.OperationalError as e:
                if "disk" in str(e).lower() or "full" in str(e).lower():
                    logger.error(f"Disk full - cannot add to sync queue: {e}")
                    # Try to trigger cleanup if possible
                elif "locked" in str(e).lower():
                    logger.warning(f"Database locked, sync queue add may have failed: {e}")
                else:
                    logger.error(f"Database error adding to sync queue: {e}")
                return False
            except Exception as e:
                logger.error(f"Error adding to sync queue: {e}")
                return False
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass

        except Exception as e:
            logger.error(f"Error in add_to_queue: {e}")
            return False

    def get_pending_records(self, limit: int = 50, max_retries: int = 10) -> List[Dict]:
        """
        Get pending records from sync queue, excluding records exceeding max retries

        Args:
            limit: Maximum number of records to retrieve
            max_retries: Maximum retry count before marking as failed

        Returns:
            List of pending sync records (excludes records at max retry limit)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get stuck records first (for alerting)
            cursor.execute(
                """
                SELECT id, record_type, record_id, retry_count, error_message, created_at
                FROM sync_queue
                WHERE retry_count >= ?
            """,
                (max_retries,),
            )
            stuck_records = cursor.fetchall()
            
            if stuck_records:
                logger.warning(
                    f"⚠️  ALERT: {len(stuck_records)} records stuck in sync queue (exceeded {max_retries} retries)"
                )
                for record in stuck_records:
                    logger.error(
                        f"Stuck record: type={record['record_type']}, "
                        f"id={record['record_id']}, retries={record['retry_count']}, "
                        f"error={record['error_message'][:100] if record['error_message'] else 'None'}, "
                        f"age={record['created_at']}"
                    )

            # Get pending records that haven't exceeded max retries
            cursor.execute(
                """
                SELECT * FROM sync_queue
                WHERE retry_count < ?
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
            """,
                (max_retries, limit),
            )

            rows = cursor.fetchall()
            conn.close()

            records = []
            for row in rows:
                record = dict(row)
                record["data"] = json.loads(record["data"])
                records.append(record)

            return records

        except Exception as e:
            logger.error(f"Error getting pending records: {e}")
            return []

    def remove_from_queue(self, queue_id: int) -> bool:
        """Remove record from sync queue after successful sync"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM sync_queue WHERE id = ?", (queue_id,))

            conn.commit()
            conn.close()

            logger.debug(f"Removed queue record: {queue_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing from queue: {e}")
            return False

    def update_retry_count(self, queue_id: int, error_message: str = None) -> bool:
        """Update retry count for failed sync attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE sync_queue
                SET retry_count = retry_count + 1,
                    last_attempt = ?,
                    error_message = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), error_message, queue_id),
            )

            conn.commit()
            conn.close()

            logger.debug(f"Updated retry count for queue record: {queue_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating retry count: {e}")
            return False

    def mark_attendance_synced(
        self, attendance_id: int, cloud_record_id: str = None
    ) -> bool:
        """Mark attendance record as synced"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE attendance
                SET synced = 1,
                    sync_timestamp = ?,
                    cloud_record_id = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), cloud_record_id, attendance_id),
            )

            conn.commit()
            conn.close()

            logger.debug(f"Marked attendance {attendance_id} as synced")
            return True

        except Exception as e:
            logger.error(f"Error marking attendance as synced: {e}")
            return False

    def get_unsynced_attendance(self, limit: int = 100) -> List[Dict]:
        """Get unsynced attendance records"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM attendance
                WHERE synced = 0
                ORDER BY timestamp ASC
                LIMIT ?
            """,
                (limit,),
            )

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting unsynced attendance: {e}")
            return []

    def get_queue_size(self) -> int:
        """Get number of records in sync queue"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM sync_queue")
            count = cursor.fetchone()[0]

            conn.close()
            return count

        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return 0

    def update_device_status(
        self, device_id: str = None, sync_count: int = None
    ) -> bool:
        """Update device sync status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            pending = self.get_queue_size()

            if device_id and sync_count is not None:
                cursor.execute(
                    """
                    UPDATE device_status
                    SET device_id = ?,
                        last_sync = ?,
                        sync_count = ?,
                        pending_records = ?
                    WHERE id = 1
                """,
                    (device_id, datetime.now().isoformat(), sync_count, pending),
                )
            elif sync_count is not None:
                cursor.execute(
                    """
                    UPDATE device_status
                    SET last_sync = ?,
                        sync_count = ?,
                        pending_records = ?
                    WHERE id = 1
                """,
                    (datetime.now().isoformat(), sync_count, pending),
                )

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            return False

    def get_device_status(self) -> Dict:
        """Get device sync status"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM device_status WHERE id = 1")
            row = cursor.fetchone()

            conn.close()

            if row:
                return dict(row)
            return {}

        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return {}

    def archive_stuck_records(self, max_retries: int = 10) -> int:
        """
        Archive records that have exceeded max retries to failed_sync_queue table
        for investigation, instead of deleting them
        
        Returns:
            Number of records archived
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create archive table if it doesn't exist
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS failed_sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_id INTEGER,
                    record_type TEXT NOT NULL,
                    record_id INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    last_attempt TEXT,
                    error_message TEXT,
                    archived_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    reason TEXT
                )
            """
            )
            
            # Move stuck records to archive
            cursor.execute(
                """
                INSERT INTO failed_sync_queue 
                    (original_id, record_type, record_id, data, priority, 
                     retry_count, created_at, last_attempt, error_message, reason)
                SELECT 
                    id, record_type, record_id, data, priority,
                    retry_count, created_at, last_attempt, error_message,
                    'Exceeded max retries: ' || retry_count || '/' || ?
                FROM sync_queue
                WHERE retry_count >= ?
            """,
                (max_retries, max_retries),
            )
            
            archived = cursor.rowcount
            
            # Remove from active queue
            cursor.execute(
                """
                DELETE FROM sync_queue
                WHERE retry_count >= ?
            """,
                (max_retries,),
            )

            conn.commit()
            conn.close()

            if archived > 0:
                logger.warning(
                    f"⚠️ Archived {archived} stuck sync records to failed_sync_queue (exceeded {max_retries} retries)"
                )
                logger.info(
                    f"💡 Review failed records with: SELECT * FROM failed_sync_queue ORDER BY archived_at DESC LIMIT 10"
                )

            return archived

        except Exception as e:
            logger.error(f"Error archiving stuck records: {e}")
            return 0

    def clear_old_failed_records(self, max_retries: int = 5) -> int:
        """
        DEPRECATED: Use archive_stuck_records() instead
        Remove records that have exceeded max retries
        """
        logger.warning("clear_old_failed_records is deprecated, use archive_stuck_records instead")
        return self.archive_stuck_records(max_retries)
