"""
File Locking Utilities
Provides file locking for concurrent access safety
"""
import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from src.utils.logging_factory import get_logger
from src.utils.log_decorators import log_execution_time

logger = get_logger(__name__)


class FileLock:
    """
    File-based lock for coordinating concurrent access

    Uses fcntl for POSIX-compliant file locking
    """

    def __init__(self, lock_file: str, timeout: int = 30):
        """
        Initialize file lock

        Args:
            lock_file: Path to lock file
            timeout: Max seconds to wait for lock
        """
        self.lock_file = Path(lock_file)
        self.timeout = timeout
        self.fd: Optional[int] = None

    def acquire(self, blocking: bool = True) -> bool:
        """
        Acquire lock

        Args:
            blocking: If True, wait for lock. If False, return immediately

        Returns:
            True if lock acquired, False otherwise
        """
        # Ensure lock directory exists
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Open lock file
            self.fd = os.open(self.lock_file, os.O_CREAT | os.O_RDWR)

            if blocking:
                # Try to acquire with timeout
                start_time = time.time()
                while True:
                    try:
                        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        logger.debug(f"Lock acquired: {self.lock_file}")
                        return True
                    except IOError:
                        if time.time() - start_time > self.timeout:
                            logger.error(f"Lock timeout after {self.timeout}s: {self.lock_file}")
                            os.close(self.fd)
                            self.fd = None
                            return False
                        time.sleep(0.1)
            else:
                # Non-blocking
                try:
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    logger.debug(f"Lock acquired (non-blocking): {self.lock_file}")
                    return True
                except IOError:
                    os.close(self.fd)
                    self.fd = None
                    return False

        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
            return False

    def release(self):
        """Release lock"""
        if self.fd is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                os.close(self.fd)
                logger.debug(f"Lock released: {self.lock_file}")
            except Exception as e:
                logger.error(f"Failed to release lock: {e}")
            finally:
                self.fd = None

    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise LockTimeoutError(f"Could not acquire lock: {self.lock_file}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()

    def __del__(self):
        """Cleanup on deletion"""
        if self.fd is not None:
            self.release()


@contextmanager
def file_lock(lock_file: str, timeout: int = 30):
    """
    Context manager for file locking

    Args:
        lock_file: Path to lock file
        timeout: Max seconds to wait for lock

    Yields:
        FileLock instance

    Example:
        with file_lock("data/.db.lock"):
            # Critical section
            pass
    """
    lock = FileLock(lock_file, timeout)
    try:
        if not lock.acquire():
            raise LockTimeoutError(f"Could not acquire lock: {lock_file}")
        yield lock
    finally:
        lock.release()


class DatabaseLock:
    """
    Lock wrapper specifically for database operations

    Prevents concurrent writes to SQLite database
    """

    def __init__(self, db_path: str, timeout: int = 30):
        """
        Initialize database lock

        Args:
            db_path: Path to database file
            timeout: Max seconds to wait for lock
        """
        self.db_path = Path(db_path)
        lock_file = self.db_path.parent / f".{self.db_path.name}.lock"
        self.lock = FileLock(str(lock_file), timeout)

    def __enter__(self):
        """Context manager entry"""
        if not self.lock.acquire():
            raise LockTimeoutError(f"Could not acquire database lock: {self.db_path}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.lock.release()


class PhotoLock:
    """
    Lock wrapper for photo file operations

    Prevents concurrent access to same photo file
    """

    def __init__(self, photo_path: str, timeout: int = 10):
        """
        Initialize photo lock

        Args:
            photo_path: Path to photo file
            timeout: Max seconds to wait for lock
        """
        self.photo_path = Path(photo_path)
        lock_file = self.photo_path.parent / f".{self.photo_path.name}.lock"
        self.lock = FileLock(str(lock_file), timeout)

    def __enter__(self):
        """Context manager entry"""
        if not self.lock.acquire():
            raise LockTimeoutError(f"Could not acquire photo lock: {self.photo_path}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.lock.release()


class LockTimeoutError(Exception):
    """Exception raised when lock acquisition times out"""

    pass
