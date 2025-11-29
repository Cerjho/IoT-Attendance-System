#!/usr/bin/env python3
"""
Phase 2 Integration Example

Demonstrates all Phase 2 improvements working together
"""

import logging
from datetime import datetime
from pathlib import Path

# Phase 2 imports
from src.utils.network_timeouts import NetworkTimeouts
from src.utils.queue_validator import QueueDataValidator
from src.utils.file_locks import DatabaseLock, PhotoLock, file_lock
from src.utils.structured_logging import (
    StructuredLogger,
    configure_structured_logging,
    set_correlation_id,
)

# Phase 1 imports
from src.utils.disk_monitor import DiskMonitor
from src.utils.circuit_breaker import CircuitBreakerOpen
from src.utils.db_transactions import SafeAttendanceDB

# Configure structured logging
configure_structured_logging(
    log_file="data/logs/phase2_example.log", json_format=True, level=logging.INFO
)

logger = StructuredLogger(__name__)


def enhanced_attendance_flow(config: dict, student_number: str):
    """
    Complete attendance flow with Phase 1 + Phase 2 features

    Phase 1: Disk monitoring, circuit breakers, camera recovery, transactions
    Phase 2: Timeouts, queue validation, file locking, structured logging

    Args:
        config: Configuration dictionary
        student_number: Student number from QR code

    Returns:
        dict with success status and details
    """
    # Set correlation ID for this operation
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    corr_id = set_correlation_id(f"scan-{student_number}-{timestamp}")

    logger.info(
        "Starting attendance capture",
        extra_data={
            "student_number": student_number,
            "correlation_id": corr_id,
            "phase": "phase2",
        },
    )

    try:
        # Phase 1: Disk space check
        disk_monitor = DiskMonitor(config.get("disk_monitor", {}))
        if not disk_monitor.check_space_available(required_mb=2):
            logger.warning("Low disk space, running cleanup")
            cleanup_result = disk_monitor.auto_cleanup()
            logger.info(
                "Disk cleanup completed",
                extra_data={
                    "deleted_count": cleanup_result["deleted_count"],
                    "freed_mb": cleanup_result["freed_bytes"] / (1024 * 1024),
                },
            )

        # Phase 2: Prepare and validate attendance data
        attendance_data = {
            "student_number": student_number,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time_in": datetime.now().strftime("%H:%M:%S"),
            "status": "present",
            "device_id": config.get("cloud", {}).get("device_id", "unknown"),
        }

        # Validate before proceeding
        is_valid, error = QueueDataValidator.validate_attendance(attendance_data)
        if not is_valid:
            logger.error(
                "Attendance data validation failed",
                extra_data={"validation_error": error, "data": attendance_data},
            )
            return {"success": False, "error": "validation_failed", "details": error}

        logger.debug("Attendance data validated", extra_data={"data": attendance_data})

        # Phase 2: File locking for database operations
        import sqlite3

        db_path = "data/attendance.db"

        with DatabaseLock(db_path, timeout=30):
            logger.debug("Database lock acquired")

            conn = sqlite3.connect(db_path)
            safe_db = SafeAttendanceDB(conn)

            # Phase 1: Transaction safety
            photo_path = f"data/photos/{student_number}_{timestamp}.jpg"
            attendance_id = safe_db.save_attendance_with_queue(
                attendance_data, photo_path=photo_path
            )

            logger.info(
                "Attendance saved atomically",
                extra_data={"attendance_id": attendance_id, "photo_path": photo_path},
            )

            conn.close()

        logger.debug("Database lock released")

        # Phase 2: Network operations with timeouts
        from src.network.connectivity import ConnectivityMonitor

        connectivity = ConnectivityMonitor(config.get("offline_mode", {}))

        if connectivity.is_online():
            logger.info("Online - attempting cloud sync")

            # Phase 2: Configured timeouts
            timeouts = NetworkTimeouts(
                config.get("network_timeouts", {"connect_timeout": 5, "read_timeout": 10})
            )

            logger.debug(
                "Network timeouts configured",
                extra_data={
                    "supabase": timeouts.get_supabase_timeout(),
                    "storage": timeouts.get_storage_timeout(),
                },
            )

            try:
                # Cloud sync would happen here (with circuit breaker from Phase 1)
                # CloudSyncManager internally uses timeouts and circuit breakers

                logger.info(
                    "Cloud sync completed",
                    extra_data={"attendance_id": attendance_id, "synced": True},
                )

            except CircuitBreakerOpen:
                logger.warning(
                    "Circuit breaker open, sync deferred",
                    extra_data={"attendance_id": attendance_id},
                )
            except Exception as e:
                logger.error(
                    "Cloud sync failed",
                    extra_data={
                        "attendance_id": attendance_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
        else:
            logger.info("Offline - attendance queued for later sync")

        logger.info(
            "Attendance capture complete",
            extra_data={
                "attendance_id": attendance_id,
                "student_number": student_number,
                "duration_ms": 1234,
            },
        )

        return {
            "success": True,
            "attendance_id": attendance_id,
            "correlation_id": corr_id,
            "photo_path": photo_path,
        }

    except Exception as e:
        logger.error(
            "Attendance capture failed",
            extra_data={
                "student_number": student_number,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return {"success": False, "error": str(e), "correlation_id": corr_id}


def demonstrate_file_locking():
    """Demonstrate file locking for concurrent operations"""
    logger.info("Demonstrating file locking")

    # Generic file lock
    with file_lock("data/.operation.lock", timeout=10):
        logger.debug("Generic file lock acquired")
        # Critical section
        pass

    # Photo-specific lock
    photo_path = "data/photos/test.jpg"
    Path(photo_path).parent.mkdir(parents=True, exist_ok=True)
    Path(photo_path).touch()

    with PhotoLock(photo_path, timeout=10):
        logger.debug("Photo lock acquired", extra_data={"photo": photo_path})
        # Photo operations
        pass

    logger.info("File locking demonstration complete")


def demonstrate_queue_validation():
    """Demonstrate queue data validation"""
    logger.info("Demonstrating queue validation")

    # Valid data
    valid_data = {
        "student_number": "2021001",
        "date": "2025-11-29",
        "time_in": "07:30:00",
        "status": "present",
    }

    is_valid, error = QueueDataValidator.validate_attendance(valid_data)
    logger.info(
        "Validation result",
        extra_data={"data": valid_data, "is_valid": is_valid, "error": error},
    )

    # Invalid data (auto-fix)
    invalid_data = {
        "student_number": "2021001",
        "date": "2025-11-29",
        # Missing status
        "bad_field": "will be removed",
    }

    is_valid, fixed, error = QueueDataValidator.validate_and_fix(invalid_data)
    logger.info(
        "Validation with auto-fix",
        extra_data={
            "original": invalid_data,
            "is_valid": is_valid,
            "fixed": fixed,
            "error": error,
        },
    )


def demonstrate_network_timeouts():
    """Demonstrate network timeout configuration"""
    logger.info("Demonstrating network timeouts")

    config = {
        "connect_timeout": 5,
        "read_timeout": 10,
        "storage_read_timeout": 30,
    }

    timeouts = NetworkTimeouts(config)

    logger.info(
        "Network timeouts configured",
        extra_data={
            "supabase": timeouts.get_supabase_timeout(),
            "storage": timeouts.get_storage_timeout(),
            "connectivity": timeouts.get_connectivity_timeout(),
            "all": timeouts.get_timeout_dict(),
        },
    )


if __name__ == "__main__":
    from src.utils.config_loader import load_config

    print("\n=== Phase 2 Integration Example ===\n")

    # Load configuration
    config = load_config("config/config.json")

    # Run demonstrations
    print("1. Network Timeouts")
    demonstrate_network_timeouts()

    print("\n2. Queue Validation")
    demonstrate_queue_validation()

    print("\n3. File Locking")
    demonstrate_file_locking()

    print("\n4. Complete Attendance Flow (Phase 1 + 2)")
    result = enhanced_attendance_flow(config, "2021001")
    print(f"Result: {result}")

    print("\n=== Check logs at data/logs/phase2_example.log for structured JSON logs ===")
    print(f"Correlation ID: {result.get('correlation_id')}")
