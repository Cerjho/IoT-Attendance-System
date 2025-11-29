"""
Database Transaction Wrappers
Provides transaction safety for multi-step database operations
"""
import functools
import logging
import sqlite3
from contextlib import contextmanager
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@contextmanager
def transaction(connection: sqlite3.Connection):
    """
    Context manager for database transactions

    Args:
        connection: SQLite connection

    Yields:
        connection

    Example:
        with transaction(conn):
            cursor.execute("INSERT ...")
            cursor.execute("UPDATE ...")
        # Auto-commits on success, rolls back on exception
    """
    try:
        # SQLite transactions start with first SQL statement
        # We use explicit BEGIN for clarity
        connection.execute("BEGIN")
        yield connection
        connection.commit()
        logger.debug("Transaction committed")
    except Exception as e:
        connection.rollback()
        logger.error(f"Transaction rolled back: {e}")
        raise


def with_transaction(func: Callable) -> Callable:
    """
    Decorator for methods that should run in a transaction

    The decorated method must have a `connection` parameter or
    access to self.connection (for class methods).

    Example:
        @with_transaction
        def save_attendance(self, connection, data):
            # Multiple DB operations here
            pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Try to find connection parameter
        connection = None

        # Check kwargs
        if "connection" in kwargs:
            connection = kwargs["connection"]
        # Check if first arg is self with connection attribute
        elif len(args) > 0 and hasattr(args[0], "connection"):
            connection = args[0].connection
        # Check if connection is passed as positional arg
        elif len(args) > 1 and isinstance(args[1], sqlite3.Connection):
            connection = args[1]

        if connection is None:
            raise ValueError(
                "Cannot find SQLite connection for transaction. "
                "Method must have 'connection' parameter or self.connection"
            )

        with transaction(connection):
            return func(*args, **kwargs)

    return wrapper


class TransactionalDB:
    """
    Base class for database managers with transaction support

    Subclasses should set self.connection in __init__
    """

    def __init__(self, db_path: str):
        """
        Initialize transactional database

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row

    @contextmanager
    def transaction(self):
        """
        Context manager for transactions on this DB

        Example:
            with db.transaction():
                db.insert_record(...)
                db.update_queue(...)
        """
        with transaction(self.connection):
            yield self.connection

    def execute_in_transaction(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function within a transaction

        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result from func
        """
        with self.transaction():
            return func(*args, **kwargs)

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class SafeAttendanceDB:
    """
    Transaction-safe wrapper for attendance database operations

    Ensures attendance record + queue operations are atomic
    """

    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize with existing connection

        Args:
            connection: SQLite connection
        """
        self.connection = connection

    def save_attendance_with_queue(
        self,
        attendance_data: dict,
        photo_path: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> int:
        """
        Save attendance and add to sync queue atomically

        Args:
            attendance_data: Dict with student_number, date, time_in/time_out, status, etc.
            photo_path: Optional path to photo
            device_id: Optional device ID

        Returns:
            attendance_id: ID of inserted attendance record

        Raises:
            Exception: If transaction fails (no partial save)
        """
        with transaction(self.connection):
            cursor = self.connection.cursor()

            # Insert attendance
            cursor.execute(
                """
                INSERT INTO attendance 
                (student_number, date, time_in, time_out, status, photo_path, device_id, synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    attendance_data.get("student_number"),
                    attendance_data.get("date"),
                    attendance_data.get("time_in"),
                    attendance_data.get("time_out"),
                    attendance_data.get("status"),
                    photo_path,
                    device_id,
                ),
            )

            attendance_id = cursor.lastrowid

            # Add to sync queue
            cursor.execute(
                """
                INSERT INTO sync_queue 
                (record_type, record_id, data, priority)
                VALUES ('attendance', ?, ?, 5)
                """,
                (
                    attendance_id,
                    str(
                        {
                            **attendance_data,
                            "photo_path": photo_path,
                            "device_id": device_id,
                        }
                    ),
                ),
            )

            logger.info(
                f"Saved attendance {attendance_id} with queue entry (transaction)"
            )
            return attendance_id

    def mark_synced_and_cleanup_queue(
        self, attendance_id: int, cloud_record_id: Optional[str] = None
    ):
        """
        Mark attendance as synced and remove from queue atomically

        Args:
            attendance_id: Local attendance ID
            cloud_record_id: Cloud record ID (optional)
        """
        with transaction(self.connection):
            cursor = self.connection.cursor()

            # Update attendance
            if cloud_record_id:
                cursor.execute(
                    """
                    UPDATE attendance 
                    SET synced = 1, cloud_record_id = ?
                    WHERE id = ?
                    """,
                    (cloud_record_id, attendance_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE attendance 
                    SET synced = 1
                    WHERE id = ?
                    """,
                    (attendance_id,),
                )

            # Remove from queue
            cursor.execute(
                """
                DELETE FROM sync_queue 
                WHERE record_type = 'attendance' AND record_id = ?
                """,
                (attendance_id,),
            )

            logger.debug(f"Marked attendance {attendance_id} synced and removed from queue")
