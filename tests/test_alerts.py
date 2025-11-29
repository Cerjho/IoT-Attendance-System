"""
Tests for Alert Notifications System

Tests alert channels, severity handling, cooldowns, and multi-channel routing.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.utils.alerts import (
    Alert,
    AlertChannel,
    AlertManager,
    AlertSeverity,
    AlertType,
    FileAlertChannel,
    LogAlertChannel,
    SMSAlertChannel,
    WebhookAlertChannel,
)


class TestAlert:
    """Test Alert data structure."""

    def test_alert_creation(self):
        """Test creating alert."""
        alert = Alert(
            alert_type=AlertType.DISK_FULL,
            severity=AlertSeverity.CRITICAL,
            message="Disk usage at 95%",
            component="disk_monitor",
            timestamp=datetime.now(),
            details={"usage": 95},
        )

        assert alert.alert_type == AlertType.DISK_FULL
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.component == "disk_monitor"

    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        timestamp = datetime.now()
        alert = Alert(
            alert_type=AlertType.SYNC_FAILURE,
            severity=AlertSeverity.ERROR,
            message="Sync failed",
            component="cloud_sync",
            timestamp=timestamp,
            details={"error": "timeout"},
        )

        alert_dict = alert.to_dict()

        assert alert_dict["alert_type"] == "sync_failure"
        assert alert_dict["severity"] == "error"
        assert alert_dict["message"] == "Sync failed"
        assert alert_dict["timestamp"] == timestamp.isoformat()
        assert alert_dict["details"]["error"] == "timeout"


class TestLogAlertChannel:
    """Test LogAlertChannel."""

    def test_send_alert(self, caplog):
        """Test sending alert to log."""
        channel = LogAlertChannel()

        alert = Alert(
            alert_type=AlertType.DISK_FULL,
            severity=AlertSeverity.WARNING,
            message="Test alert",
            component="test",
            timestamp=datetime.now(),
        )

        result = channel.send(alert)
        assert result is True

    def test_send_with_custom_log_file(self, tmp_path):
        """Test sending to custom log file."""
        log_file = tmp_path / "alerts.log"
        channel = LogAlertChannel(str(log_file))

        alert = Alert(
            alert_type=AlertType.CAMERA_FAILURE,
            severity=AlertSeverity.CRITICAL,
            message="Camera failed",
            component="camera",
            timestamp=datetime.now(),
        )

        channel.send(alert)

        assert log_file.exists()


class TestFileAlertChannel:
    """Test FileAlertChannel."""

    def test_send_alert(self, tmp_path):
        """Test sending alert to file."""
        alert_file = tmp_path / "alerts.json"
        channel = FileAlertChannel(str(alert_file))

        alert = Alert(
            alert_type=AlertType.SYNC_FAILURE,
            severity=AlertSeverity.ERROR,
            message="Sync failed",
            component="cloud_sync",
            timestamp=datetime.now(),
        )

        result = channel.send(alert)
        assert result is True
        assert alert_file.exists()

        # Check file content
        with open(alert_file) as f:
            alerts = json.load(f)

        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "sync_failure"

    def test_multiple_alerts(self, tmp_path):
        """Test sending multiple alerts."""
        alert_file = tmp_path / "alerts.json"
        channel = FileAlertChannel(str(alert_file))

        for i in range(3):
            alert = Alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.ERROR,
                message=f"Error {i}",
                component="test",
                timestamp=datetime.now(),
            )
            channel.send(alert)

        with open(alert_file) as f:
            alerts = json.load(f)

        assert len(alerts) == 3

    def test_alert_limit(self, tmp_path):
        """Test alert file size limit."""
        alert_file = tmp_path / "alerts.json"
        channel = FileAlertChannel(str(alert_file))

        # Send more than limit (1000)
        for i in range(1050):
            alert = Alert(
                alert_type=AlertType.SYSTEM_ERROR,
                severity=AlertSeverity.INFO,
                message=f"Alert {i}",
                component="test",
                timestamp=datetime.now(),
            )
            channel.send(alert)

        with open(alert_file) as f:
            alerts = json.load(f)

        # Should keep only last 1000
        assert len(alerts) == 1000


class TestSMSAlertChannel:
    """Test SMSAlertChannel."""

    def test_disabled_channel(self):
        """Test disabled SMS channel."""
        config = {"enabled": False}
        channel = SMSAlertChannel(config)

        alert = Alert(
            alert_type=AlertType.DISK_FULL,
            severity=AlertSeverity.CRITICAL,
            message="Disk full",
            component="disk",
            timestamp=datetime.now(),
        )

        result = channel.send(alert)
        assert result is False

    def test_non_critical_alert(self):
        """Test non-critical alerts are not sent via SMS."""
        config = {"enabled": True, "admin_numbers": ["+1234567890"]}
        channel = SMSAlertChannel(config)

        alert = Alert(
            alert_type=AlertType.SYNC_FAILURE,
            severity=AlertSeverity.WARNING,  # Not critical
            message="Sync warning",
            component="sync",
            timestamp=datetime.now(),
        )

        result = channel.send(alert)
        assert result is False

    @patch("src.notifications.sms_notifier.SMSNotifier")
    def test_send_critical_alert(self, mock_notifier_class):
        """Test sending critical alert via SMS."""
        mock_notifier = MagicMock()
        mock_notifier.send_sms.return_value = True
        mock_notifier_class.return_value = mock_notifier

        config = {"enabled": True, "admin_numbers": ["+1234567890"]}
        channel = SMSAlertChannel(config)

        alert = Alert(
            alert_type=AlertType.CAMERA_FAILURE,
            severity=AlertSeverity.CRITICAL,
            message="Camera failed",
            component="camera",
            timestamp=datetime.now(),
        )

        result = channel.send(alert)
        assert result is True
        mock_notifier.send_sms.assert_called_once()


class TestWebhookAlertChannel:
    """Test WebhookAlertChannel."""

    def test_disabled_channel(self):
        """Test disabled webhook channel."""
        config = {"enabled": False}
        channel = WebhookAlertChannel(config)

        alert = Alert(
            alert_type=AlertType.DISK_FULL,
            severity=AlertSeverity.CRITICAL,
            message="Disk full",
            component="disk",
            timestamp=datetime.now(),
        )

        result = channel.send(alert)
        assert result is False

    @patch("requests.post")
    def test_send_alert(self, mock_post):
        """Test sending alert to webhook."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        config = {"enabled": True, "url": "https://example.com/webhook"}
        channel = WebhookAlertChannel(config)

        alert = Alert(
            alert_type=AlertType.CIRCUIT_BREAKER_OPEN,
            severity=AlertSeverity.ERROR,
            message="Circuit breaker opened",
            component="circuit_breaker",
            timestamp=datetime.now(),
        )

        result = channel.send(alert)
        assert result is True
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_send_with_auth(self, mock_post):
        """Test sending with authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        config = {
            "enabled": True,
            "url": "https://example.com/webhook",
            "auth_header": "Bearer token123",
        }
        channel = WebhookAlertChannel(config)

        alert = Alert(
            alert_type=AlertType.SYSTEM_ERROR,
            severity=AlertSeverity.ERROR,
            message="System error",
            component="system",
            timestamp=datetime.now(),
        )

        channel.send(alert)

        # Check auth header was included
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer token123"


class TestAlertManager:
    """Test AlertManager class."""

    def test_initialization(self):
        """Test manager initialization."""
        config = {"alerts": {"enabled": True}}
        manager = AlertManager(config)

        assert manager.enabled
        assert len(manager.channels) >= 2  # At least log and file channels

    def test_disabled_manager(self):
        """Test disabled manager."""
        config = {"alerts": {"enabled": False}}
        manager = AlertManager(config)

        assert not manager.enabled

    def test_send_alert(self, tmp_path):
        """Test sending alert."""
        config = {
            "alerts": {
                "enabled": True,
                "log_file": str(tmp_path / "alerts.log"),
                "alert_file": str(tmp_path / "alerts.json"),
            }
        }
        manager = AlertManager(config)

        result = manager.send_alert(
            AlertType.DISK_FULL,
            AlertSeverity.CRITICAL,
            "Disk full",
            "disk_monitor",
            {"usage": 95},
        )

        assert result is True
        assert len(manager.alert_history) == 1

    def test_alert_cooldown(self, tmp_path):
        """Test alert cooldown."""
        config = {
            "alerts": {
                "enabled": True,
                "cooldown_minutes": 5,
                "alert_file": str(tmp_path / "alerts.json"),
            }
        }
        manager = AlertManager(config)

        # Send first alert
        result1 = manager.send_alert(
            AlertType.SYNC_FAILURE,
            AlertSeverity.ERROR,
            "Sync failed",
            "cloud_sync",
        )
        assert result1 is True

        # Send same alert immediately (should be in cooldown)
        result2 = manager.send_alert(
            AlertType.SYNC_FAILURE,
            AlertSeverity.ERROR,
            "Sync failed again",
            "cloud_sync",
        )
        assert result2 is False

        # Only one alert should be in history
        assert len(manager.alert_history) == 1

    def test_convenience_methods(self, tmp_path):
        """Test convenience alert methods."""
        config = {
            "alerts": {"enabled": True, "alert_file": str(tmp_path / "alerts.json")}
        }
        manager = AlertManager(config)

        manager.alert_disk_full(95.0, "/data")
        manager.alert_circuit_breaker_open("students")
        manager.alert_sync_failure("timeout", 3)
        manager.alert_camera_failure("init failed")
        manager.alert_database_error("connection failed")
        manager.alert_network_offline()
        manager.alert_queue_overflow(1000, 500)

        assert len(manager.alert_history) == 7

    def test_get_recent_alerts(self, tmp_path):
        """Test getting recent alerts."""
        config = {
            "alerts": {
                "enabled": True,
                "alert_file": str(tmp_path / "alerts.json"),
                "cooldown_minutes": 0,  # Disable cooldown
            }
        }
        manager = AlertManager(config)

        # Send multiple alerts with different components to avoid cooldown
        for i in range(10):
            manager.send_alert(
                AlertType.SYSTEM_ERROR,
                AlertSeverity.INFO,
                f"Alert {i}",
                f"component_{i}",  # Different component for each alert
            )

        recent = manager.get_recent_alerts(limit=5)
        assert len(recent) == 5

    def test_alert_history_limit(self, tmp_path):
        """Test alert history size limit."""
        config = {
            "alerts": {
                "enabled": True,
                "alert_file": str(tmp_path / "alerts.json"),
                "cooldown_minutes": 0,  # Disable cooldown
            }
        }
        manager = AlertManager(config)

        # Send more than 100 alerts
        for i in range(150):
            # Use different components to avoid cooldown
            manager.send_alert(
                AlertType.SYSTEM_ERROR,
                AlertSeverity.INFO,
                f"Alert {i}",
                f"component_{i}",
            )

        # Should keep only last 100
        assert len(manager.alert_history) <= 100
