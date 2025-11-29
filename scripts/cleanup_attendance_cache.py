#!/usr/bin/env python3
"""
Nightly Attendance Cache Cleanup

Clears synced attendance records from local cache while preserving:
- Unsynced records (offline queue)
- Today's records (for dashboard metrics)

Designed to run at 11:59 PM daily via cron.
"""
import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.utils.logger_config import setup_logger

logger = setup_logger(__name__)


def cleanup_synced_attendance(db_path: str = "data/attendance.db", keep_days: int = 0):
    """
    Delete synced attendance records older than keep_days.
    
    Args:
        db_path: Path to attendance database
        keep_days: Keep records from last N days (0 = today only)
    
    Returns:
        dict: Cleanup statistics
    """
    try:
        if not Path(db_path).exists():
            logger.error(f"Database not found: {db_path}")
            return {"error": "Database not found"}
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        # Count records before cleanup
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE synced=1 AND date(timestamp) < ?", (cutoff_str,))
        synced_old_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE synced=0")
        unsynced_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date(timestamp) >= ?", (cutoff_str,))
        recent_count = cursor.fetchone()[0]
        
        # Delete old synced records
        cursor.execute("""
            DELETE FROM attendance 
            WHERE synced=1 
            AND date(timestamp) < ?
        """, (cutoff_str,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM attendance")
        remaining_count = cursor.fetchone()[0]
        
        conn.close()
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "cutoff_date": cutoff_str,
            "deleted_synced_old": deleted_count,
            "kept_unsynced": unsynced_count,
            "kept_recent": recent_count,
            "remaining_total": remaining_count,
            "success": True
        }
        
        logger.info(f"Cleanup complete: deleted {deleted_count} old synced records, "
                   f"kept {unsynced_count} unsynced + {recent_count} recent records")
        
        return stats
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        return {"error": str(e), "success": False}


def cleanup_old_photos(photos_dir: str = "data/photos", keep_days: int = 7):
    """
    Delete old photo files to save disk space.
    
    Args:
        photos_dir: Directory containing photos
        keep_days: Keep photos from last N days
        
    Returns:
        dict: Cleanup statistics
    """
    try:
        photos_path = Path(photos_dir)
        if not photos_path.exists():
            logger.warning(f"Photos directory not found: {photos_dir}")
            return {"deleted_files": 0, "freed_mb": 0}
        
        cutoff_time = datetime.now() - timedelta(days=keep_days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        deleted_count = 0
        freed_bytes = 0
        
        for photo_file in photos_path.rglob("*.jpg"):
            try:
                file_mtime = photo_file.stat().st_mtime
                if file_mtime < cutoff_timestamp:
                    file_size = photo_file.stat().st_size
                    photo_file.unlink()
                    deleted_count += 1
                    freed_bytes += file_size
            except Exception as e:
                logger.warning(f"Failed to delete {photo_file}: {e}")
        
        freed_mb = freed_bytes / (1024 * 1024)
        
        logger.info(f"Photo cleanup: deleted {deleted_count} files, freed {freed_mb:.2f} MB")
        
        return {
            "deleted_files": deleted_count,
            "freed_mb": round(freed_mb, 2)
        }
        
    except Exception as e:
        logger.error(f"Photo cleanup failed: {e}", exc_info=True)
        return {"error": str(e)}


def main():
    """Run nightly cleanup."""
    print("🧹 Starting nightly attendance cache cleanup...")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Cleanup synced attendance records (keep today only)
    print("\n📊 Cleaning attendance database...")
    db_stats = cleanup_synced_attendance(keep_days=0)
    
    if db_stats.get("success"):
        print(f"  ✅ Deleted: {db_stats['deleted_synced_old']} old synced records")
        print(f"  ✅ Kept: {db_stats['kept_unsynced']} unsynced + {db_stats['kept_recent']} recent records")
        print(f"  ✅ Remaining total: {db_stats['remaining_total']} records")
    else:
        print(f"  ❌ Error: {db_stats.get('error')}")
    
    # Cleanup old photos (keep 7 days)
    print("\n📸 Cleaning old photos...")
    photo_stats = cleanup_old_photos(keep_days=7)
    
    if "error" not in photo_stats:
        print(f"  ✅ Deleted: {photo_stats['deleted_files']} files")
        print(f"  ✅ Freed: {photo_stats['freed_mb']} MB")
    else:
        print(f"  ❌ Error: {photo_stats.get('error')}")
    
    print("\n✨ Cleanup complete!")


if __name__ == "__main__":
    main()
