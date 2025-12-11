"""
Audit and Security Event Logging
Specialized logging for security events, data changes, and compliance
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class AuditLogger:
    """
    Logger for audit events and security incidents
    Writes to separate audit log file with structured format
    """
    
    def __init__(self, log_dir: str = "data/logs", level: int = logging.INFO):
        """
        Initialize audit logger
        
        Args:
            log_dir: Directory for audit logs
            level: Logging level (default: INFO)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dedicated audit logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(level)  # Use configured level
        self.logger.propagate = False  # Don't propagate to root logger
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Add audit file handler
        audit_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(audit_file, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        
        # Add JSON audit file handler
        json_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.json"
        json_handler = logging.FileHandler(json_file, encoding='utf-8')
        json_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(json_handler)
    
    def _log_event(
        self,
        event_type: str,
        message: str,
        severity: str = "INFO",
        **context
    ):
        """
        Log an audit event
        
        Args:
            event_type: Type of event (SECURITY, ACCESS, DATA_CHANGE, etc.)
            message: Human-readable message
            severity: Event severity (INFO, WARNING, CRITICAL)
            **context: Additional context fields
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "severity": severity,
            "message": message,
            **context
        }
        
        # Write as JSON
        self.logger.info(json.dumps(event))
    
    def security_event(
        self,
        message: str,
        threat_level: str = "LOW",
        **context
    ):
        """
        Log a security event
        
        Args:
            message: Security event description
            threat_level: LOW, MEDIUM, HIGH, CRITICAL
            **context: Additional context
        
        Example:
            audit_logger.security_event(
                "Unauthorized access attempt",
                threat_level="MEDIUM",
                student_id="unknown",
                reason="not_in_roster"
            )
        """
        severity = "WARNING" if threat_level in ["MEDIUM", "HIGH"] else "CRITICAL"
        if threat_level == "CRITICAL":
            severity = "CRITICAL"
        
        self._log_event(
            "SECURITY",
            message,
            severity=severity,
            threat_level=threat_level,
            **context
        )
    
    def access_event(
        self,
        action: str,
        resource: str,
        status: str = "success",
        **context
    ):
        """
        Log an access event
        
        Args:
            action: Action performed (LOGIN, LOGOUT, VIEW, etc.)
            resource: Resource accessed
            status: success or failure
            **context: Additional context
        
        Example:
            audit_logger.access_event(
                action="LOGIN",
                resource="attendance_system",
                status="success",
                student_id="2021001",
                device_id="pi-lab-01"
            )
        """
        self._log_event(
            "ACCESS",
            f"{action} {resource} - {status}",
            severity="INFO",
            action=action,
            resource=resource,
            status=status,
            **context
        )
    
    def data_change(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        before: Optional[Dict] = None,
        after: Optional[Dict] = None,
        **context
    ):
        """
        Log a data change event
        
        Args:
            entity_type: Type of entity (student, attendance, etc.)
            entity_id: Entity identifier
            action: CREATE, UPDATE, DELETE
            before: Data before change (for UPDATE/DELETE)
            after: Data after change (for CREATE/UPDATE)
            **context: Additional context
        
        Example:
            audit_logger.data_change(
                entity_type="attendance",
                entity_id="rec-123",
                action="CREATE",
                after={"student_id": "2021001", "status": "present"},
                device_id="pi-lab-01"
            )
        """
        self._log_event(
            "DATA_CHANGE",
            f"{action} {entity_type} {entity_id}",
            severity="INFO",
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before=before,
            after=after,
            **context
        )
    
    def compliance_event(
        self,
        message: str,
        regulation: str,
        **context
    ):
        """
        Log a compliance-related event
        
        Args:
            message: Compliance event description
            regulation: Regulation/policy reference
            **context: Additional context
        
        Example:
            audit_logger.compliance_event(
                "Photo data retained beyond policy limit",
                regulation="DATA_RETENTION_POLICY",
                photo_count=150,
                retention_days=45
            )
        """
        self._log_event(
            "COMPLIANCE",
            message,
            severity="WARNING",
            regulation=regulation,
            **context
        )
    
    def system_event(
        self,
        message: str,
        component: str,
        status: str = "INFO",
        **context
    ):
        """
        Log a system-level event
        
        Args:
            message: System event description
            component: System component affected
            status: INFO, WARNING, ERROR
            **context: Additional context
        
        Example:
            audit_logger.system_event(
                "System startup completed",
                component="attendance_system",
                version="2.0.0",
                device_id="pi-lab-01"
            )
        """
        self._log_event(
            "SYSTEM",
            message,
            severity=status,
            component=component,
            **context
        )


class BusinessEventLogger:
    """
    Logger for business metrics and KPIs
    """
    
    def __init__(self, log_dir: str = "data/logs", level: int = logging.INFO):
        """
        Initialize business event logger
        
        Args:
            log_dir: Directory for business logs
            level: Logging level (default: INFO)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dedicated metrics logger
        self.logger = logging.getLogger("business_metrics")
        self.logger.setLevel(level)  # Use configured level
        self.logger.propagate = False
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Add metrics file handler (JSON only)
        metrics_file = self.log_dir / f"business_metrics_{datetime.now().strftime('%Y%m%d')}.json"
        handler = logging.FileHandler(metrics_file, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
    
    def log_event(
        self,
        event_name: str,
        **metrics
    ):
        """
        Log a business event with metrics
        
        Args:
            event_name: Event name (student_attendance, photo_captured, etc.)
            **metrics: Key-value metrics
        
        Example:
            business_logger.log_event(
                "student_attendance",
                student_id="2021001",
                type="LOGIN",
                status="ON_TIME",
                processing_time_ms=456
            )
        """
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event_name,
            **metrics
        }
        
        self.logger.info(json.dumps(event))
    
    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        **context
    ):
        """
        Log a performance metric
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            **context: Additional context
        """
        self.log_event(
            "performance",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            **context
        )
    
    def log_error_rate(
        self,
        component: str,
        error_count: int,
        total_count: int,
        **context
    ):
        """
        Log error rate metric
        
        Args:
            component: Component name
            error_count: Number of errors
            total_count: Total operations
            **context: Additional context
        """
        error_rate = (error_count / total_count * 100) if total_count > 0 else 0
        
        self.log_event(
            "error_rate",
            component=component,
            error_count=error_count,
            total_count=total_count,
            error_rate=round(error_rate, 2),
            **context
        )


# Global instances
_audit_logger = None
_business_logger = None


def get_audit_logger(log_dir: str = "data/logs", config: dict = None) -> AuditLogger:
    """Get global audit logger instance
    
    Args:
        log_dir: Directory for audit logs
        config: Optional logging config dict to read level from
    """
    global _audit_logger
    if _audit_logger is None:
        level = logging.INFO
        if config:
            level_str = config.get("audit", {}).get("level", "INFO")
            level = getattr(logging, level_str.upper(), logging.INFO)
        _audit_logger = AuditLogger(log_dir, level=level)
    return _audit_logger


def get_business_logger(log_dir: str = "data/logs", config: dict = None) -> BusinessEventLogger:
    """Get global business logger instance
    
    Args:
        log_dir: Directory for business logs
        config: Optional logging config dict to read level from
    """
    global _business_logger
    if _business_logger is None:
        level = logging.INFO
        if config:
            level_str = config.get("business_metrics", {}).get("level", "INFO")
            level = getattr(logging, level_str.upper(), logging.INFO)
        _business_logger = BusinessEventLogger(log_dir, level=level)
    return _business_logger
