"""
Professional Logging Factory
Single source of truth for all application logging
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json

from .structured_logging import StructuredFormatter, CorrelationIdFilter


class LogLevel:
    """Custom log levels"""
    SECURITY = 25  # Between INFO and WARNING
    AUDIT = 22     # Between INFO and WARNING
    METRICS = 21   # Between INFO and WARNING


# Register custom levels
logging.addLevelName(LogLevel.SECURITY, "SECURITY")
logging.addLevelName(LogLevel.AUDIT, "AUDIT")
logging.addLevelName(LogLevel.METRICS, "METRICS")


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'SECURITY': '\033[95m',   # Light Magenta
        'AUDIT': '\033[94m',      # Light Blue
        'METRICS': '\033[96m',    # Light Cyan
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        result = super().format(record)
        
        # Reset levelname for other handlers
        record.levelname = levelname
        return result


class LoggingFactory:
    """Factory for creating and configuring loggers"""
    
    _configured = False
    _config = None
    
    @classmethod
    def configure(cls, config: Dict[str, Any], environment: str = "production"):
        """
        Configure global logging from config
        
        Args:
            config: Logging configuration dictionary
            environment: Environment name (development, staging, production)
        """
        if cls._configured:
            return
        
        cls._config = config
        cls._environment = environment
        
        # Create log directory
        log_dir = config.get("log_dir", "data/logs")
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Configure root logger with level from config
        root_logger = logging.getLogger()
        global_level_str = config.get("level", "INFO")
        global_level = getattr(logging, global_level_str.upper(), logging.INFO)
        root_logger.setLevel(global_level)  # Use configured level, filter further in handlers
        
        # Remove existing handlers
        root_logger.handlers.clear()
        
        # Add correlation ID filter globally
        corr_filter = CorrelationIdFilter()
        
        # Configure outputs
        outputs = config.get("outputs", {})
        
        # File output (detailed logs)
        if outputs.get("file", {}).get("enabled", True):
            cls._add_file_handler(root_logger, config, corr_filter)
        
        # JSON file output (for machine parsing)
        if outputs.get("json_file", {}).get("enabled", True):
            cls._add_json_handler(root_logger, config, corr_filter)
        
        # Console output
        if outputs.get("console", {}).get("enabled", True):
            cls._add_console_handler(root_logger, config, corr_filter, environment)
        
        # Syslog/systemd journal output
        if outputs.get("syslog", {}).get("enabled", False):
            cls._add_syslog_handler(root_logger, config, corr_filter)
        
        cls._configured = True
        
        root_logger.info("Logging system configured", extra={
            "environment": environment,
            "log_dir": log_dir
        })
    
    @classmethod
    def _add_file_handler(cls, logger, config, corr_filter):
        """Add rotating file handler with detailed format"""
        log_dir = config.get("log_dir", "data/logs")
        file_config = config.get("outputs", {}).get("file", {})
        
        # Use date in filename
        filename = f"attendance_system_{datetime.now().strftime('%Y%m%d')}.log"
        filepath = os.path.join(log_dir, filename)
        
        rotation = file_config.get("rotation", {})
        max_bytes = rotation.get("max_size_mb", 100) * 1024 * 1024
        backup_count = rotation.get("backup_count", 10)
        
        handler = logging.handlers.RotatingFileHandler(
            filepath,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        
        # Detailed format for file
        formatter = logging.Formatter(
            "%(asctime)s [%(correlation_id)s] %(levelname)-8s [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            defaults={"correlation_id": "-"}
        )
        
        handler.setFormatter(formatter)
        handler.addFilter(corr_filter)
        
        # Read level from config (default: DEBUG for detailed file logs)
        file_level_str = file_config.get("level", "DEBUG")
        file_level = getattr(logging, file_level_str.upper(), logging.DEBUG)
        handler.setLevel(file_level)
        
        logger.addHandler(handler)
    
    @classmethod
    def _add_json_handler(cls, logger, config, corr_filter):
        """Add JSON handler for structured logs"""
        log_dir = config.get("log_dir", "data/logs")
        json_config = config.get("outputs", {}).get("json_file", {})
        
        filename = f"attendance_system_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = os.path.join(log_dir, filename)
        
        handler = logging.handlers.RotatingFileHandler(
            filepath,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5,
            encoding='utf-8'
        )
        
        handler.setFormatter(StructuredFormatter())
        handler.addFilter(corr_filter)
        
        # Read level from config (default: DEBUG for structured logs)
        json_level_str = json_config.get("level", "DEBUG")
        json_level = getattr(logging, json_level_str.upper(), logging.DEBUG)
        handler.setLevel(json_level)
        
        logger.addHandler(handler)
    
    @classmethod
    def _add_console_handler(cls, logger, config, corr_filter, environment):
        """Add console handler with appropriate formatting"""
        console_config = config.get("outputs", {}).get("console", {})
        level_str = console_config.get("level", "INFO")
        level = getattr(logging, level_str.upper(), logging.INFO)
        colored = console_config.get("colored", True) and environment != "production"
        
        handler = logging.StreamHandler(sys.stdout)
        
        if colored:
            # Colored format for development
            formatter = ColoredFormatter(
                "%(asctime)s [%(correlation_id)s] %(levelname)s [%(name)s] %(message)s",
                datefmt="%H:%M:%S",
                defaults={"correlation_id": "-"}
            )
        else:
            # Simple format for production (systemd handles timestamps)
            formatter = logging.Formatter(
                "[%(correlation_id)s] %(levelname)s [%(name)s] %(message)s",
                defaults={"correlation_id": "-"}
            )
        
        handler.setFormatter(formatter)
        handler.addFilter(corr_filter)
        handler.setLevel(level)
        
        logger.addHandler(handler)
    
    @classmethod
    def _add_syslog_handler(cls, logger, config, corr_filter):
        """Add syslog handler for systemd journal integration"""
        try:
            # Try systemd journal handler first (better for systemd integration)
            try:
                from systemd import journal
                
                handler = journal.JournalHandler(
                    SYSLOG_IDENTIFIER='attendance-system'
                )
                
                # Simple format - journal adds its own metadata
                formatter = logging.Formatter(
                    "[%(correlation_id)s] %(levelname)s [%(name)s] %(message)s",
                    defaults={"correlation_id": "-"}
                )
                
                handler.setFormatter(formatter)
                handler.addFilter(corr_filter)
                
                # Read level from config (default: INFO for production syslog)
                syslog_config = config.get("outputs", {}).get("syslog", {})
                syslog_level_str = syslog_config.get("level", "INFO")
                syslog_level = getattr(logging, syslog_level_str.upper(), logging.INFO)
                handler.setLevel(syslog_level)
                
                logger.addHandler(handler)
                return
                
            except ImportError:
                # Fall back to SysLogHandler if systemd.journal not available
                pass
            
            # Fallback: traditional syslog
            syslog_config = config.get("outputs", {}).get("syslog", {})
            address = syslog_config.get("address", "/dev/log")
            
            # Map facility name to constant
            facility_name = syslog_config.get("facility", "LOCAL0")
            facility_map = {
                "LOCAL0": logging.handlers.SysLogHandler.LOG_LOCAL0,
                "LOCAL1": logging.handlers.SysLogHandler.LOG_LOCAL1,
                "LOCAL2": logging.handlers.SysLogHandler.LOG_LOCAL2,
                "LOCAL3": logging.handlers.SysLogHandler.LOG_LOCAL3,
                "LOCAL4": logging.handlers.SysLogHandler.LOG_LOCAL4,
                "LOCAL5": logging.handlers.SysLogHandler.LOG_LOCAL5,
                "LOCAL6": logging.handlers.SysLogHandler.LOG_LOCAL6,
                "LOCAL7": logging.handlers.SysLogHandler.LOG_LOCAL7,
                "USER": logging.handlers.SysLogHandler.LOG_USER,
                "DAEMON": logging.handlers.SysLogHandler.LOG_DAEMON,
            }
            facility = facility_map.get(facility_name, logging.handlers.SysLogHandler.LOG_LOCAL0)
            
            handler = logging.handlers.SysLogHandler(
                address=address,
                facility=facility
            )
            
            formatter = logging.Formatter(
                "[%(correlation_id)s] %(levelname)s [%(name)s] %(message)s",
                defaults={"correlation_id": "-"}
            )
            
            handler.setFormatter(formatter)
            handler.addFilter(corr_filter)
            
            # Read level from config (default: INFO for production syslog)
            syslog_level_str = syslog_config.get("level", "INFO")
            syslog_level = getattr(logging, syslog_level_str.upper(), logging.INFO)
            handler.setLevel(syslog_level)
            
            logger.addHandler(handler)
        except Exception as e:
            # If syslog not available, log error but continue
            logger.warning(f"Failed to configure syslog handler: {e}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with custom level methods
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Enhanced logger with custom methods
        """
        logger = logging.getLogger(name)
        
        # Add custom level methods
        def security(msg, *args, **kwargs):
            if logger.isEnabledFor(LogLevel.SECURITY):
                logger._log(LogLevel.SECURITY, msg, args, **kwargs)
        
        def audit(msg, *args, **kwargs):
            if logger.isEnabledFor(LogLevel.AUDIT):
                logger._log(LogLevel.AUDIT, msg, args, **kwargs)
        
        def metrics(msg, *args, **kwargs):
            if logger.isEnabledFor(LogLevel.METRICS):
                logger._log(LogLevel.METRICS, msg, args, **kwargs)
        
        logger.security = security
        logger.audit = audit
        logger.metrics = metrics
        
        return logger


def get_logger(name: str) -> logging.Logger:
    """
    Convenience function to get a logger
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return LoggingFactory.get_logger(name)
