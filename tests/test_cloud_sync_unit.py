from datetime import datetime
from typing import Dict, Any, List

import json
import os
import types
import pytest

from src.cloud.cloud_sync import CloudSyncManager


class FakeConnectivity:
    def __init__(self, online=True):
        self._online = online

    def is_online(self):
        return self._online

    def get_connection_quality(self):
        return {"online": self._online, "latency_ms": 0}

    def wait_for_connection(self, timeout=30):
        return self._online


class FakeQueue:
    def __init__(self):
        self.added = []
        self.synced = []
        self.removed = []
        self.pending: List[Dict[str, Any]] = []
        self.device_status = {}

    def add_to_queue(self, record_type, record_id, data, priority=0):
        self.added.append((record_type, record_id, data, priority))
        return True

    def mark_attendance_synced(self, attendance_id, cloud_record_id=None):
        self.synced.append((attendance_id, cloud_record_id))
        return True

    def remove_from_queue(self, queue_id):
        self.removed.append(queue_id)
        return True

    def get_pending_records(self, limit=10):
        return list(self.pending)[:limit]

    def update_retry_count(self, queue_id, err=None):
        return True

    def update_device_status(self, device_id, sync_count):
        self.device_status = {"device_id": device_id, "sync_count": sync_count}
        return True

    def get_device_status(self):
        return {"last_sync": None}

    def get_queue_size(self):
        return len(self.pending)

    def get_unsynced_attendance(self, limit=100):
        return []


class FakeResp:
    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json = json_body
        self.text = text

    def json(self):
        return self._json


def test_insert_to_cloud_success(monkeypatch, tmp_path):
    cfg = {"enabled": True, "url": "https://x.supabase.co", "api_key": "k", "device_id": "d"}
    queue = FakeQueue()
    conn = FakeConnectivity(True)
    csm = CloudSyncManager(cfg, queue, conn)

    # Mock requests
    def fake_get(url, headers=None, timeout=5, params=None):
        return FakeResp(200, json_body=[{"id": "uuid-1"}])

    def fake_post(url, headers=None, json=None, timeout=10):
        return FakeResp(201, json_body=[{"id": 123}])

    import requests as _requests

    monkeypatch.setattr(_requests, "get", fake_get)
    monkeypatch.setattr(_requests, "post", fake_post)

    cloud_id = csm._insert_to_cloud(
        {
            "student_number": "2021001",
            "date": "2025-01-01",
            "status": "present",
            "time_in": "08:00:00",
        }
    )

    assert cloud_id == "123"


def test_sync_attendance_queues_when_disabled(monkeypatch):
    cfg = {"enabled": False, "url": "${SUPABASE_URL}", "api_key": "${SUPABASE_KEY}", "device_id": "dev"}
    queue = FakeQueue()
    conn = FakeConnectivity(True)
    csm = CloudSyncManager(cfg, queue, conn)

    attendance = {
        "id": 1,
        "student_id": "2021001",
        "timestamp": "2025-01-01T08:00:00",
        "qr_data": "2021001",
        "scan_type": "time_in",
        "status": "present",
    }
    ok = csm.sync_attendance_record(attendance, photo_path=None)
    assert ok is False
    assert len(queue.added) == 1
