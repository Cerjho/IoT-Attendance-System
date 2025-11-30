"""
Structured Logging with Correlation IDs
Provides consistent log format with context tracking
"""
import json
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# Context variable for correlation ID (thread-safe)
correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logs

    Outputs logs in JSON format with correlation IDs and metadata
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON

        Args:
            record: Log record to format

        Returns:
            JSON string
        """
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        corr_id = correlation_id.get()
        if corr_id:
            log_entry["correlation_id"] = corr_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data

        # Add custom fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "extra_data",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry)


class CorrelationIdFilter(logging.Filter):
    """
    Filter that adds correlation ID to log records

    Adds correlation_id field to every log record
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add correlation ID to record

        Args:
            record: Log record to filter

        Returns:
            True (always passes record)
        """
        corr_id = correlation_id.get()
        if corr_id:
            record.correlation_id = corr_id
        return True


def set_correlation_id(corr_id: Optional[str] = None) -> str:
    """
    Set correlation ID for current context

    Args:
        corr_id: Correlation ID to set, or None to generate new UUID

    Returns:
        The correlation ID that was set
    """
    if corr_id is None:
        corr_id = str(uuid.uuid4())
    correlation_id.set(corr_id)
    return corr_id


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID

    Returns:
        Correlation ID or None
    """
    return correlation_id.get()


def clear_correlation_id():
    """Clear correlation ID from current context"""
    correlation_id.set(None)


class StructuredLogger:
    """
    Helper for structured logging with context

    Provides convenience methods for logging with extra data
    """

    def __init__(self, name: str):
        """
        Initialize structured logger

        Args:
            name: Logger name (typically __name__)
        """
        self.logger = logging.getLogger(name)

    def _log_with_extra(
        self, level: int, msg: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs
    ):
        """
        Log with extra structured data

        Args:
            level: Log level
            msg: Log message
            extra_data: Extra fields to include
            **kwargs: Additional keyword arguments for logger
        """
        if extra_data:
            kwargs["extra"] = {"extra_data": extra_data}
        self.logger.log(level, msg, **kwargs)

    def debug(self, msg: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """Log debug message with extra data"""
        self._log_with_extra(logging.DEBUG, msg, extra_data, **kwargs)

    def info(self, msg: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """Log info message with extra data"""
        self._log_with_extra(logging.INFO, msg, extra_data, **kwargs)

    def warning(self, msg: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """Log warning message with extra data"""
        self._log_with_extra(logging.WARNING, msg, extra_data, **kwargs)

    def error(self, msg: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """Log error message with extra data"""
        self._log_with_extra(logging.ERROR, msg, extra_data, **kwargs)

    def critical(self, msg: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs):
        """Log critical message with extra data"""
        self._log_with_extra(logging.CRITICAL, msg, extra_data, **kwargs)


def configure_structured_logging(
    log_file: Optional[str] = None,
    json_format: bool = True,
    level: int = logging.INFO,
):
    """
    Configure structured logging for application

    Args:
        log_file: Path to log file (optional)
        json_format: Use JSON format if True, else human-readable
        level: Log level
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add correlation ID filter
    corr_filter = CorrelationIdFilter()

    if json_format:
        # JSON formatter
        formatter = StructuredFormatter()
    else:
        # Human-readable formatter with correlation ID
        formatter = logging.Formatter(
            "%(asctime)s [%(correlation_id)s] %(levelname)-8s [%(name)s] %(message)s",
            defaults={"correlation_id": "-"},
        )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(corr_filter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        from pathlib import Path

        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(corr_filter)
        root_logger.addHandler(file_handler)
