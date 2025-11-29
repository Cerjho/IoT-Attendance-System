"""
Tests for File Locking
"""
import os
import tempfile
import threading
import time
from pathlib import Path

import pytest

from src.utils.file_locks import (
    DatabaseLock,
    FileLock,
    LockTimeoutError,
    PhotoLock,
    file_lock,
)


@pytest.fixture
def temp_lock_file():
    """Create temporary lock file"""
    with tempfile.NamedTemporaryFile(suffix=".lock", delete=False) as f:
        lock_file = f.name
    yield lock_file
    # Cleanup
    if Path(lock_file).exists():
        Path(lock_file).unlink()


def test_file_lock_acquire_release(temp_lock_file):
    """Test basic lock acquire and release"""
    lock = FileLock(temp_lock_file, timeout=5)

    assert lock.acquire()
    assert lock.fd is not None

    lock.release()
    assert lock.fd is None


def test_file_lock_context_manager(temp_lock_file):
    """Test lock as context manager"""
    with FileLock(temp_lock_file, timeout=5) as lock:
        assert lock.fd is not None

    assert lock.fd is None


def test_file_lock_blocking(temp_lock_file):
    """Test blocking behavior"""
    lock1 = FileLock(temp_lock_file, timeout=5)
    lock2 = FileLock(temp_lock_file, timeout=1)

    # First lock acquires
    assert lock1.acquire()

    # Second lock should block and timeout
    start = time.time()
    assert not lock2.acquire()
    elapsed = time.time() - start

    assert elapsed >= 1  # Should wait for timeout
    assert elapsed < 2  # Should not wait much longer

    lock1.release()


def test_file_lock_non_blocking(temp_lock_file):
    """Test non-blocking acquire"""
    lock1 = FileLock(temp_lock_file, timeout=5)
    lock2 = FileLock(temp_lock_file, timeout=5)

    assert lock1.acquire()

    # Non-blocking should fail immediately
    start = time.time()
    assert not lock2.acquire(blocking=False)
    elapsed = time.time() - start

    assert elapsed < 0.5  # Should return immediately

    lock1.release()


def test_file_lock_concurrent_threads(temp_lock_file):
    """Test lock prevents concurrent access"""
    results = []

    def worker(lock_file, worker_id):
        lock = FileLock(lock_file, timeout=5)
        if lock.acquire():
            # Critical section
            results.append(f"start-{worker_id}")
            time.sleep(0.1)
            results.append(f"end-{worker_id}")
            lock.release()

    threads = [
        threading.Thread(target=worker, args=(temp_lock_file, i))
        for i in range(3)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify no interleaving (each start followed by its end)
    for i in range(3):
        start_idx = results.index(f"start-{i}")
        end_idx = results.index(f"end-{i}")
        # No other starts between this start and end
        between = results[start_idx + 1 : end_idx]
        assert all(not item.startswith("start-") for item in between)


def test_file_lock_context_timeout(temp_lock_file):
    """Test context manager timeout"""
    lock1 = FileLock(temp_lock_file, timeout=5)
    lock1.acquire()

    with pytest.raises(LockTimeoutError):
        with file_lock(temp_lock_file, timeout=1):
            pass

    lock1.release()


def test_database_lock():
    """Test DatabaseLock wrapper"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        with DatabaseLock(str(db_path), timeout=5):
            # Critical section
            pass

        # Lock should be released


def test_photo_lock():
    """Test PhotoLock wrapper"""
    with tempfile.TemporaryDirectory() as tmpdir:
        photo_path = Path(tmpdir) / "photo.jpg"
        photo_path.touch()

        with PhotoLock(str(photo_path), timeout=5):
            # Critical section
            pass

        # Lock should be released


def test_lock_creates_directory(temp_lock_file):
    """Test lock creates lock directory if needed"""
    nested_lock = str(Path(temp_lock_file).parent / "subdir" / "nested.lock")

    lock = FileLock(nested_lock, timeout=5)
    assert lock.acquire()

    assert Path(nested_lock).parent.exists()

    lock.release()
    # Cleanup
    Path(nested_lock).unlink()
    Path(nested_lock).parent.rmdir()


def test_lock_cleanup_on_del(temp_lock_file):
    """Test lock is released on object deletion"""
    lock = FileLock(temp_lock_file, timeout=5)
    lock.acquire()

    del lock

    # Should be able to acquire new lock
    lock2 = FileLock(temp_lock_file, timeout=5)
    assert lock2.acquire()
    lock2.release()


def test_multiple_locks_different_files():
    """Test multiple locks on different files work independently"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file1 = Path(tmpdir) / "lock1.lock"
        lock_file2 = Path(tmpdir) / "lock2.lock"

        lock1 = FileLock(str(lock_file1), timeout=5)
        lock2 = FileLock(str(lock_file2), timeout=5)

        # Both should acquire successfully
        assert lock1.acquire()
        assert lock2.acquire()

        lock1.release()
        lock2.release()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
