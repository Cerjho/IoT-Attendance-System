"""
Logger Configuration Module
Sets up logging for the IoT attendance system
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime


def setup_logger(
    name: str, log_dir: str = "data/logs", level=logging.INFO
) -> logging.Logger:
    """
    Setup logger with file and console handlers.

    Args:
        name: Logger name
        log_dir: Directory for log files
        level: Logging level

    Returns:
        logging.Logger: Configured logger
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )

    # File handler (detailed logs)
    log_filename = os.path.join(
        log_dir, f"attendance_system_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler = logging.handlers.RotatingFileHandler(
        log_filename, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Console handler (simple logs)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    return logger


class JSONLogFormatter(logging.Formatter):
    """Simple JSON formatter for structured logs."""
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "file": record.filename,
            "line": record.lineno,
        }
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


def get_json_logger(name: str, log_dir: str = "data/logs", level=logging.INFO) -> logging.Logger:
    """Get a logger configured to emit JSON lines (in addition to existing handlers if any)."""
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    log_filename = os.path.join(log_dir, f"attendance_json_{datetime.now().strftime('%Y%m%d')}.log")
    json_handler = logging.handlers.RotatingFileHandler(log_filename, maxBytes=5 * 1024 * 1024, backupCount=3)
    json_handler.setFormatter(JSONLogFormatter())
    json_handler.setLevel(level)
    # Avoid duplicate handler addition
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) and getattr(h, 'baseFilename', '').endswith('attendance_json_'+datetime.now().strftime('%Y%m%d')+'.log') for h in logger.handlers):
        logger.addHandler(json_handler)
    return logger
