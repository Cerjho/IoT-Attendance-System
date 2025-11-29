import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from src.cloud.cloud_sync import CloudSyncManager
from src.database.sync_queue import SyncQueueManager


class DummyConnectivity:
    def __init__(self, online=True):
        self._online = online

    def is_online(self):
        return self._online

    def get_connection_quality(self):
        return {"online": self._online, "latency_ms": 10}

    def wait_for_connection(self, timeout=30):
        return self._online


@pytest.mark.integration
def test_process_sync_queue_marks_records_synced(monkeypatch, tmp_path):
    # Setup temporary DB
    db_path = tmp_path / "attendance.db"
    # Pre-create attendance table before instantiating queue manager (which adds sync columns)
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            timestamp TEXT,
            status TEXT,
            scan_type TEXT,
            synced INTEGER DEFAULT 0,
            sync_timestamp TEXT,
            cloud_record_id TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    queue = SyncQueueManager(db_path=str(db_path))

    # Create a minimal attendance row in local DB
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Insert unsynced record
    ts = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO attendance (student_id, timestamp, status, scan_type, synced)
        VALUES (?, ?, ?, ?, 0)
        """,
        ("2021001", ts, "present", "time_in"),
    )
    attendance_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Queue the record (simulate offline capture with photo)
    queue.add_to_queue(
        "attendance",
        attendance_id,
        {
            "attendance": {
                "id": attendance_id,
                "student_id": "2021001",  # local uses student_number
                "timestamp": ts,
                "status": "present",
                "scan_type": "time_in",
                "qr_data": "2021001",
            },
            "photo_path": None,
        },
    )

    # Mock requests for student lookup and attendance insert
    class MockResponse:
        def __init__(self, status_code=200, json_data=None, text=""):
            self.status_code = status_code
            self._json = json_data or []
            self.text = text

        def json(self):
            return self._json

    def fake_get(url, headers=None, params=None, timeout=5):
        if "students" in url:
            # Return a single UUID for student_number
            return MockResponse(200, [{"id": "3c2c6e8f-uuid"}])
        return MockResponse(200, [])

    def fake_post(url, headers=None, json=None, timeout=10, data=None):
        if "/rest/v1/attendance" in url:
            # Return a created record with id
            return MockResponse(201, [{"id": 12345}])
        if "/storage/v1/object/" in url:
            return MockResponse(200, [])
        return MockResponse(200, [])

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.post", fake_post)

    # Build CloudSyncManager with dummy connectivity
    config = {
        "enabled": True,
        "url": "https://example.supabase.co",
        "api_key": "key",
        "device_id": "pi-lab-01",
        "retry_attempts": 2,
        "retry_delay": 1,
    }

    connectivity = DummyConnectivity(online=True)
    cloud = CloudSyncManager(config, queue, connectivity)

    # Ensure client is initialized (REST test fakes success)
    cloud.client = True

    # Process queue
    result = cloud.process_sync_queue(batch_size=10)
    assert result["processed"] == 1
    assert result["succeeded"] == 1
    assert result["failed"] == 0

    # Verify attendance marked synced
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT synced, cloud_record_id FROM attendance WHERE id = ?", (attendance_id,))
    synced, cloud_id = cur.fetchone()
    conn.close()
    assert synced == 1
    assert str(cloud_id) == "12345"
