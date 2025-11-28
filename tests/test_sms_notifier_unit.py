import types
from datetime import datetime, time, timedelta

import pytest

from src.notifications.sms_notifier import SMSNotifier, TimeProvider


class FakeTime(TimeProvider):
    def __init__(self, dt: datetime):
        self._now = dt

    def now(self) -> datetime:
        return self._now

    def advance_minutes(self, mins: int):
        self._now = self._now + timedelta(minutes=mins)


def build_notifier(fake_time: FakeTime, quiet_enabled=True) -> SMSNotifier:
    cfg = {
        "enabled": True,
        "username": "user",
        "password": "pass",
        "device_id": "dev1",
        "quiet_hours": {"enabled": quiet_enabled, "start": "22:00", "end": "06:00"},
        "duplicate_sms_cooldown_minutes": 5,
        "include_unsubscribe": False,
    }
    return SMSNotifier(cfg, time_provider=fake_time)


def test_quiet_hours_blocks_notifications(monkeypatch):
    # 23:00 is within quiet hours (22:00-06:00)
    fake_time = FakeTime(datetime(2025, 1, 1, 23, 0, 0))
    sms = build_notifier(fake_time, quiet_enabled=True)

    # Spy send_sms to ensure it is not called
    called = {"count": 0}

    def fake_send(phone, msg):
        called["count"] += 1
        return True

    monkeypatch.setattr(sms, "send_sms", fake_send)

    sent = sms.send_attendance_notification(
        student_id="S1", student_name="Alice", parent_phone="09123456789"
    )
    assert sent is False
    assert called["count"] == 0, "send_sms should not be called during quiet hours"


def test_cooldown_prevents_duplicate(monkeypatch):
    fake_time = FakeTime(datetime(2025, 1, 1, 9, 0, 0))
    sms = build_notifier(fake_time, quiet_enabled=False)

    calls = {"msgs": []}

    def fake_send(phone, msg):
        calls["msgs"].append((phone, msg))
        return True

    monkeypatch.setattr(sms, "send_sms", fake_send)

    # First send succeeds
    assert sms.send_attendance_notification(
        student_id="S1", student_name="Alice", parent_phone="09123456789"
    ) is True
    # Immediate second send blocked by cooldown
    assert (
        sms.send_attendance_notification(
            student_id="S1", student_name="Alice", parent_phone="09123456789"
        )
        is False
    )
    # After cooldown passes, should send again
    fake_time.advance_minutes(6)
    assert sms.send_attendance_notification(
        student_id="S1", student_name="Alice", parent_phone="09123456789"
    ) is True
    assert len(calls["msgs"]) == 2
