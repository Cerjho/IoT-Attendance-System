#!/usr/bin/env python3
"""
Test script to verify professional logging implementation
Tests all logging outputs: console, file, JSON, audit, business metrics
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.utils.logging_factory import LoggingFactory, get_logger
from src.utils.log_decorators import log_execution_time, log_with_context
from src.utils.audit_logger import get_audit_logger, get_business_logger
from src.utils.structured_logging import set_correlation_id
from src.utils.config_loader import load_config
import uuid


def test_basic_logging(logger):
    """Test basic logging at all levels"""
    print("\n" + "=" * 70)
    print("TEST 1: Basic Logging Levels")
    print("=" * 70)
    
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")
    
    # Test custom levels
    logger.security("This is a SECURITY event")
    logger.audit("This is an AUDIT event")
    logger.metrics("This is a METRICS event")
    
    print("✅ Basic logging test complete\n")


def test_structured_logging(logger):
    """Test structured logging with extra context"""
    print("=" * 70)
    print("TEST 2: Structured Logging with Context")
    print("=" * 70)
    
    # Set correlation ID
    set_correlation_id(f"test-{uuid.uuid4().hex[:8]}")
    
    logger.info("Processing student attendance", extra={
        "student_id": "2021001",
        "scan_type": "LOGIN",
        "device_id": "pi-lab-01"
    })
    
    logger.warning("Slow operation detected", extra={
        "operation": "face_detection",
        "duration_ms": 1523.45,
        "threshold_ms": 1000
    })
    
    print("✅ Structured logging test complete\n")


@log_execution_time(slow_threshold_ms=100.0)
def slow_operation():
    """Simulated slow operation"""
    time.sleep(0.15)
    return "completed"


@log_with_context(operation="test_operation")
def operation_with_context(logger, value):
    """Function with context tracking"""
    logger.info("Starting operation", extra={"input_value": value})
    time.sleep(0.05)
    logger.info("Operation complete")
    return value * 2


def test_decorators(logger):
    """Test logging decorators"""
    print("=" * 70)
    print("TEST 3: Logging Decorators")
    print("=" * 70)
    
    # Test execution time logging
    result = slow_operation()
    print(f"Slow operation result: {result}")
    
    # Test context logging
    result = operation_with_context(logger, 42)
    print(f"Operation result: {result}")
    
    print("✅ Decorator test complete\n")


def test_audit_logging(audit_logger):
    """Test audit logging"""
    print("=" * 70)
    print("TEST 4: Audit Logging")
    print("=" * 70)
    
    # Security event
    audit_logger.security_event(
        "Unauthorized access attempt",
        threat_level="MEDIUM",
        student_id="unknown",
        reason="not_in_roster",
        device_id="pi-lab-01"
    )
    print("✅ Security event logged")
    
    # Access event
    audit_logger.access_event(
        action="LOGIN",
        resource="attendance_system",
        status="success",
        student_id="2021001",
        device_id="pi-lab-01"
    )
    print("✅ Access event logged")
    
    # Data change event
    audit_logger.data_change(
        entity_type="attendance",
        entity_id="rec-123",
        action="CREATE",
        after={
            "student_id": "2021001",
            "status": "present",
            "scan_type": "LOGIN"
        },
        device_id="pi-lab-01"
    )
    print("✅ Data change event logged")
    
    # System event
    audit_logger.system_event(
        "System startup completed",
        component="attendance_system",
        version="2.0.0",
        device_id="pi-lab-01"
    )
    print("✅ System event logged")
    
    print("✅ Audit logging test complete\n")


def test_business_metrics(business_logger):
    """Test business metrics logging"""
    print("=" * 70)
    print("TEST 5: Business Metrics")
    print("=" * 70)
    
    # Attendance event
    business_logger.log_event(
        "student_attendance",
        student_id="2021001",
        record_id="rec-123",
        scan_type="LOGIN",
        status="ON_TIME",
        processing_time_ms=456.78,
        device_id="pi-lab-01"
    )
    print("✅ Attendance metric logged")
    
    # Performance metric
    business_logger.log_performance(
        operation="face_detection",
        duration_ms=234.56,
        frame_count=45
    )
    print("✅ Performance metric logged")
    
    # Error rate metric
    business_logger.log_error_rate(
        component="camera",
        error_count=3,
        total_count=100,
        period="1h"
    )
    print("✅ Error rate metric logged")
    
    print("✅ Business metrics test complete\n")


def test_exception_logging(logger):
    """Test exception logging"""
    print("=" * 70)
    print("TEST 6: Exception Logging")
    print("=" * 70)
    
    try:
        # Simulate an error
        result = 10 / 0
    except Exception as e:
        logger.error(
            "Division by zero error",
            extra={
                "operation": "calculate",
                "input": 10,
                "divisor": 0
            },
            exc_info=True
        )
        print("✅ Exception logged with traceback")
    
    print("✅ Exception logging test complete\n")


def verify_log_files(log_dir):
    """Verify that log files were created"""
    print("=" * 70)
    print("TEST 7: Verify Log Files Created")
    print("=" * 70)
    
    import os
    from datetime import datetime
    
    today = datetime.now().strftime("%Y%m%d")
    
    expected_files = [
        f"attendance_system_{today}.log",
        f"attendance_system_{today}.json",
        f"audit_{today}.log",
        f"audit_{today}.json",
        f"business_metrics_{today}.json"
    ]
    
    for filename in expected_files:
        filepath = os.path.join(log_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"✅ {filename} ({size} bytes)")
        else:
            print(f"❌ {filename} NOT FOUND")
    
    print("\n✅ Log file verification complete\n")


def main():
    """Run all logging tests"""
    print("\n" + "=" * 70)
    print("PROFESSIONAL LOGGING SYSTEM TEST")
    print("=" * 70)
    
    # Load configuration
    config = load_config("config/config.json")
    
    # Configure logging
    environment = "development"
    logging_config = config.get("logging", {})
    LoggingFactory.configure(logging_config, environment=environment)
    
    # Get loggers
    logger = get_logger(__name__)
    log_dir = logging_config.get("log_dir", "data/logs")
    audit_logger = get_audit_logger(log_dir)
    business_logger = get_business_logger(log_dir)
    
    print(f"Environment: {environment}")
    print(f"Log directory: {log_dir}")
    print("")
    
    # Run tests
    test_basic_logging(logger)
    test_structured_logging(logger)
    test_decorators(logger)
    test_audit_logging(audit_logger)
    test_business_metrics(business_logger)
    test_exception_logging(logger)
    verify_log_files(log_dir)
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print("\nCheck the following files:")
    print(f"  - {log_dir}/attendance_system_*.log (human-readable)")
    print(f"  - {log_dir}/attendance_system_*.json (machine-parseable)")
    print(f"  - {log_dir}/audit_*.log (audit trail)")
    print(f"  - {log_dir}/audit_*.json (audit trail JSON)")
    print(f"  - {log_dir}/business_metrics_*.json (business metrics)")
    print("")


if __name__ == "__main__":
    main()
