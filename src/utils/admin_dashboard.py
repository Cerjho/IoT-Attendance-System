"""
Admin Dashboard API

REST API for monitoring system health, viewing recent scans,
checking queue status, and viewing configuration.
"""

import base64
import hashlib
import hmac
import ipaddress
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
    device_manager = None  # Multi-device manager

    def log_message(self, format, *args):
        """Override to use standard logger."""
        logger.debug(f"{self.address_string()} - {format % args}")

    def _is_ip_allowed(self, client_ip: str) -> bool:
        """Check if client IP is in allowed list (supports CIDR notation)."""
        if not self.allowed_ips:
            return True
        
        try:
            client = ipaddress.ip_address(client_ip)
            for allowed in self.allowed_ips:
                # Check if it's a CIDR range
                if '/' in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if client in network:
                        return True
                # Exact IP match
                elif client_ip == allowed:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking IP {client_ip}: {e}")
            return False

    def _check_authentication(self) -> bool:
        """Check if request is authenticated."""
        if not self.auth_enabled:
            return True
        
        # Check IP whitelist if configured
        client_ip = self.client_address[0]
        if self.allowed_ips and not self._is_ip_allowed(client_ip):
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, X-API-Key, Content-Type")
        self.send_header("Access-Control-Allow-Credentials", "true")
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
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.end_headers()
        self.wfile.write(text.encode())

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", self.headers.get('Origin', '*'))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, X-API-Key, Content-Type")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_POST(self):
        """Handle POST requests for device management."""
        # Check authentication first
        if not self._check_authentication():
            self._send_json_response({
                "error": "Unauthorized",
                "message": "Valid API key required"
            }, 401)
            return
        
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            data = json.loads(body) if body else {}

            if path == "/config":
                self._handle_config_update(data)
            elif path == "/devices/register":
                self._handle_device_register(data)
            elif path == "/devices/heartbeat":
                self._handle_device_heartbeat(data)
            elif path.startswith("/devices/") and path.endswith("/command"):
                device_id = path.split("/")[2]
                command = data.get('command')
                params = data.get('params', {})
                result = self.device_manager.send_command_to_device(device_id, command, params) if self.device_manager else {"error": "Multi-device not enabled"}
                self._send_json_response(result)
            else:
                self._send_json_response({"error": "Not found"}, 404)

        except json.JSONDecodeError:
            self._send_json_response({"error": "Invalid JSON"}, 400)
        except Exception as e:
            logger.error(f"Error handling POST: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_device_register(self, data: Dict):
        """Register a new device."""
        if not self.device_manager:
            self._send_json_response({"error": "Multi-device management not enabled"}, 503)
            return

        required_fields = ['device_id', 'device_name', 'ip_address']
        if not all(field in data for field in required_fields):
            self._send_json_response({
                "error": "Missing required fields",
                "required": required_fields
            }, 400)
            return

        try:
            success = self.device_manager.registry.register_device(
                device_id=data['device_id'],
                device_name=data['device_name'],
                ip_address=data['ip_address'],
                location=data.get('location'),
                building=data.get('building'),
                floor=data.get('floor'),
                room=data.get('room'),
                api_key=data.get('api_key'),
                config=data.get('config')
            )

            if success:
                self._send_json_response({
                    "success": True,
                    "message": f"Device {data['device_id']} registered successfully"
                })
            else:
                self._send_json_response({"error": "Registration failed"}, 500)

        except Exception as e:
            logger.error(f"Error registering device: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_device_heartbeat(self, data: Dict):
        """Handle device heartbeat report."""
        if not self.device_manager:
            self._send_json_response({"error": "Multi-device management not enabled"}, 503)
            return

        device_id = data.get('device_id')
        if not device_id:
            self._send_json_response({"error": "device_id required"}, 400)
            return

        try:
            metrics = data.get('metrics', {})
            self.device_manager.update_device_heartbeat_from_remote(device_id, metrics)

            self._send_json_response({
                "success": True,
                "message": "Heartbeat recorded"
            })

        except Exception as e:
            logger.error(f"Error recording heartbeat: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)
        
        # Serve dashboard HTML without authentication
        if path == "/" or path == "/index.html":
            try:
                dashboard_path = Path("public/multi-device-dashboard.html")
                if dashboard_path.exists():
                    with open(dashboard_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content.encode('utf-8'))))
                    self.end_headers()
                    self.wfile.write(content.encode('utf-8'))
                else:
                    self._send_json_response({"error": "Dashboard HTML not found"}, 404)
                return
            except Exception as e:
                logger.error(f"Error serving dashboard HTML: {e}")
                self._send_json_response({"error": "Failed to load dashboard"}, 500)
                return
        
        # Check authentication for API endpoints
        if not self._check_authentication():
            self._send_json_response({
                "error": "Unauthorized",
                "message": "Valid API key required. Use Authorization: Bearer <key> or X-API-Key: <key> header"
            }, 401)
            return

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
            elif path == "/api/verify-url":
                self._handle_verify_url(query_params)
            # Multi-device endpoints
            elif path == "/devices":
                self._handle_devices_list()
            elif path == "/devices/discover":
                network = query_params.get("network", ["192.168.1.0/24"])[0]
                self._handle_devices_discover(network)
            elif path == "/devices/status":
                self._handle_devices_status()
            elif path == "/devices/metrics":
                self._handle_devices_metrics()
            elif path.startswith("/devices/") and "/status" in path:
                device_id = path.split("/")[2]
                self._handle_device_status(device_id)
            elif path.startswith("/devices/") and "/command/" in path:
                parts = path.split("/")
                device_id = parts[2]
                command = parts[4] if len(parts) > 4 else None
                self._handle_device_command(device_id, command)
            elif path == "/locations":
                self._handle_device_locations()
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
        
        # Add real-time database metrics
        if self.db_path and Path(self.db_path).exists():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Count today's scans
                cursor.execute("""
                    SELECT COUNT(*) FROM attendance 
                    WHERE date(timestamp) = date('now')
                """)
                today_scans = cursor.fetchone()[0]
                
                # Count pending queue
                cursor.execute("SELECT COUNT(*) FROM sync_queue")
                queue_count = cursor.fetchone()[0]
                
                conn.close()
                
                # Add to metrics
                metrics['total_scans_today'] = today_scans
                metrics['queue_count'] = queue_count
                
            except Exception as e:
                logger.error(f"Error getting DB metrics: {e}")
                metrics['total_scans_today'] = 0
                metrics['queue_count'] = 0
        
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

    def _handle_config_update(self, new_config: Dict):
        """Update configuration file (non-sensitive fields only)."""
        import os
        import shutil
        from pathlib import Path
        from src.utils.config_loader import ConfigLoader
        
        try:
            # Validate no sensitive fields in update
            blocked_fields = []
            sensitive_paths = {
                'cloud.url', 'cloud.api_key',
                'sms_notifications.username', 'sms_notifications.password',
                'sms_notifications.device_id', 'sms_notifications.api_url'
            }
            
            # Check if any sensitive fields are being modified
            for path in self._get_update_paths(new_config):
                if path in sensitive_paths:
                    # Check if value is not a placeholder
                    value = self._get_nested_value(new_config, path)
                    if value and not (isinstance(value, str) and value.startswith('${') and value.endswith('}')):
                        blocked_fields.append(path)
            
            if blocked_fields:
                self._send_json_response({
                    "error": "Cannot update sensitive fields via dashboard",
                    "blocked_fields": blocked_fields,
                    "message": "Sensitive credentials must be set via environment variables (.env file)"
                }, 403)
                return
            
            config_path = Path("config/config.json")
            
            # Backup existing config
            backup_path = Path(f"config/config.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            if config_path.exists():
                shutil.copy2(config_path, backup_path)
                logger.info(f"Config backed up to {backup_path}")
            
            # Load current config and merge updates
            config_loader = ConfigLoader(str(config_path))
            current = config_loader.get_all()
            
            # Deep merge new config into current
            merged = config_loader._deep_merge(current, new_config)
            
            # Export with placeholders for sensitive fields (never commit secrets)
            config_loader.config = merged
            safe_export = config_loader.export_for_commit()
            
            # Write safe config (with placeholders)
            with open(config_path, 'w') as f:
                json.dump(safe_export, f, indent=2)
            
            logger.info("Configuration updated successfully")
            
            # Send response FIRST, then do async restart and git operations
            self._send_json_response({
                "success": True,
                "message": "Configuration saved successfully. Service will restart automatically.",
                "backup": str(backup_path),
                "auto_restart": "pending",
                "git_commit": "pending"
            })
            
            # Auto-restart service and commit changes (async, after response sent)
            import subprocess
            import threading
            
            def async_post_save():
                restart_success = False
                git_success = False
                
                try:
                    # Restart the dashboard service
                    result = subprocess.run(
                        ['sudo', 'systemctl', 'restart', 'attendance-dashboard.service'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    restart_success = (result.returncode == 0)
                    if restart_success:
                        logger.info("Service restarted successfully")
                    else:
                        logger.warning(f"Service restart failed: {result.stderr}")
                except Exception as e:
                    logger.error(f"Failed to restart service: {e}")
            
                try:
                    # Git commit and push
                    subprocess.run(['git', 'add', 'config/config.json'], 
                                  cwd='/home/iot/attendance-system', check=True, timeout=5)
                    
                    commit_msg = f"config: Update configuration via dashboard\n\nBackup: {backup_path.name}\nTimestamp: {datetime.now().isoformat()}"
                    subprocess.run(['git', 'commit', '-m', commit_msg],
                                  cwd='/home/iot/attendance-system', check=True, timeout=10)
                    
                    subprocess.run(['git', 'push', 'origin', 'main'],
                                  cwd='/home/iot/attendance-system', check=True, timeout=30)
                    
                    git_success = True
                    logger.info("Configuration committed and pushed to Git")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Git operations failed: {e}")
                except Exception as e:
                    logger.error(f"Failed to commit/push config: {e}")
                
                logger.info(f"Post-save operations completed: restart={restart_success}, git={git_success}")
            
            # Run async operations in background thread
            thread = threading.Thread(target=async_post_save, daemon=True)
            thread.start()
            return  # Response already sent above
            
        except Exception as e:
            logger.error(f"Failed to update config: {e}", exc_info=True)
            self._send_json_response({
                "error": "Failed to save configuration",
                "details": str(e)
            }, 500)

    def _handle_system_info(self):
        """System information endpoint."""
        import platform
        import sys

        device_id = self.config.get('device_id', 'unknown') if hasattr(self.config, 'get') else 'unknown'

        info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "device_id": device_id,
            "timestamp": datetime.now().isoformat(),
        }

        self._send_json_response(info)

    # Multi-Device Management Endpoints

    def _handle_devices_list(self):
        """List all registered devices."""
        if not self.device_manager:
            self._send_json_response({"error": "Multi-device management not enabled"}, 503)
            return

        try:
            from urllib.parse import parse_qs
            query = parse_qs(urlparse(self.path).query)
            
            status = query.get('status', [None])[0]
            building = query.get('building', [None])[0]
            floor = query.get('floor', [None])[0]

            devices = self.device_manager.registry.get_all_devices(
                status=status,
                building=building,
                floor=floor
            )

            self._send_json_response({
                "devices": devices,
                "count": len(devices),
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error listing devices: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_devices_discover(self, network: str):
        """Discover devices on network."""
        if not self.device_manager:
            self._send_json_response({"error": "Multi-device management not enabled"}, 503)
            return

        try:
            logger.info(f"Starting device discovery on {network}")
            
            discovered = self.device_manager.discover_devices(network)
            
            # Auto-register discovered devices
            registered = self.device_manager.register_discovered_devices(discovered)

            self._send_json_response({
                "discovered": len(discovered),
                "registered": registered,
                "devices": discovered,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error discovering devices: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_devices_status(self):
        """Get status of all devices."""
        if not self.device_manager:
            self._send_json_response({"error": "Multi-device management not enabled"}, 503)
            return

        try:
            devices_status = self.device_manager.get_all_devices_status()
            status_summary = self.device_manager.registry.get_device_status_summary()

            self._send_json_response({
                "summary": status_summary,
                "devices": devices_status,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error getting devices status: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_devices_metrics(self):
        """Get aggregated metrics from all devices."""
        if not self.device_manager:
            self._send_json_response({"error": "Multi-device management not enabled"}, 503)
            return

        try:
            metrics = self.device_manager.get_aggregated_metrics()
            self._send_json_response(metrics)

        except Exception as e:
            logger.error(f"Error getting aggregated metrics: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_device_status(self, device_id: str):
        """Get status of a specific device."""
        if not self.device_manager:
            self._send_json_response({"error": "Multi-device management not enabled"}, 503)
            return

        try:
            device = self.device_manager.registry.get_device(device_id)
            if not device:
                self._send_json_response({"error": "Device not found"}, 404)
                return

            # Get current status from device
            status_result = self.device_manager.send_command_to_device(device_id, 'status')

            self._send_json_response({
                "device": device,
                "current_status": status_result.get('data') if status_result.get('success') else None,
                "online": status_result.get('success', False),
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error getting device status: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_device_command(self, device_id: str, command: str):
        """Send command to a specific device."""
        if not self.device_manager:
            self._send_json_response({"error": "Multi-device management not enabled"}, 503)
            return

        if not command:
            self._send_json_response({"error": "Command required"}, 400)
            return

        try:
            result = self.device_manager.send_command_to_device(device_id, command)
            self._send_json_response(result)

        except Exception as e:
            logger.error(f"Error sending command to device: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

    def _handle_device_locations(self):
        """Get device location hierarchy."""
        if not self.device_manager:
            self._send_json_response({"error": "Multi-device management not enabled"}, 503)
            return

        try:
            locations = self.device_manager.registry.get_device_locations()
            self._send_json_response({
                "locations": locations,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error getting device locations: {e}", exc_info=True)
            self._send_json_response({"error": str(e)}, 500)

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

    def _get_update_paths(self, obj: dict, prefix='') -> list:
        """Recursively get all field paths in dict.
        
        Args:
            obj: Dictionary to traverse
            prefix: Current path prefix
            
        Returns:
            List of dot-notation paths
        """
        paths = []
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.append(path)
            if isinstance(value, dict):
                paths.extend(self._get_update_paths(value, path))
        return paths

    def _get_nested_value(self, obj: dict, path: str):
        """Get nested value using dot-notation path.
        
        Args:
            obj: Dictionary to query
            path: Dot-notation path (e.g., 'cloud.api_key')
            
        Returns:
            Value at path or None
        """
        keys = path.split('.')
        current = obj
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def _handle_verify_url(self, query_params: Dict):
        """
        Verify signed URL and return student UUID if valid.
        
        Query parameters:
            student_id: Student number
            expires: Unix timestamp
            sig: HMAC signature
        
        Returns:
            200 with student UUID if valid
            403 if invalid or expired
        """
        try:
            # Extract parameters
            student_id = query_params.get('student_id', [None])[0]
            expires = query_params.get('expires', [None])[0]
            sig = query_params.get('sig', [None])[0]
            
            if not all([student_id, expires, sig]):
                self._send_json_response({
                    "valid": False,
                    "error": "Missing required parameters (student_id, expires, sig)"
                }, 400)
                return
            
            # Import URLSigner
            from src.auth.url_signer import URLSigner
            
            # Get signing secret from config or env
            secret = os.environ.get('URL_SIGNING_SECRET')
            if not secret:
                # Fallback to config if env not set
                secret = self.config.get('url_signing', {}).get('secret')
            
            if not secret:
                logger.error("URL_SIGNING_SECRET not configured")
                self._send_json_response({
                    "valid": False,
                    "error": "URL signing not configured"
                }, 500)
                return
            
            # Create signer and verify
            signer = URLSigner(secret)
            
            # Reconstruct URL for verification
            base_url = "https://dummy.com"  # URL doesn't matter, only params
            verify_url = f"{base_url}?student_id={student_id}&expires={expires}&sig={sig}"
            
            is_valid, verified_student_id, error = signer.verify_url(verify_url)
            
            if not is_valid:
                logger.warning(f"Invalid signed URL for student {student_id}: {error}")
                self._send_json_response({
                    "valid": False,
                    "error": error or "Invalid signature"
                }, 403)
                return
            
            # Look up student UUID from student_number
            # Query local database or Supabase
            student_uuid = self._get_student_uuid(verified_student_id)
            
            if not student_uuid:
                self._send_json_response({
                    "valid": False,
                    "error": "Student not found"
                }, 404)
                return
            
            # Valid - return success
            self._send_json_response({
                "valid": True,
                "student_id": verified_student_id,
                "student_uuid": student_uuid,
                "expires_at": datetime.fromtimestamp(int(expires)).isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error verifying URL: {e}", exc_info=True)
            self._send_json_response({
                "valid": False,
                "error": "Verification failed"
            }, 500)
    
    def _get_student_uuid(self, student_number: str) -> Optional[str]:
        """
        Get student UUID from student number.
        
        Args:
            student_number: Student number (e.g., "2021001")
        
        Returns:
            Student UUID or None if not found
        """
        try:
            # Try local database first
            if self.db_path and Path(self.db_path).exists():
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT student_id FROM students WHERE student_id = ?",
                    (student_number,)
                )
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    return result[0]
            
            # If not found locally, try Supabase
            # Note: In production, you'd want to cache this
            from src.cloud.cloud_sync import CloudSyncManager
            
            # This is a simplified lookup - in production you'd inject the cloud manager
            # For now, return None and let the frontend handle the Supabase lookup
            logger.warning(f"Student {student_number} not found in local cache")
            return None
            
        except Exception as e:
            logger.error(f"Error looking up student UUID: {e}")
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
        enable_multi_device: bool = False,
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
            enable_multi_device: Enable multi-device management
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

        # Multi-device management
        self.device_manager = None
        if enable_multi_device or dashboard_config.get("multi_device_enabled", False):
            try:
                from ..database.device_registry import DeviceRegistry
                from .multi_device_manager import MultiDeviceManager
                
                registry = DeviceRegistry()
                self.device_manager = MultiDeviceManager(config, registry)
                self.device_manager.start()
                logger.info("Multi-device management ENABLED")
            except Exception as e:
                logger.error(f"Failed to enable multi-device management: {e}")

        # Set class variables for handler
        AdminAPIHandler.config = config
        AdminAPIHandler.metrics_collector = metrics_collector
        AdminAPIHandler.shutdown_manager = shutdown_manager
        AdminAPIHandler.db_path = db_path
        AdminAPIHandler.auth_enabled = self.auth_enabled
        AdminAPIHandler.api_key = self.api_key
        AdminAPIHandler.allowed_ips = self.allowed_ips
        AdminAPIHandler.device_manager = self.device_manager

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

        # Stop multi-device manager
        if self.device_manager:
            self.device_manager.stop()

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.server_thread is not None and self.server_thread.is_alive()
