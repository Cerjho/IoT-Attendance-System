#!/usr/bin/env python3
"""
Phase 1 Robustness Integration Example

Demonstrates how all Phase 1 components work together in a typical attendance flow.
This is a reference implementation showing best practices.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

# Phase 1 imports
from src.utils.disk_monitor import DiskMonitor
from src.utils.circuit_breaker import CircuitBreakerOpen
from src.utils.db_transactions import SafeAttendanceDB
from src.camera.camera_handler import CameraHandler

# Existing imports
from src.cloud.cloud_sync import CloudSyncManager
from src.database.sync_queue import SyncQueueManager
from src.network.connectivity import ConnectivityMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def robust_attendance_flow(config: dict, student_number: str):
    """
    Complete attendance capture flow with Phase 1 robustness features

    Args:
        config: Configuration dictionary
        student_number: Student number from QR code

    Returns:
        dict with success status and details
    """
    # Initialize components
    disk_monitor = DiskMonitor(config.get("disk_monitor", {}))
    conn = sqlite3.connect("data/attendance.db")
    safe_db = SafeAttendanceDB(conn)

    # Camera with recovery
    camera_config = config.get("camera", {})
    recovery_config = config.get("camera_recovery", {})
    camera = CameraHandler(
        camera_index=camera_config.get("index", 0),
        resolution=(
            camera_config.get("resolution", {}).get("width", 640),
            camera_config.get("resolution", {}).get("height", 480),
        ),
        max_init_retries=recovery_config.get("max_init_retries", 3),
        init_retry_delay=recovery_config.get("init_retry_delay", 5),
        health_check_interval=recovery_config.get("health_check_interval", 30),
    )

    # Cloud sync with circuit breakers
    sync_queue = SyncQueueManager("data/attendance.db")
    connectivity = ConnectivityMonitor(config.get("offline_mode", {}))
    cloud_sync = CloudSyncManager(config.get("cloud", {}), sync_queue, connectivity)

    try:
        # Step 1: Check disk space before capturing
        if not disk_monitor.check_space_available(required_mb=2):
            logger.error("Insufficient disk space, running cleanup...")
            cleanup_result = disk_monitor.auto_cleanup()
            logger.info(
                f"Cleanup freed {cleanup_result['freed_bytes']/(1024*1024):.2f}MB"
            )

            # Recheck after cleanup
            if not disk_monitor.check_space_available(required_mb=2):
                return {
                    "success": False,
                    "error": "disk_full",
                    "message": "Insufficient disk space even after cleanup",
                }

        # Step 2: Initialize camera (with automatic retry)
        if not camera.start():
            logger.error("Camera initialization failed after retries")
            return {
                "success": False,
                "error": "camera_unavailable",
                "message": "Camera not available, continuing in offline mode",
            }

        # Step 3: Capture photo (camera auto-recovers on transient failures)
        frame = camera.get_frame()
        if frame is None:
            logger.warning("Frame capture failed, camera may be recovering")
            return {
                "success": False,
                "error": "frame_capture_failed",
                "message": "Camera recovery in progress, try again",
            }

        # Step 4: Save photo to disk
        photo_dir = Path(config.get("disk_monitor", {}).get("photo_dir", "data/photos"))
        photo_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = photo_dir / f"{student_number}_{timestamp}.jpg"

        import cv2

        cv2.imwrite(str(photo_path), frame)
        logger.info(f"Photo saved: {photo_path}")

        # Step 5: Save to database with transaction safety
        attendance_data = {
            "student_number": student_number,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time_in": datetime.now().strftime("%H:%M:%S"),
            "time_out": None,
            "status": "present",
        }

        # Atomic operation: attendance + queue
        attendance_id = safe_db.save_attendance_with_queue(
            attendance_data,
            photo_path=str(photo_path),
            device_id=config.get("cloud", {}).get("device_id", "unknown"),
        )
        logger.info(f"Attendance {attendance_id} saved atomically")

        # Step 6: Cloud sync (with circuit breaker protection)
        if connectivity.is_online() and cloud_sync.enabled:
            try:
                # CloudSyncManager internally uses circuit breakers for REST calls
                result = cloud_sync.sync_attendance(
                    attendance_id, attendance_data, str(photo_path)
                )

                if result:
                    # Atomic sync completion
                    safe_db.mark_synced_and_cleanup_queue(
                        attendance_id, cloud_record_id=result
                    )
                    logger.info(f"Synced to cloud: {result}")
                else:
                    logger.warning("Cloud sync failed, will retry later")

            except CircuitBreakerOpen:
                logger.warning("Circuit breaker OPEN, deferring sync to queue")
            except Exception as e:
                logger.error(f"Cloud sync error: {e}, will retry later")
        else:
            logger.info("Offline mode, attendance queued for sync")

        return {
            "success": True,
            "attendance_id": attendance_id,
            "photo_path": str(photo_path),
            "synced": result if connectivity.is_online() else False,
        }

    except Exception as e:
        logger.error(f"Attendance flow error: {e}")
        return {"success": False, "error": str(e)}

    finally:
        camera.release()
        conn.close()


def periodic_maintenance(config: dict):
    """
    Periodic maintenance tasks using Phase 1 components

    Should be run daily or on startup
    """
    logger.info("Running periodic maintenance...")

    # Disk cleanup
    disk_monitor = DiskMonitor(config.get("disk_monitor", {}))
    cleanup_result = disk_monitor.auto_cleanup()
    logger.info(
        f"Cleaned {cleanup_result['deleted_count']} files, "
        f"freed {cleanup_result['freed_bytes']/(1024*1024):.2f}MB"
    )

    # Check disk usage
    usage = disk_monitor.get_disk_usage()
    logger.info(f"Disk space: {usage['free_percent']:.1f}% free")

    if usage["free_percent"] < 10:
        logger.warning("Low disk space, consider manual cleanup")

    # Circuit breaker status (if available)
    try:
        sync_queue = SyncQueueManager("data/attendance.db")
        connectivity = ConnectivityMonitor(config.get("offline_mode", {}))
        cloud_sync = CloudSyncManager(config.get("cloud", {}), sync_queue, connectivity)

        students_status = cloud_sync.circuit_breaker_students.get_status()
        attendance_status = cloud_sync.circuit_breaker_attendance.get_status()

        logger.info(f"Circuit breaker (students): {students_status['state']}")
        logger.info(f"Circuit breaker (attendance): {attendance_status['state']}")

        # Reset if manually requested
        # cloud_sync.circuit_breaker_students.reset()
        # cloud_sync.circuit_breaker_attendance.reset()

    except Exception as e:
        logger.warning(f"Circuit breaker status check failed: {e}")


if __name__ == "__main__":
    # Example configuration
    from src.utils.config_loader import load_config

    config = load_config("config/config.json")

    # Run periodic maintenance
    periodic_maintenance(config)

    # Example attendance flow
    result = robust_attendance_flow(config, "2021001")
    print(f"\nAttendance result: {result}")
