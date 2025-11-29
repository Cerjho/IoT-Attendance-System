"""
Tests for Database Transactions
"""
import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.utils.db_transactions import (
    SafeAttendanceDB,
    TransactionalDB,
    transaction,
    with_transaction,
)


@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY,
            student_number TEXT,
            date TEXT,
            time_in TEXT,
            time_out TEXT,
            status TEXT,
            photo_path TEXT,
            device_id TEXT,
            synced INTEGER DEFAULT 0,
            cloud_record_id TEXT
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE sync_queue (
            id INTEGER PRIMARY KEY,
            record_type TEXT,
            record_id INTEGER,
            data TEXT,
            priority INTEGER,
            retry_count INTEGER DEFAULT 0
        )
    """
    )
    conn.commit()

    yield db_path, conn

    conn.close()
    Path(db_path).unlink()


def test_transaction_context_manager_success(temp_db):
    """Test transaction commits on success"""
    db_path, conn = temp_db

    with transaction(conn):
        conn.execute(
            "INSERT INTO attendance (student_number, date, status) VALUES (?, ?, ?)",
            ("2021001", "2025-01-01", "present"),
        )

    # Verify committed
    cursor = conn.execute("SELECT COUNT(*) FROM attendance")
    count = cursor.fetchone()[0]
    assert count == 1


def test_transaction_context_manager_rollback(temp_db):
    """Test transaction rolls back on exception"""
    db_path, conn = temp_db

    try:
        with transaction(conn):
            conn.execute(
                "INSERT INTO attendance (student_number, date, status) VALUES (?, ?, ?)",
                ("2021001", "2025-01-01", "present"),
            )
            raise Exception("Intentional failure")
    except Exception:
        pass

    # Verify rolled back
    cursor = conn.execute("SELECT COUNT(*) FROM attendance")
    count = cursor.fetchone()[0]
    assert count == 0


def test_with_transaction_decorator(temp_db):
    """Test transaction decorator"""
    db_path, conn = temp_db

    class TestDB:
        def __init__(self, connection):
            self.connection = connection

        @with_transaction
        def save_record(self):
            self.connection.execute(
                "INSERT INTO attendance (student_number, date, status) VALUES (?, ?, ?)",
                ("2021001", "2025-01-01", "present"),
            )

    db = TestDB(conn)
    db.save_record()

    cursor = conn.execute("SELECT COUNT(*) FROM attendance")
    count = cursor.fetchone()[0]
    assert count == 1


def test_with_transaction_decorator_rollback(temp_db):
    """Test transaction decorator rolls back on exception"""
    db_path, conn = temp_db

    class TestDB:
        def __init__(self, connection):
            self.connection = connection

        @with_transaction
        def save_and_fail(self):
            self.connection.execute(
                "INSERT INTO attendance (student_number, date, status) VALUES (?, ?, ?)",
                ("2021001", "2025-01-01", "present"),
            )
            raise Exception("Intentional failure")

    db = TestDB(conn)

    with pytest.raises(Exception):
        db.save_and_fail()

    cursor = conn.execute("SELECT COUNT(*) FROM attendance")
    count = cursor.fetchone()[0]
    assert count == 0


def test_transactional_db_class(temp_db):
    """Test TransactionalDB base class"""
    db_path, _ = temp_db

    with TransactionalDB(db_path) as db:
        with db.transaction():
            db.connection.execute(
                "INSERT INTO attendance (student_number, date, status) VALUES (?, ?, ?)",
                ("2021001", "2025-01-01", "present"),
            )

        cursor = db.connection.execute("SELECT COUNT(*) FROM attendance")
        count = cursor.fetchone()[0]
        assert count == 1


def test_safe_attendance_db_save_with_queue(temp_db):
    """Test SafeAttendanceDB atomic save"""
    db_path, conn = temp_db

    safe_db = SafeAttendanceDB(conn)

    attendance_data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "time_in": "07:30:00",
        "time_out": None,
        "status": "present",
    }

    attendance_id = safe_db.save_attendance_with_queue(
        attendance_data, photo_path="/path/to/photo.jpg", device_id="pi-lab-01"
    )

    # Verify attendance saved
    cursor = conn.execute("SELECT * FROM attendance WHERE id = ?", (attendance_id,))
    record = cursor.fetchone()
    assert record is not None

    # Verify queue entry added
    cursor = conn.execute(
        "SELECT * FROM sync_queue WHERE record_type = 'attendance' AND record_id = ?",
        (attendance_id,),
    )
    queue_record = cursor.fetchone()
    assert queue_record is not None


def test_safe_attendance_db_rollback(temp_db):
    """Test SafeAttendanceDB rolls back on failure"""
    db_path, conn = temp_db

    # Drop sync_queue to cause failure
    conn.execute("DROP TABLE sync_queue")

    safe_db = SafeAttendanceDB(conn)

    attendance_data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "time_in": "07:30:00",
        "status": "present",
    }

    # Should fail and rollback
    with pytest.raises(Exception):
        safe_db.save_attendance_with_queue(attendance_data)

    # Verify nothing saved
    cursor = conn.execute("SELECT COUNT(*) FROM attendance")
    count = cursor.fetchone()[0]
    assert count == 0


def test_safe_attendance_db_mark_synced(temp_db):
    """Test SafeAttendanceDB mark synced and cleanup"""
    db_path, conn = temp_db

    safe_db = SafeAttendanceDB(conn)

    # Insert test data
    attendance_data = {
        "student_number": "2021001",
        "date": "2025-01-01",
        "time_in": "07:30:00",
        "status": "present",
    }
    attendance_id = safe_db.save_attendance_with_queue(attendance_data)

    # Mark as synced
    safe_db.mark_synced_and_cleanup_queue(attendance_id, cloud_record_id="cloud-123")

    # Verify attendance marked synced
    cursor = conn.execute("SELECT synced, cloud_record_id FROM attendance WHERE id = ?", (attendance_id,))
    synced, cloud_id = cursor.fetchone()
    assert synced == 1
    assert cloud_id == "cloud-123"

    # Verify queue entry removed
    cursor = conn.execute(
        "SELECT COUNT(*) FROM sync_queue WHERE record_type = 'attendance' AND record_id = ?",
        (attendance_id,),
    )
    count = cursor.fetchone()[0]
    assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
