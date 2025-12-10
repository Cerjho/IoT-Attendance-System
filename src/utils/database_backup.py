#!/usr/bin/env python3
"""
Database Backup Manager
Automatic backups with corruption detection and cleanup
"""
import logging
import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)


class DatabaseBackupManager:
    """
    Automatic database backup with corruption detection
    - Hourly backups
    - Corruption detection via PRAGMA integrity_check
    - Automatic cleanup (keep last N backups)
    - Restore functionality
    """

    def __init__(
        self,
        db_path: str = "data/attendance.db",
        backup_dir: str = "data/backups",
        backup_interval: int = 3600,  # 1 hour
        keep_backups: int = 24,  # Keep 24 hourly backups (1 day)
        enabled: bool = True
    ):
        """
        Initialize backup manager
        
        Args:
            db_path: Path to database file
            backup_dir: Directory to store backups
            backup_interval: Seconds between backups
            keep_backups: Number of backups to retain
            enabled: Enable/disable automatic backups
        """
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_interval = backup_interval
        self.keep_backups = keep_backups
        self.enabled = enabled
        
        self.running = False
        self.thread = None
        
        # Create backup directory
        os.makedirs(self.backup_dir, exist_ok=True)
        
        if self.enabled:
            logger.info(
                f"Database backup manager initialized: "
                f"interval={backup_interval}s, keep={keep_backups}"
            )
        else:
            logger.info("Database backup manager disabled")

    def start(self):
        """Start automatic backup thread"""
        if not self.enabled:
            logger.debug("Backup manager disabled, not starting")
            return
        
        if self.running:
            logger.warning("Backup manager already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._backup_loop, daemon=True)
        self.thread.start()
        logger.info("Automatic backup started")

    def stop(self):
        """Stop automatic backup thread"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Automatic backup stopped")

    def _backup_loop(self):
        """Background backup loop"""
        logger.info("Backup loop started")
        
        # Do initial backup immediately
        self.create_backup()
        
        while self.running:
            try:
                time.sleep(self.backup_interval)
                
                if self.running:  # Check again after sleep
                    self.create_backup()
                
            except Exception as e:
                logger.error(f"Backup loop error: {e}")
                time.sleep(60)  # Wait before retrying
        
        logger.info("Backup loop stopped")

    def create_backup(self) -> Optional[str]:
        """
        Create database backup
        
        Returns:
            Path to backup file, or None if failed
        """
        try:
            # Check database integrity first
            if not self.check_integrity():
                logger.error("Database integrity check failed, backup aborted")
                return None
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"attendance_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Create backup using SQLite backup API (safer than file copy)
            self._sqlite_backup(self.db_path, backup_path)
            
            # Verify backup integrity
            if not self.check_integrity(backup_path):
                logger.error(f"Backup integrity check failed: {backup_path}")
                os.remove(backup_path)
                return None
            
            logger.info(f"✅ Database backup created: {backup_filename}")
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def _sqlite_backup(self, source_path: str, dest_path: str):
        """
        Create backup using SQLite backup API
        Safer than file copy as it handles locks properly
        """
        try:
            # Connect to source database
            source_conn = sqlite3.connect(source_path)
            
            # Connect to destination (will create if doesn't exist)
            dest_conn = sqlite3.connect(dest_path)
            
            # Perform backup
            source_conn.backup(dest_conn)
            
            # Close connections
            dest_conn.close()
            source_conn.close()
            
            logger.debug(f"SQLite backup completed: {dest_path}")
            
        except Exception as e:
            logger.error(f"SQLite backup failed: {e}")
            raise

    def check_integrity(self, db_path: Optional[str] = None) -> bool:
        """
        Check database integrity using PRAGMA integrity_check
        
        Args:
            db_path: Path to database (default: self.db_path)
            
        Returns:
            True if integrity check passed
        """
        db_path = db_path or self.db_path
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            
            conn.close()
            
            if result == "ok":
                logger.debug(f"Integrity check passed: {db_path}")
                return True
            else:
                logger.error(f"Integrity check failed: {db_path} - {result}")
                return False
                
        except Exception as e:
            logger.error(f"Integrity check error: {e}")
            return False

    def _cleanup_old_backups(self):
        """Remove old backups keeping only the most recent ones"""
        try:
            # Get all backup files
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("attendance_") and filename.endswith(".db"):
                    filepath = os.path.join(self.backup_dir, filename)
                    backups.append((filepath, os.path.getmtime(filepath)))
            
            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old backups
            removed_count = 0
            for filepath, _ in backups[self.keep_backups:]:
                try:
                    os.remove(filepath)
                    removed_count += 1
                    logger.debug(f"Removed old backup: {os.path.basename(filepath)}")
                except Exception as e:
                    logger.error(f"Failed to remove backup {filepath}: {e}")
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old backups")
            
        except Exception as e:
            logger.error(f"Backup cleanup error: {e}")

    def list_backups(self) -> List[dict]:
        """
        List all available backups
        
        Returns:
            List of backup info dicts
        """
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("attendance_") and filename.endswith(".db"):
                    filepath = os.path.join(self.backup_dir, filename)
                    stat = os.stat(filepath)
                    
                    backups.append({
                        "filename": filename,
                        "path": filepath,
                        "size_bytes": stat.st_size,
                        "size_mb": round(stat.st_size / 1024 / 1024, 2),
                        "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
        
        return backups

    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore database from backup
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if restore successful
        """
        try:
            # Check backup integrity
            if not self.check_integrity(backup_path):
                logger.error(f"Backup file is corrupt: {backup_path}")
                return False
            
            # Create safety backup of current database
            safety_backup = f"{self.db_path}.before_restore"
            shutil.copy2(self.db_path, safety_backup)
            logger.info(f"Safety backup created: {safety_backup}")
            
            # Restore backup
            shutil.copy2(backup_path, self.db_path)
            
            # Verify restored database
            if self.check_integrity():
                logger.info(f"✅ Database restored from: {backup_path}")
                return True
            else:
                logger.error("Restored database integrity check failed, reverting")
                shutil.copy2(safety_backup, self.db_path)
                return False
                
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def get_status(self) -> dict:
        """Get backup manager status"""
        backups = self.list_backups()
        
        return {
            "enabled": self.enabled,
            "running": self.running,
            "backup_interval_seconds": self.backup_interval,
            "keep_backups": self.keep_backups,
            "backup_dir": self.backup_dir,
            "total_backups": len(backups),
            "total_size_mb": round(sum(b["size_mb"] for b in backups), 2),
            "latest_backup": backups[0] if backups else None,
            "database_integrity": "ok" if self.check_integrity() else "corrupted"
        }
