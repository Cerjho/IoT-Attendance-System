"""
Tests for Disk Monitor
"""
import os
import tempfile
import time
from pathlib import Path

import pytest

from src.utils.disk_monitor import DiskMonitor


@pytest.fixture
def temp_dirs():
    """Create temporary photo and log directories"""
    with tempfile.TemporaryDirectory() as tmpdir:
        photo_dir = Path(tmpdir) / "photos"
        log_dir = Path(tmpdir) / "logs"
        photo_dir.mkdir()
        log_dir.mkdir()
        yield {"photo_dir": str(photo_dir), "log_dir": str(log_dir)}


def test_disk_usage_check(temp_dirs):
    """Test disk usage check"""
    config = {
        "warn_threshold_percent": 10,
        "critical_threshold_percent": 5,
        **temp_dirs,
    }
    monitor = DiskMonitor(config)

    usage = monitor.get_disk_usage()
    assert "total" in usage
    assert "free" in usage
    assert "free_percent" in usage
    assert usage["free_percent"] > 0


def test_space_available(temp_dirs):
    """Test space availability check"""
    config = {
        "warn_threshold_percent": 10,
        "critical_threshold_percent": 5,
        **temp_dirs,
    }
    monitor = DiskMonitor(config)

    # Should have space available (unless disk is critically low)
    assert monitor.check_space_available(required_mb=1)


def test_cleanup_old_photos(temp_dirs):
    """Test photo cleanup by age"""
    config = {
        "photo_retention_days": 1,  # Keep only 1 day
        **temp_dirs,
    }
    monitor = DiskMonitor(config)

    photo_dir = Path(temp_dirs["photo_dir"])

    # Create old photo
    old_photo = photo_dir / "old.jpg"
    old_photo.write_text("old photo")
    # Set mtime to 2 days ago
    old_time = time.time() - (2 * 24 * 60 * 60)
    os.utime(old_photo, (old_time, old_time))

    # Create recent photo
    recent_photo = photo_dir / "recent.jpg"
    recent_photo.write_text("recent photo")

    # Run cleanup
    result = monitor.cleanup_old_photos(force=True)

    assert result["deleted_count"] == 1
    assert result["freed_bytes"] > 0
    assert not old_photo.exists()
    assert recent_photo.exists()


def test_cleanup_old_logs(temp_dirs):
    """Test log cleanup by age"""
    config = {
        "log_retention_days": 1,
        **temp_dirs,
    }
    monitor = DiskMonitor(config)

    log_dir = Path(temp_dirs["log_dir"])

    # Create old log
    old_log = log_dir / "old.log"
    old_log.write_text("old log")
    old_time = time.time() - (2 * 24 * 60 * 60)
    os.utime(old_log, (old_time, old_time))

    # Create recent log
    recent_log = log_dir / "recent.log"
    recent_log.write_text("recent log")

    result = monitor.cleanup_old_logs()

    assert result["deleted_count"] == 1
    assert not old_log.exists()
    assert recent_log.exists()


def test_enforce_photo_size_limit(temp_dirs):
    """Test photo size limit enforcement"""
    config = {
        "photo_max_size_mb": 0.001,  # 1KB limit
        **temp_dirs,
    }
    monitor = DiskMonitor(config)

    photo_dir = Path(temp_dirs["photo_dir"])

    # Create multiple photos exceeding limit
    for i in range(3):
        photo = photo_dir / f"photo{i}.jpg"
        photo.write_text("x" * 500)  # 500 bytes each
        time.sleep(0.01)  # Ensure different mtimes

    result = monitor.enforce_photo_size_limit()

    # Should delete oldest photos to get under 1KB
    assert result["deleted_count"] > 0

    # Total size should be under limit
    total_size = sum(f.stat().st_size for f in photo_dir.glob("*"))
    assert total_size <= 1024


def test_auto_cleanup(temp_dirs):
    """Test auto cleanup combines all cleanup methods"""
    config = {
        "photo_retention_days": 1,
        "log_retention_days": 1,
        "photo_max_size_mb": 0.001,
        **temp_dirs,
    }
    monitor = DiskMonitor(config)

    photo_dir = Path(temp_dirs["photo_dir"])
    log_dir = Path(temp_dirs["log_dir"])

    # Create old photo
    old_photo = photo_dir / "old.jpg"
    old_photo.write_text("old")
    old_time = time.time() - (2 * 24 * 60 * 60)
    os.utime(old_photo, (old_time, old_time))

    # Create old log
    old_log = log_dir / "old.log"
    old_log.write_text("old")
    os.utime(old_log, (old_time, old_time))

    result = monitor.auto_cleanup()

    assert result["deleted_count"] >= 2  # At least old photo and log
    assert not old_photo.exists()
    assert not old_log.exists()


def test_cleanup_interval(temp_dirs):
    """Test cleanup respects interval"""
    config = {
        "photo_retention_days": 1,
        **temp_dirs,
    }
    monitor = DiskMonitor(config)
    monitor._cleanup_interval_hours = 1  # 1 hour interval

    # First cleanup should run
    result1 = monitor.cleanup_old_photos(force=True)
    assert monitor._last_cleanup is not None

    # Immediate second cleanup should skip
    result2 = monitor.cleanup_old_photos(force=False)
    assert result2["deleted_count"] == 0

    # Force flag should override
    result3 = monitor.cleanup_old_photos(force=True)
    # May or may not delete depending on files, but should run


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
