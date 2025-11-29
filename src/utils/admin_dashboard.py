"""
Admin Dashboard API

REST API for monitoring system health, viewing recent scans,
checking queue status, and viewing configuration.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


class AdminAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for admin API."""

    # Class variables set by AdminDashboard
    config = None
    metrics_collector = None
    shutdown_manager = None
    db_path = None
    auth_enabled = False
    api_key = None
    allowed_ips = []

    def log_message(self, format, *args):
        """Override to use standard logger."""
        logger.debug(f"{self.address_string()} - {format % args}")

    def _check_authentication(self) -> bool:
        """Check if request is authenticated."""
        if not self.auth_enabled:
            return True
        
        # Check IP whitelist if configured
        client_ip = self.client_address[0]
        if self.allowed_ips and client_ip not in self.allowed_ips:
            logger.warning(f"Rejected request from unauthorized IP: {client_ip}")
            return False
        
        # Check API key
        auth_header = self.headers.get('Authorization', '')
        api_key_header = self.headers.get('X-API-Key', '')
        
        # Support both Bearer token and X-API-Key header
        provided_key = None
        if auth_header.startswith('Bearer '):
            provided_key = auth_header[7:]
        elif api_key_header:
            provided_key = api_key_header
        
        if not provided_key:
            logger.warning(f"Missing authentication from {client_ip}")
            return False
        
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided_key, self.api_key):
            logger.warning(f"Invalid API key from {client_ip}")
            return False
        
        return True

    def _send_json_response(self, data: dict, status_code: int = 200):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        # Security headers
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        # CORS - restrict in production
        allowed_origin = self.headers.get('Origin', '*')
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, X-API-Key")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def _send_text_response(self, text: str, status_code: int = 200, content_type: str = "text/plain"):
        """Send text response."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        # Security headers
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        allowed_origin = self.headers.get('Origin', '*')
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.end_headers()
        self.wfile.write(text.encode())

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", self.headers.get('Origin', '*'))
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, X-API-Key, Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        # Check authentication first
        if not self._check_authentication():
            self._send_json_response({
                "error": "Unauthorized",
                "message": "Valid API key required. Use Authorization: Bearer <key> or X-API-Key: <key> header"
            }, 401)
            return
        
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)

        try:
            if path == "/health":
                self._handle_health()
            elif path == "/status":
                self._handle_status()
            elif path == "/metrics":
                self._handle_metrics()
            elif path == "/metrics/prometheus":
                self._handle_prometheus_metrics()
            elif path == "/scans/recent":
                limit = int(query_params.get("limit", [100])[0])
                self._handle_recent_scans(limit)
            elif path == "/queue/status":
                self._handle_queue_status()
            elif path == "/config":
                self._handle_config()
            elif path == "/system/info":
                self._handle_system_info()
            else:
                self._send_json_response({"error": "Not found"}, 404)

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            self._send_json_response(
                {"error": "Internal server error", "details": str(e)}, 500
            )

    def _handle_health(self):
        """Health check endpoint."""
        is_shutting_down = (
            self.shutdown_manager.is_shutting_down()
            if self.shutdown_manager
            else False
        )

        health = {
            "status": "shutting_down" if is_shutting_down else "healthy",
            "timestamp": datetime.now().isoformat(),
        }

        status_code = 503 if is_shutting_down else 200
        self._send_json_response(health, status_code)

    def _handle_status(self):
        """System status endpoint."""
        from src.network.connectivity import ConnectivityMonitor

        # Get connectivity status
        connectivity = ConnectivityMonitor(self.config.get("offline_mode", {}))
        is_online = connectivity.is_online()

        # Get disk usage
        data_path = Path("data")
        if data_path.exists():
            import shutil

            usage = shutil.disk_usage(data_path)
            disk_info = {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "percent_used": round(usage.used / usage.total * 100, 2),
            }
        else:
            disk_info = {"error": "data path not found"}

        # Get queue size
        queue_size = self._get_queue_size()

        # Get uptime (if state file exists)
        uptime_seconds = self._get_uptime()

        status = {
            "online": is_online,
            "disk": disk_info,
            "queue_size": queue_size,
            "uptime_seconds": uptime_seconds,
            "timestamp": datetime.now().isoformat(),
        }

        self._send_json_response(status)

    def _handle_metrics(self):
        """Metrics endpoint (JSON format)."""
        if not self.metrics_collector:
            self._send_json_response({"error": "Metrics not enabled"}, 503)
            return

        metrics = self.metrics_collector.get_metrics_dict()
        self._send_json_response(metrics)

    def _handle_prometheus_metrics(self):
        """Prometheus metrics endpoint (text format)."""
        if not self.metrics_collector:
            self._send_text_response("# Metrics not enabled\n", 503)
            return

        metrics_text = self.metrics_collector.export_prometheus()
        self._send_text_response(metrics_text, content_type="text/plain; version=0.0.4")

    def _handle_recent_scans(self, limit: int = 100):
        """Recent scans endpoint."""
        if not self.db_path or not Path(self.db_path).exists():
            self._send_json_response({"error": "Database not found"}, 503)
            return

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    id, student_id, timestamp, scan_type, status,
                    photo_path, synced, sync_timestamp, cloud_record_id
                FROM attendance
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )

            scans = [dict(row) for row in cursor.fetchall()]
            conn.close()

            self._send_json_response({"scans": scans, "count": len(scans)})

        except Exception as e:
            logger.error(f"Error fetching recent scans: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_queue_status(self):
        """Queue status endpoint."""
        if not self.db_path or not Path(self.db_path).exists():
            self._send_json_response({"error": "Database not found"}, 503)
            return

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get queue summary
            cursor.execute(
                """
                SELECT 
                    record_type,
                    priority,
                    COUNT(*) as count,
                    AVG(retry_count) as avg_retries,
                    MAX(retry_count) as max_retries
                FROM sync_queue
                GROUP BY record_type, priority
            """
            )

            summary = [dict(row) for row in cursor.fetchall()]

            # Get oldest pending record
            cursor.execute(
                """
                SELECT created_at, retry_count
                FROM sync_queue
                ORDER BY created_at ASC
                LIMIT 1
            """
            )

            oldest = cursor.fetchone()
            oldest_dict = dict(oldest) if oldest else None

            # Get total count
            cursor.execute("SELECT COUNT(*) as total FROM sync_queue")
            total = cursor.fetchone()["total"]

            conn.close()

            self._send_json_response(
                {"total": total, "summary": summary, "oldest": oldest_dict}
            )

        except Exception as e:
            logger.error(f"Error fetching queue status: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_config(self):
        """Configuration endpoint (sanitized)."""
        if not self.config:
            self._send_json_response({"error": "Config not available"}, 503)
            return

        # Convert ConfigLoader to dict if needed
        if hasattr(self.config, 'get_all'):
            config_dict = self.config.get_all()
        elif isinstance(self.config, dict):
            config_dict = self.config
        else:
            config_dict = dict(self.config)
        
        # Sanitize sensitive data
        safe_config = self._sanitize_config(config_dict)
        self._send_json_response(safe_config)

    def _handle_system_info(self):
        """System information endpoint."""
        import platform
        import sys

        info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "timestamp": datetime.now().isoformat(),
        }

        self._send_json_response(info)

    def _get_queue_size(self) -> int:
        """Get sync queue size."""
        if not self.db_path or not Path(self.db_path).exists():
            return -1

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sync_queue")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return -1

    def _get_uptime(self) -> Optional[float]:
        """Get system uptime in seconds."""
        state_file = Path("data/system_state.json")
        if not state_file.exists():
            return None

        try:
            with open(state_file) as f:
                state = json.load(f)
            start_time = datetime.fromisoformat(state.get("startup_time", ""))
            uptime = (datetime.now() - start_time).total_seconds()
            return uptime
        except Exception:
            return None

    def _sanitize_config(self, config: dict) -> dict:
        """Remove sensitive data from config."""
        import copy

        safe = copy.deepcopy(config)

        # Remove sensitive keys
        sensitive_keys = [
            "api_key",
            "apikey",
            "password",
            "secret",
            "token",
            "auth_token",
            "credentials",
        ]

        def remove_sensitive(obj):
            if isinstance(obj, dict):
                for key in list(obj.keys()):
                    if any(s in key.lower() for s in sensitive_keys):
                        obj[key] = "***REDACTED***"
                    else:
                        remove_sensitive(obj[key])
            elif isinstance(obj, list):
                for item in obj:
                    remove_sensitive(item)

        remove_sensitive(safe)
        return safe


class AdminDashboard:
    """
    Admin dashboard for system monitoring.

    Provides REST API for:
    - Health checks
    - System status
    - Recent scans
    - Queue status
    - Configuration viewing
    - Metrics export (JSON and Prometheus)
    """

    def __init__(
        self,
        config: dict,
        metrics_collector=None,
        shutdown_manager=None,
        db_path: str = "data/attendance.db",
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        """
        Initialize admin dashboard.

        Args:
            config: System configuration
            metrics_collector: Optional MetricsCollector instance
            shutdown_manager: Optional ShutdownManager instance
            db_path: Path to database
            host: Server host
            port: Server port
        """
        self.config = config
        self.metrics_collector = metrics_collector
        self.shutdown_manager = shutdown_manager
        self.db_path = db_path
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[Thread] = None

        # Get dashboard config
        dashboard_config = config.get("admin_dashboard", {}) if hasattr(config, 'get') else config.get("admin_dashboard", {})
        
        # Authentication setup
        self.auth_enabled = dashboard_config.get("auth_enabled", False)
        self.api_key = os.getenv("DASHBOARD_API_KEY") or dashboard_config.get("api_key")
        
        # Generate API key if auth enabled but no key provided
        if self.auth_enabled and not self.api_key:
            self.api_key = secrets.token_urlsafe(32)
            logger.warning(f"Generated API key: {self.api_key}")
            logger.warning("Save this key securely! Set DASHBOARD_API_KEY in .env")
        
        # IP whitelist
        self.allowed_ips = dashboard_config.get("allowed_ips", [])
        if self.allowed_ips:
            logger.info(f"IP whitelist enabled: {len(self.allowed_ips)} IPs allowed")

        # Set class variables for handler
        AdminAPIHandler.config = config
        AdminAPIHandler.metrics_collector = metrics_collector
        AdminAPIHandler.shutdown_manager = shutdown_manager
        AdminAPIHandler.db_path = db_path
        AdminAPIHandler.auth_enabled = self.auth_enabled
        AdminAPIHandler.api_key = self.api_key
        AdminAPIHandler.allowed_ips = self.allowed_ips

        if self.auth_enabled:
            logger.info(f"Admin dashboard initialized on {host}:{port} (AUTH ENABLED)")
        else:
            logger.warning(f"Admin dashboard initialized on {host}:{port} (NO AUTH - NOT SECURE FOR REMOTE ACCESS)")
            logger.warning("Enable auth_enabled in config for remote access security")

    def start(self):
        """Start the dashboard server."""
        try:
            self.server = HTTPServer((self.host, self.port), AdminAPIHandler)
            self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()

            logger.info(f"Admin dashboard started at http://{self.host}:{self.port}")
            logger.info(f"Endpoints: /health, /status, /metrics, /scans/recent, /queue/status, /config")

        except Exception as e:
            logger.error(f"Error starting admin dashboard: {e}", exc_info=True)
            raise

    def stop(self):
        """Stop the dashboard server."""
        if self.server:
            logger.info("Stopping admin dashboard")
            self.server.shutdown()
            self.server.server_close()

            if self.server_thread:
                self.server_thread.join(timeout=5)

            logger.info("Admin dashboard stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.server_thread is not None and self.server_thread.is_alive()
