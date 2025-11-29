"""
Tests for Admin Dashboard API

Tests REST endpoints, health checks, status reporting, and metrics export.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.utils.admin_dashboard import AdminDashboard, AdminAPIHandler
from src.utils.metrics import MetricsCollector


@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "test.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute(
        """
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY,
            student_number TEXT,
            timestamp TEXT,
            scan_type TEXT,
            status TEXT,
            photo_path TEXT,
            synced INTEGER DEFAULT 0,
            sync_timestamp TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE sync_queue (
            id INTEGER PRIMARY KEY,
            record_type TEXT,
            record_id INTEGER,
            data TEXT,
            priority INTEGER DEFAULT 0,
            retry_count INTEGER DEFAULT 0,
            created_at TEXT,
            last_attempt TEXT
        )
    """
    )

    # Insert test data
    cursor.execute(
        """
        INSERT INTO attendance (student_number, timestamp, scan_type, status)
        VALUES ('2021001', '2025-11-29 08:00:00', 'LOGIN', 'present')
    """
    )

    cursor.execute(
        """
        INSERT INTO sync_queue (record_type, record_id, data, priority, retry_count, created_at)
        VALUES ('attendance', 1, '{}', 0, 0, '2025-11-29 08:00:00')
    """
    )

    conn.commit()
    conn.close()

    return str(db_path)


@pytest.fixture
def config():
    """Test configuration."""
    return {
        "offline_mode": {},
        "cloud": {"device_id": "test-device"},
    }


@pytest.fixture
def metrics_collector():
    """Test metrics collector."""
    return MetricsCollector({"enabled": True})


class TestAdminAPIHandler:
    """Test AdminAPIHandler class."""

    def test_sanitize_config(self):
        """Test configuration sanitization."""
        from src.utils.admin_dashboard import AdminDashboard

        # Use the static method via AdminDashboard
        config = {
            "api_key": "secret123",
            "supabase": {"url": "https://test.com", "api_key": "key123"},
            "safe_value": "visible",
        }

        # Create dummy handler instance to access method
        AdminAPIHandler.config = config
        handler_instance = type('obj', (object,), {'_sanitize_config': AdminAPIHandler._sanitize_config, 'config': config})()
        sanitized = handler_instance._sanitize_config(config)

        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["supabase"]["api_key"] == "***REDACTED***"
        assert sanitized["safe_value"] == "visible"


class TestAdminDashboard:
    """Test AdminDashboard class."""

    def test_initialization(self, config, metrics_collector, test_db):
        """Test dashboard initialization."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            port=18080,  # Use different port
        )

        assert dashboard.config == config
        assert dashboard.metrics_collector == metrics_collector
        assert dashboard.port == 18080

    def test_start_stop(self, config, metrics_collector, test_db):
        """Test starting and stopping dashboard."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18081,
        )

        try:
            dashboard.start()
            time.sleep(0.5)  # Allow server to start

            assert dashboard.is_running()

            dashboard.stop()
            time.sleep(0.5)  # Allow server to stop

            assert not dashboard.is_running()

        except Exception as e:
            if dashboard.is_running():
                dashboard.stop()
            raise e

    def test_health_endpoint(self, config, metrics_collector, test_db):
        """Test /health endpoint."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18082,
        )

        try:
            dashboard.start()
            time.sleep(0.5)

            response = requests.get("http://127.0.0.1:18082/health", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] in ["healthy", "shutting_down"]
            assert "timestamp" in data

        finally:
            dashboard.stop()

    def test_status_endpoint(self, config, metrics_collector, test_db):
        """Test /status endpoint."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18083,
        )

        try:
            dashboard.start()
            time.sleep(0.5)

            response = requests.get("http://127.0.0.1:18083/status", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert "online" in data
            assert "disk" in data
            assert "queue_size" in data
            assert "timestamp" in data

        finally:
            dashboard.stop()

    def test_metrics_endpoint(self, config, metrics_collector, test_db):
        """Test /metrics endpoint (JSON)."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18084,
        )

        try:
            dashboard.start()
            time.sleep(0.5)

            # Record some metrics
            metrics_collector.record_scan(True, "LOGIN", 1.0, {})

            response = requests.get("http://127.0.0.1:18084/metrics", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert isinstance(data, dict)
            assert len(data) > 0

        finally:
            dashboard.stop()

    def test_prometheus_metrics_endpoint(self, config, metrics_collector, test_db):
        """Test /metrics/prometheus endpoint."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18085,
        )

        try:
            dashboard.start()
            time.sleep(0.5)

            response = requests.get(
                "http://127.0.0.1:18085/metrics/prometheus", timeout=5
            )
            assert response.status_code == 200
            assert "text/plain" in response.headers["Content-Type"]

            text = response.text
            assert "# HELP" in text
            assert "# TYPE" in text

        finally:
            dashboard.stop()

    def test_recent_scans_endpoint(self, config, metrics_collector, test_db):
        """Test /scans/recent endpoint."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18086,
        )

        try:
            dashboard.start()
            time.sleep(0.5)

            response = requests.get(
                "http://127.0.0.1:18086/scans/recent?limit=10", timeout=5
            )
            assert response.status_code == 200

            data = response.json()
            assert "scans" in data
            assert "count" in data
            assert isinstance(data["scans"], list)

        finally:
            dashboard.stop()

    def test_queue_status_endpoint(self, config, metrics_collector, test_db):
        """Test /queue/status endpoint."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18087,
        )

        try:
            dashboard.start()
            time.sleep(0.5)

            response = requests.get("http://127.0.0.1:18087/queue/status", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert "total" in data
            assert "summary" in data
            assert isinstance(data["total"], int)

        finally:
            dashboard.stop()

    def test_config_endpoint(self, config, metrics_collector, test_db):
        """Test /config endpoint."""
        config_with_secrets = config.copy()
        config_with_secrets["api_key"] = "secret123"

        dashboard = AdminDashboard(
            config=config_with_secrets,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18088,
        )

        try:
            dashboard.start()
            time.sleep(0.5)

            response = requests.get("http://127.0.0.1:18088/config", timeout=5)
            assert response.status_code == 200

            data = response.json()
            # Secrets should be redacted
            assert data.get("api_key") == "***REDACTED***"

        finally:
            dashboard.stop()

    def test_system_info_endpoint(self, config, metrics_collector, test_db):
        """Test /system/info endpoint."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18089,
        )

        try:
            dashboard.start()
            time.sleep(0.5)

            response = requests.get("http://127.0.0.1:18089/system/info", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert "python_version" in data
            assert "platform" in data
            assert "hostname" in data

        finally:
            dashboard.stop()

    def test_not_found_endpoint(self, config, metrics_collector, test_db):
        """Test 404 for unknown endpoint."""
        dashboard = AdminDashboard(
            config=config,
            metrics_collector=metrics_collector,
            db_path=test_db,
            host="127.0.0.1",
            port=18090,
        )

        try:
            dashboard.start()
            time.sleep(0.5)

            response = requests.get("http://127.0.0.1:18090/unknown", timeout=5)
            assert response.status_code == 404

        finally:
            dashboard.stop()
