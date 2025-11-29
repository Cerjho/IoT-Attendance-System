"""
Tests for Structured Logging
"""
import json
import logging
import tempfile
from pathlib import Path

import pytest

from src.utils.structured_logging import (
    CorrelationIdFilter,
    StructuredFormatter,
    StructuredLogger,
    clear_correlation_id,
    configure_structured_logging,
    get_correlation_id,
    set_correlation_id,
)


def test_set_and_get_correlation_id():
    """Test setting and getting correlation ID"""
    corr_id = set_correlation_id("test-123")
    assert corr_id == "test-123"
    assert get_correlation_id() == "test-123"

    clear_correlation_id()
    assert get_correlation_id() is None


def test_auto_generate_correlation_id():
    """Test auto-generating correlation ID"""
    corr_id = set_correlation_id()
    assert corr_id is not None
    assert len(corr_id) == 36  # UUID format
    assert get_correlation_id() == corr_id

    clear_correlation_id()


def test_correlation_id_filter():
    """Test correlation ID filter adds field to records"""
    clear_correlation_id()
    set_correlation_id("filter-test")

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    filter = CorrelationIdFilter()
    filter.filter(record)

    assert hasattr(record, "correlation_id")
    assert record.correlation_id == "filter-test"

    clear_correlation_id()


def test_structured_formatter():
    """Test JSON formatter"""
    set_correlation_id("format-test")

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "format-test"

    formatter = StructuredFormatter()
    output = formatter.format(record)

    # Parse JSON
    log_entry = json.loads(output)

    assert log_entry["level"] == "INFO"
    assert log_entry["logger"] == "test_logger"
    assert log_entry["message"] == "Test message"
    assert log_entry["line"] == 42
    assert log_entry["correlation_id"] == "format-test"
    assert "timestamp" in log_entry

    clear_correlation_id()


def test_structured_formatter_with_exception():
    """Test formatter includes exception info"""
    try:
        raise ValueError("Test error")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="Error occurred",
        args=(),
        exc_info=exc_info,
    )

    formatter = StructuredFormatter()
    output = formatter.format(record)

    log_entry = json.loads(output)

    assert "exception" in log_entry
    assert "ValueError" in log_entry["exception"]
    assert "Test error" in log_entry["exception"]


def test_structured_logger():
    """Test StructuredLogger convenience methods"""
    logger = StructuredLogger("test_structured")

    # Capture logs
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as f:
        log_file = f.name

    try:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(StructuredFormatter())
        logging.getLogger("test_structured").addHandler(handler)
        logging.getLogger("test_structured").setLevel(logging.DEBUG)

        set_correlation_id("struct-test")

        # Log with extra data
        logger.info("Test message", extra_data={"user_id": 123, "action": "test"})

        handler.close()

        # Read log
        with open(log_file, "r") as f:
            log_line = f.readline()

        log_entry = json.loads(log_line)

        assert log_entry["message"] == "Test message"
        assert "extra" in log_entry
        assert log_entry["extra"]["user_id"] == 123
        assert log_entry["extra"]["action"] == "test"

    finally:
        Path(log_file).unlink()
        clear_correlation_id()


def test_configure_structured_logging_json():
    """Test configure structured logging with JSON format"""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_file = f.name

    try:
        configure_structured_logging(log_file=log_file, json_format=True, level=logging.INFO)

        set_correlation_id("config-test")
        logger = logging.getLogger("test_config")
        logger.info("Test log entry")

        # Read log
        with open(log_file, "r") as f:
            lines = f.readlines()

        # Should have logs (console + file)
        assert len(lines) > 0

        log_entry = json.loads(lines[-1])
        assert log_entry["message"] == "Test log entry"
        assert log_entry["correlation_id"] == "config-test"

    finally:
        Path(log_file).unlink()
        clear_correlation_id()


def test_configure_structured_logging_human_readable():
    """Test configure structured logging with human-readable format"""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_file = f.name

    try:
        configure_structured_logging(log_file=log_file, json_format=False, level=logging.INFO)

        set_correlation_id("human-test")
        logger = logging.getLogger("test_human")
        logger.info("Human readable message")

        # Read log
        with open(log_file, "r") as f:
            lines = f.readlines()

        # Should have human-readable format with correlation ID
        assert len(lines) > 0
        log_line = lines[-1]
        assert "human-test" in log_line
        assert "Human readable message" in log_line

    finally:
        Path(log_file).unlink()
        clear_correlation_id()


def test_structured_logger_all_levels():
    """Test all log levels"""
    logger = StructuredLogger("test_levels")

    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_file = f.name

    try:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(StructuredFormatter())
        logging.getLogger("test_levels").addHandler(handler)
        logging.getLogger("test_levels").setLevel(logging.DEBUG)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        handler.close()

        # Read logs
        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 5

        levels = [json.loads(line)["level"] for line in lines]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    finally:
        Path(log_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
