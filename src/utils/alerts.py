"""
Alert Notifications System

Sends alerts for critical system events via multiple channels
(logs, SMS, webhook, email simulation).
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from src.utils.logging_factory import get_logger
from src.utils.log_decorators import log_execution_time
from src.utils.audit_logger import get_business_logger

logger = get_logger(__name__)
business_logger = get_business_logger()


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    """Alert types."""

    DISK_FULL = "disk_full"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    SYNC_FAILURE = "sync_failure"
    CAMERA_FAILURE = "camera_failure"
    DATABASE_ERROR = "database_error"
    NETWORK_OFFLINE = "network_offline"
    QUEUE_OVERFLOW = "queue_overflow"
    SYSTEM_ERROR = "system_error"


@dataclass
class Alert:
    """Alert data structure."""

    alert_type: AlertType
    severity: AlertSeverity
    message: str
    component: str
    timestamp: datetime
    details: Optional[Dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details or {},
        }


class AlertChannel:
    """Base class for alert channels."""

    def send(self, alert: Alert) -> bool:
        """
        Send alert.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully
        """
        raise NotImplementedError


class LogAlertChannel(AlertChannel):
    """Send alerts to log file."""

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize log alert channel.

        Args:
            log_file: Optional specific log file for alerts
        """
        self.log_file = log_file
        if log_file:
            # Create separate logger for alerts
            self.alert_logger = logging.getLogger("alerts")
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            self.alert_logger.addHandler(handler)
            self.alert_logger.setLevel(logging.INFO)
        else:
            self.alert_logger = logger

    def send(self, alert: Alert) -> bool:
        """Send alert to log."""
        try:
            log_level = {
                AlertSeverity.INFO: logging.INFO,
                AlertSeverity.WARNING: logging.WARNING,
                AlertSeverity.ERROR: logging.ERROR,
                AlertSeverity.CRITICAL: logging.CRITICAL,
            }[alert.severity]

            self.alert_logger.log(
                log_level,
                f"ALERT [{alert.alert_type.value}] {alert.message}",
                extra={"alert": alert.to_dict()},
            )
            return True

        except Exception as e:
            logger.error(f"Error sending log alert: {e}", exc_info=True)
            return False


class FileAlertChannel(AlertChannel):
    """Save alerts to JSON file."""

    def __init__(self, alert_file: str = "data/logs/alerts.json"):
        """
        Initialize file alert channel.

        Args:
            alert_file: Path to alerts file
        """
        self.alert_file = Path(alert_file)
        self.alert_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if doesn't exist
        if not self.alert_file.exists():
            self.alert_file.write_text("[]")

    def send(self, alert: Alert) -> bool:
        """Save alert to file."""
        try:
            # Read existing alerts
            alerts = []
            if self.alert_file.exists():
                with open(self.alert_file) as f:
                    alerts = json.load(f)

            # Append new alert
            alerts.append(alert.to_dict())

            # Keep only last 1000 alerts
            alerts = alerts[-1000:]

            # Write back
            with open(self.alert_file, "w") as f:
                json.dump(alerts, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Error saving alert to file: {e}", exc_info=True)
            return False


class SMSAlertChannel(AlertChannel):
    """Send critical alerts via SMS."""

    def __init__(self, sms_config: dict):
        """
        Initialize SMS alert channel.

        Args:
            sms_config: SMS configuration
        """
        self.config = sms_config
        self.enabled = sms_config.get("enabled", False)
        self.admin_numbers = sms_config.get("admin_numbers", [])

    def send(self, alert: Alert) -> bool:
        """Send alert via SMS."""
        if not self.enabled or not self.admin_numbers:
            logger.debug("SMS alerts not configured, skipping")
            return False

        # Only send critical alerts via SMS
        if alert.severity != AlertSeverity.CRITICAL:
            return False

        try:
            from src.notifications.sms_notifier import SMSNotifier

            notifier = SMSNotifier(self.config)

            message = f"CRITICAL ALERT: {alert.message}"
            if alert.details:
                message += f" | Details: {alert.details}"

            for number in self.admin_numbers:
                success = notifier.send_sms(number, message)
                if not success:
                    logger.warning(f"Failed to send SMS alert to {number}")

            return True

        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}", exc_info=True)
            return False


class WebhookAlertChannel(AlertChannel):
    """Send alerts to webhook endpoint."""

    def __init__(self, webhook_config: dict):
        """
        Initialize webhook alert channel.

        Args:
            webhook_config: Webhook configuration
        """
        self.config = webhook_config
        self.enabled = webhook_config.get("enabled", False)
        self.url = webhook_config.get("url")
        self.auth_header = webhook_config.get("auth_header")

    def send(self, alert: Alert) -> bool:
        """Send alert to webhook."""
        if not self.enabled or not self.url:
            logger.debug("Webhook alerts not configured, skipping")
            return False

        try:
            business_logger.log_event(
                "alert_webhook_send",
                alert_type=alert.alert_type.value,
                severity=alert.severity.value,
                component=alert.component
            )
            import requests
            from src.utils.network_timeouts import NetworkTimeouts

            timeouts = NetworkTimeouts({"connect_timeout": 5, "read_timeout": 10})

            headers = {"Content-Type": "application/json"}
            if self.auth_header:
                headers["Authorization"] = self.auth_header

            payload = alert.to_dict()

            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=timeouts.get_connectivity_timeout(),
            )

            response.raise_for_status()
            logger.debug(f"Sent alert to webhook: {self.url}")
            return True

        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}", exc_info=True)
            return False


class AlertManager:
    """
    Manages system alerts.

    Routes alerts to multiple channels based on severity and configuration.
    Tracks alert history and prevents alert storms.
    """

    def __init__(self, config: dict):
        """
        Initialize alert manager.

        Args:
            config: Alert configuration
        """
        self.config = config.get("alerts", {})
        self.enabled = self.config.get("enabled", True)
        self.channels: List[AlertChannel] = []
        self.alert_history: List[Alert] = []
        self.alert_cooldowns: Dict[str, datetime] = {}

        if self.enabled:
            self._initialize_channels()
            logger.info("Alert manager initialized")
        else:
            logger.info("Alert manager disabled")

    def _initialize_channels(self):
        """Initialize alert channels."""
        # Always add log channel
        log_file = self.config.get("log_file", "data/logs/alerts.log")
        self.channels.append(LogAlertChannel(log_file))

        # Add file channel
        alert_file = self.config.get("alert_file", "data/logs/alerts.json")
        self.channels.append(FileAlertChannel(alert_file))

        # Add SMS channel if configured
        sms_config = self.config.get("sms", {})
        if sms_config.get("enabled"):
            self.channels.append(SMSAlertChannel(sms_config))

        # Add webhook channel if configured
        webhook_config = self.config.get("webhook", {})
        if webhook_config.get("enabled"):
            self.channels.append(WebhookAlertChannel(webhook_config))

        logger.info(f"Initialized {len(self.channels)} alert channels")

    def send_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        component: str,
        details: Optional[Dict] = None,
    ) -> bool:
        """
        Send an alert.

        Args:
            alert_type: Type of alert
            severity: Severity level
            message: Alert message
            component: Component name
            details: Optional details

        Returns:
            True if sent successfully to at least one channel
        """
        if not self.enabled:
            return False

        # Check cooldown
        cooldown_key = f"{alert_type.value}:{component}"
        if self._is_in_cooldown(cooldown_key):
            logger.debug(f"Alert {cooldown_key} in cooldown, skipping")
            return False

        # Create alert
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            component=component,
            timestamp=datetime.now(),
            details=details,
        )

        # Send to all channels
        success_count = 0
        for channel in self.channels:
            try:
                if channel.send(alert):
                    success_count += 1
            except Exception as e:
                logger.error(
                    f"Error sending alert via {type(channel).__name__}: {e}",
                    exc_info=True,
                )

        # Update history and cooldown
        self.alert_history.append(alert)
        self._update_cooldown(cooldown_key)

        # Trim history (keep last 100)
        self.alert_history = self.alert_history[-100:]

        logger.info(
            f"Sent alert to {success_count}/{len(self.channels)} channels",
            extra={"alert": alert.to_dict()},
        )

        return success_count > 0

    def _is_in_cooldown(self, key: str) -> bool:
        """Check if alert is in cooldown period."""
        if key not in self.alert_cooldowns:
            return False

        cooldown_minutes = self.config.get("cooldown_minutes", 5)
        last_sent = self.alert_cooldowns[key]
        elapsed = (datetime.now() - last_sent).total_seconds() / 60

        return elapsed < cooldown_minutes

    def _update_cooldown(self, key: str):
        """Update alert cooldown timestamp."""
        self.alert_cooldowns[key] = datetime.now()

    # Convenience methods for common alerts

    def alert_disk_full(self, usage_percent: float, path: str):
        """Alert for disk full condition."""
        self.send_alert(
            AlertType.DISK_FULL,
            AlertSeverity.CRITICAL,
            f"Disk usage at {usage_percent:.1f}%",
            "disk_monitor",
            {"usage_percent": usage_percent, "path": path},
        )

    def alert_circuit_breaker_open(self, service: str):
        """Alert for circuit breaker opening."""
        self.send_alert(
            AlertType.CIRCUIT_BREAKER_OPEN,
            AlertSeverity.ERROR,
            f"Circuit breaker opened for {service}",
            "circuit_breaker",
            {"service": service},
        )

    def alert_sync_failure(self, error: str, retry_count: int):
        """Alert for sync failure."""
        severity = (
            AlertSeverity.CRITICAL if retry_count >= 5 else AlertSeverity.WARNING
        )
        self.send_alert(
            AlertType.SYNC_FAILURE,
            severity,
            f"Cloud sync failed: {error}",
            "cloud_sync",
            {"error": error, "retry_count": retry_count},
        )

    def alert_camera_failure(self, error: str):
        """Alert for camera failure."""
        self.send_alert(
            AlertType.CAMERA_FAILURE,
            AlertSeverity.CRITICAL,
            f"Camera failure: {error}",
            "camera",
            {"error": error},
        )

    def alert_database_error(self, error: str):
        """Alert for database error."""
        self.send_alert(
            AlertType.DATABASE_ERROR,
            AlertSeverity.ERROR,
            f"Database error: {error}",
            "database",
            {"error": error},
        )

    def alert_network_offline(self):
        """Alert for network going offline."""
        self.send_alert(
            AlertType.NETWORK_OFFLINE,
            AlertSeverity.WARNING,
            "Network connectivity lost",
            "network",
            {},
        )

    def alert_queue_overflow(self, queue_size: int, limit: int):
        """Alert for sync queue overflow."""
        self.send_alert(
            AlertType.QUEUE_OVERFLOW,
            AlertSeverity.ERROR,
            f"Sync queue overflow: {queue_size} records (limit: {limit})",
            "sync_queue",
            {"queue_size": queue_size, "limit": limit},
        )

    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """
        Get recent alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of alert dictionaries
        """
        return [alert.to_dict() for alert in self.alert_history[-limit:]]
