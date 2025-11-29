import sqlite3
from datetime import datetime
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


def _prep_db(db_path):
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
            photo_path TEXT,
            synced INTEGER DEFAULT 0,
            sync_timestamp TEXT,
            cloud_record_id TEXT
        )
        """
    )
    conn.commit()
    conn.close()


@pytest.mark.integration
def test_photo_upload_remarks_included(monkeypatch, tmp_path):
    db_path = tmp_path / "attendance.db"
    _prep_db(db_path)
    queue = SyncQueueManager(db_path=str(db_path))

    # Insert unsynced attendance
    ts = datetime.now().isoformat()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO attendance (student_id, timestamp, status, scan_type, photo_path, synced) VALUES (?, ?, ?, ?, ?, 0)",
        ("2021002", ts, "present", "time_in", None),
    )
    attendance_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Queue with photo path
    photo_path = str(tmp_path / "frame.jpg")
    with open(photo_path, "wb") as f:
        f.write(b"fakejpeg")

    queue.add_to_queue(
        "attendance",
        attendance_id,
        {
            "attendance": {
                "id": attendance_id,
                "student_id": "2021002",
                "timestamp": ts,
                "status": "present",
                "scan_type": "time_in",
                "qr_data": "2021002",
            },
            "photo_path": photo_path,
        },
    )

    # Mock PhotoUploader.upload_photo to return a known URL
    class MockUploader:
        def __init__(self, *args, **kwargs):
            pass

        def upload_photo(self, local_path, student_id):
            return "https://example.supabase.co/storage/v1/object/public/attendance-photos/2021002/test.jpg"

    monkeypatch.setattr("src.cloud.photo_uploader.PhotoUploader", MockUploader)

    # Mock REST
    class MockResponse:
        def __init__(self, status_code=200, json_data=None, text=""):
            self.status_code = status_code
            self._json = json_data or []
            self.text = text

        def json(self):
            return self._json

    def fake_get(url, headers=None, params=None, timeout=5):
        if "students" in url:
            return MockResponse(200, [{"id": "uuid-2021002"}])
        return MockResponse(200, [])

    captured_attendance_payload = {}

    def fake_post(url, headers=None, json=None, timeout=10, data=None):
        nonlocal captured_attendance_payload
        if "/rest/v1/attendance" in url:
            captured_attendance_payload = dict(json or {})
            return MockResponse(201, [{"id": 555}])
        if "/storage/v1/object/" in url:
            return MockResponse(200, [])
        return MockResponse(200, [])

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.post", fake_post)

    config = {
        "enabled": True,
        "url": "https://example.supabase.co",
        "api_key": "key",
        "device_id": "pi-lab-01",
        "retry_attempts": 2,
        "retry_delay": 1,
        "cleanup_photos_after_sync": False,
    }
    cloud = CloudSyncManager(config, queue, DummyConnectivity(True))
    cloud.client = True

    result = cloud.process_sync_queue(batch_size=10)
    assert result["succeeded"] == 1
    # Remarks should include photo public URL
    assert "remarks" in captured_attendance_payload
    assert "attendance-photos/2021002" in captured_attendance_payload["remarks"]


@pytest.mark.integration
def test_negative_student_not_found_keeps_in_queue(monkeypatch, tmp_path):
    db_path = tmp_path / "attendance.db"
    _prep_db(db_path)
    queue = SyncQueueManager(db_path=str(db_path))

    ts = datetime.now().isoformat()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO attendance (student_id, timestamp, status, scan_type, synced) VALUES (?, ?, ?, ?, 0)",
        ("9999999", ts, "present", "time_in"),
    )
    attendance_id = cur.lastrowid
    conn.commit()
    conn.close()

    queue.add_to_queue(
        "attendance",
        attendance_id,
        {
            "attendance": {
                "id": attendance_id,
                "student_id": "9999999",
                "timestamp": ts,
                "status": "present",
                "scan_type": "time_in",
            },
            "photo_path": None,
        },
    )

    class MockResponse:
        def __init__(self, status_code=200, json_data=None, text=""):
            self.status_code = status_code
            self._json = json_data or []
            self.text = text

        def json(self):
            return self._json

    def fake_get(url, headers=None, params=None, timeout=5):
        if "students" in url:
            return MockResponse(200, [])  # student not found
        return MockResponse(200, [])

    def fake_post(url, headers=None, json=None, timeout=10, data=None):
        return MockResponse(500, [], text="server error")

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.post", fake_post)

    config = {
        "enabled": True,
        "url": "https://example.supabase.co",
        "api_key": "key",
        "device_id": "pi-lab-01",
        "retry_attempts": 1,
        "retry_delay": 1,
    }
    cloud = CloudSyncManager(config, queue, DummyConnectivity(True))
    cloud.client = True

    result = cloud.process_sync_queue(batch_size=10)
    assert result["failed"] == 1

    # Ensure queue record remains (retry_count incremented)
    pending = queue.get_pending_records(limit=10)
    assert len(pending) == 1
    assert pending[0]["retry_count"] >= 1


@pytest.mark.integration
def test_force_sync_all_marks_records_synced(monkeypatch, tmp_path):
    db_path = tmp_path / "attendance.db"
    _prep_db(db_path)
    queue = SyncQueueManager(db_path=str(db_path))

    ts = datetime.now().isoformat()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO attendance (student_id, timestamp, status, scan_type, synced) VALUES (?, ?, ?, ?, 0)",
        ("2021003", ts, "present", "time_in"),
    )
    attendance_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Supabase REST mocks
    class MockResponse:
        def __init__(self, status_code=200, json_data=None, text=""):
            self.status_code = status_code
            self._json = json_data or []
            self.text = text

        def json(self):
            return self._json

    def fake_get(url, headers=None, params=None, timeout=5):
        if "students" in url:
            return MockResponse(200, [{"id": "uuid-2021003"}])
        return MockResponse(200, [])

    def fake_post(url, headers=None, json=None, timeout=10, data=None):
        if "/rest/v1/attendance" in url:
            return MockResponse(201, [{"id": 777}])
        return MockResponse(200, [])

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("requests.post", fake_post)

    config = {
        "enabled": True,
        "url": "https://example.supabase.co",
        "api_key": "key",
        "device_id": "pi-lab-01",
        "retry_attempts": 2,
        "retry_delay": 1,
    }
    cloud = CloudSyncManager(config, queue, DummyConnectivity(True))
    cloud.client = True

    # Get unsynced and run force sync
    result = cloud.force_sync_all()
    assert result["processed"] == 1
    assert result["succeeded"] == 1
    assert result["failed"] == 0

    # Verify attendance marked synced
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT synced, cloud_record_id FROM attendance WHERE id = ?", (attendance_id,))
    synced, cloud_id = cur.fetchone()
    conn.close()
    assert synced == 1
    assert str(cloud_id) == "777"
