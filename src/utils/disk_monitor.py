"""
Disk Space Monitor
Provides disk space checks and automatic cleanup for photos and logs
"""
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DiskMonitor:
    """Monitor disk space and manage cleanup"""

    def __init__(self, config: Dict):
        """
        Initialize disk monitor

        Config keys:
            warn_threshold_percent: Warn when free space below this (default 10%)
            critical_threshold_percent: Fail operations below this (default 5%)
            photo_retention_days: Keep photos for N days (default 30)
            photo_max_size_mb: Max total photo storage (default 500MB)
            log_retention_days: Keep logs for N days (default 7)
        """
        self.warn_threshold = config.get("warn_threshold_percent", 10)
        self.critical_threshold = config.get("critical_threshold_percent", 5)
        self.photo_retention_days = config.get("photo_retention_days", 30)
        self.photo_max_size_mb = config.get("photo_max_size_mb", 500)
        self.log_retention_days = config.get("log_retention_days", 7)

        self.photo_dir = Path(config.get("photo_dir", "data/photos"))
        self.log_dir = Path(config.get("log_dir", "data/logs"))

        self._last_cleanup = None
        self._cleanup_interval_hours = 24

        logger.info(
            f"Disk monitor initialized: warn={self.warn_threshold}%, critical={self.critical_threshold}%"
        )

    def get_disk_usage(self, path: str = "/") -> Dict:
        """
        Get disk usage statistics

        Returns:
            dict with total, used, free (bytes), and free_percent
        """
        try:
            stat = shutil.disk_usage(path)
            free_percent = (stat.free / stat.total) * 100
            return {
                "total": stat.total,
                "used": stat.used,
                "free": stat.free,
                "free_percent": free_percent,
            }
        except Exception as e:
            logger.error(f"Failed to get disk usage: {e}")
            # Return safe defaults assuming no space issue
            return {"total": 0, "used": 0, "free": 0, "free_percent": 100}

    def check_space_available(self, required_mb: float = 10) -> bool:
        """
        Check if sufficient disk space is available

        Args:
            required_mb: Required free space in MB

        Returns:
            True if space available and above critical threshold
        """
        usage = self.get_disk_usage()
        free_percent = usage["free_percent"]

        if free_percent < self.critical_threshold:
            logger.error(
                f"Critical disk space: {free_percent:.1f}% free (threshold {self.critical_threshold}%)"
            )
            return False

        if free_percent < self.warn_threshold:
            logger.warning(
                f"Low disk space: {free_percent:.1f}% free (threshold {self.warn_threshold}%)"
            )

        free_mb = usage["free"] / (1024 * 1024)
        if free_mb < required_mb:
            logger.warning(
                f"Insufficient space: {free_mb:.1f}MB free, need {required_mb}MB"
            )
            return False

        return True

    def cleanup_old_photos(self, force: bool = False) -> Dict:
        """
        Clean up old photos based on retention policy

        Args:
            force: Force cleanup even if last cleanup was recent

        Returns:
            dict with deleted_count, freed_bytes
        """
        if not force and self._last_cleanup:
            hours_since = (datetime.now() - self._last_cleanup).total_seconds() / 3600
            if hours_since < self._cleanup_interval_hours:
                logger.debug(
                    f"Skipping cleanup, last run {hours_since:.1f}h ago (interval {self._cleanup_interval_hours}h)"
                )
                return {"deleted_count": 0, "freed_bytes": 0}

        deleted_count = 0
        freed_bytes = 0

        if not self.photo_dir.exists():
            return {"deleted_count": 0, "freed_bytes": 0}

        cutoff_date = datetime.now() - timedelta(days=self.photo_retention_days)

        try:
            for photo_file in self.photo_dir.rglob("*"):
                if not photo_file.is_file():
                    continue

                # Check age
                mtime = datetime.fromtimestamp(photo_file.stat().st_mtime)
                if mtime < cutoff_date:
                    size = photo_file.stat().st_size
                    photo_file.unlink()
                    deleted_count += 1
                    freed_bytes += size

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} old photos, freed {freed_bytes/(1024*1024):.2f}MB"
                )

            self._last_cleanup = datetime.now()

        except Exception as e:
            logger.error(f"Photo cleanup failed: {e}")

        return {"deleted_count": deleted_count, "freed_bytes": freed_bytes}

    def cleanup_old_logs(self) -> Dict:
        """
        Clean up old log files based on retention policy

        Returns:
            dict with deleted_count, freed_bytes
        """
        deleted_count = 0
        freed_bytes = 0

        if not self.log_dir.exists():
            return {"deleted_count": 0, "freed_bytes": 0}

        cutoff_date = datetime.now() - timedelta(days=self.log_retention_days)

        try:
            for log_file in self.log_dir.glob("*.log"):
                if not log_file.is_file():
                    continue

                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff_date:
                    size = log_file.stat().st_size
                    log_file.unlink()
                    deleted_count += 1
                    freed_bytes += size

            if deleted_count > 0:
                logger.info(
                    f"Cleaned up {deleted_count} old logs, freed {freed_bytes/1024:.2f}KB"
                )

        except Exception as e:
            logger.error(f"Log cleanup failed: {e}")

        return {"deleted_count": deleted_count, "freed_bytes": freed_bytes}

    def enforce_photo_size_limit(self) -> Dict:
        """
        Enforce maximum photo storage size by deleting oldest first

        Returns:
            dict with deleted_count, freed_bytes
        """
        if not self.photo_dir.exists():
            return {"deleted_count": 0, "freed_bytes": 0}

        deleted_count = 0
        freed_bytes = 0
        max_bytes = self.photo_max_size_mb * 1024 * 1024

        try:
            # Get all photos with size and mtime
            photos = []
            total_size = 0
            for photo_file in self.photo_dir.rglob("*"):
                if photo_file.is_file():
                    stat = photo_file.stat()
                    photos.append((photo_file, stat.st_size, stat.st_mtime))
                    total_size += stat.st_size

            if total_size <= max_bytes:
                return {"deleted_count": 0, "freed_bytes": 0}

            # Sort by mtime (oldest first)
            photos.sort(key=lambda x: x[2])

            # Delete oldest until under limit
            for photo_file, size, mtime in photos:
                if total_size <= max_bytes:
                    break
                photo_file.unlink()
                deleted_count += 1
                freed_bytes += size
                total_size -= size

            if deleted_count > 0:
                logger.warning(
                    f"Enforced photo size limit: deleted {deleted_count} photos, freed {freed_bytes/(1024*1024):.2f}MB"
                )

        except Exception as e:
            logger.error(f"Photo size limit enforcement failed: {e}")

        return {"deleted_count": deleted_count, "freed_bytes": freed_bytes}

    def auto_cleanup(self) -> Dict:
        """
        Run automatic cleanup: photos + logs

        Returns:
            dict with total deleted_count, freed_bytes
        """
        photos = self.cleanup_old_photos()
        logs = self.cleanup_old_logs()
        size_limit = self.enforce_photo_size_limit()

        return {
            "deleted_count": photos["deleted_count"]
            + logs["deleted_count"]
            + size_limit["deleted_count"],
            "freed_bytes": photos["freed_bytes"]
            + logs["freed_bytes"]
            + size_limit["freed_bytes"],
        }
