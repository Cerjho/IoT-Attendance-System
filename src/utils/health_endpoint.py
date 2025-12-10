#!/usr/bin/env python3
"""
Health Endpoint
HTTP status endpoint for monitoring system health
"""
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify

logger = logging.getLogger(__name__)


class HealthEndpoint:
    """
    HTTP health endpoint for system monitoring
    - System uptime and status
    - Camera health
    - Database connectivity
    - Queue size
    - SMS delivery stats
    - Memory and disk usage
    """

    def __init__(
        self,
        port: int = 8080,
        host: str = "0.0.0.0",
        enabled: bool = True,
        db_path: str = "data/attendance.db"
    ):
        """
        Initialize health endpoint
        
        Args:
            port: Port to listen on
            host: Host to bind to
            enabled: Enable/disable endpoint
            db_path: Path to database
        """
        self.port = port
        self.host = host
        self.enabled = enabled
        self.db_path = db_path
        
        self.app = Flask(__name__)
        self.running = False
        self.thread = None
        self.start_time = None
        
        # External component status (set by main system)
        self.camera_status = None
        self.watchdog_status = None
        self.backup_status = None
        self.sms_webhook_status = None
        
        # Configure Flask
        self.app.logger.setLevel(logging.WARNING)  # Suppress Flask debug logs
        
        # Register routes
        self._register_routes()
        
        if self.enabled:
            logger.info(f"Health endpoint initialized on port {port}")
        else:
            logger.info("Health endpoint disabled")

    def _register_routes(self):
        """Register Flask routes"""
        
        @self.app.route("/health", methods=["GET"])
        def health():
            """Main health check endpoint"""
            try:
                status = self._get_health_status()
                http_code = 200 if status["overall_status"] == "healthy" else 503
                return jsonify(status), http_code
            except Exception as e:
                logger.error(f"Health check error: {e}")
                return jsonify({
                    "overall_status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route("/health/system", methods=["GET"])
        def health_system():
            """System-level health"""
            try:
                return jsonify(self._get_system_health())
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/health/database", methods=["GET"])
        def health_database():
            """Database health"""
            try:
                return jsonify(self._get_database_health())
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/health/components", methods=["GET"])
        def health_components():
            """Component health"""
            try:
                return jsonify(self._get_component_health())
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route("/ping", methods=["GET"])
        def ping():
            """Simple ping endpoint"""
            return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

    def start(self):
        """Start health endpoint server"""
        if not self.enabled:
            logger.debug("Health endpoint disabled, not starting")
            return
        
        if self.running:
            logger.warning("Health endpoint already running")
            return
        
        self.running = True
        self.start_time = datetime.now()
        
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        
        logger.info(f"Health endpoint started on http://{self.host}:{self.port}/health")

    def stop(self):
        """Stop health endpoint server"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Health endpoint stopped")

    def _run_server(self):
        """Run Flask server in background thread"""
        try:
            # Disable Flask startup messages
            import sys
            import io
            sys.stderr = io.StringIO()
            
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
            
        except Exception as e:
            logger.error(f"Health endpoint server error: {e}")
            self.running = False

    def _get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        system = self._get_system_health()
        database = self._get_database_health()
        components = self._get_component_health()
        
        # Determine overall status
        all_healthy = all([
            system["status"] == "healthy",
            database["status"] == "healthy",
            components["camera"]["status"] == "healthy",
        ])
        
        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "system": system,
            "database": database,
            "components": components
        }

    def _get_system_health(self) -> Dict[str, Any]:
        """Get system-level health metrics"""
        try:
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            # Memory usage
            memory_mb = 0
            try:
                import psutil
                process = psutil.Process()
                memory_mb = round(process.memory_info().rss / 1024 / 1024, 2)
            except ImportError:
                pass  # psutil not available
            
            # Disk usage
            disk_usage = {}
            try:
                stat = os.statvfs("data/")
                total_gb = round((stat.f_blocks * stat.f_frsize) / 1024 / 1024 / 1024, 2)
                free_gb = round((stat.f_bfree * stat.f_frsize) / 1024 / 1024 / 1024, 2)
                used_gb = round(total_gb - free_gb, 2)
                used_percent = round((used_gb / total_gb) * 100, 1)
                
                disk_usage = {
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "used_percent": used_percent
                }
            except Exception as e:
                logger.debug(f"Could not get disk usage: {e}")
            
            return {
                "status": "healthy",
                "uptime_seconds": round(uptime_seconds),
                "uptime_hours": round(uptime_seconds / 3600, 1),
                "memory_mb": memory_mb,
                "disk_usage": disk_usage
            }
            
        except Exception as e:
            logger.error(f"System health check error: {e}")
            return {"status": "error", "error": str(e)}

    def _get_database_health(self) -> Dict[str, Any]:
        """Get database health metrics"""
        try:
            # Check database connectivity
            conn = sqlite3.connect(self.db_path, timeout=5)
            cursor = conn.cursor()
            
            # Queue size
            cursor.execute("SELECT COUNT(*) FROM sync_queue WHERE synced = 0")
            queue_size = cursor.fetchone()[0]
            
            # Total attendance records
            cursor.execute("SELECT COUNT(*) FROM attendance")
            total_records = cursor.fetchone()[0]
            
            # Today's scans
            cursor.execute("""
                SELECT COUNT(*) FROM attendance 
                WHERE date = date('now')
            """)
            today_scans = cursor.fetchone()[0]
            
            # Database size
            cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
            db_size_bytes = cursor.fetchone()[0]
            db_size_mb = round(db_size_bytes / 1024 / 1024, 2)
            
            conn.close()
            
            return {
                "status": "healthy",
                "connectivity": "ok",
                "queue_size": queue_size,
                "total_records": total_records,
                "today_scans": today_scans,
                "size_mb": db_size_mb
            }
            
        except Exception as e:
            logger.error(f"Database health check error: {e}")
            return {
                "status": "unhealthy",
                "connectivity": "failed",
                "error": str(e)
            }

    def _get_component_health(self) -> Dict[str, Any]:
        """Get component health status"""
        return {
            "camera": self.camera_status or {
                "status": "unknown",
                "message": "Camera status not available"
            },
            "watchdog": self.watchdog_status or {
                "status": "unknown",
                "message": "Watchdog status not available"
            },
            "backup": self.backup_status or {
                "status": "unknown",
                "message": "Backup status not available"
            },
            "sms_webhook": self.sms_webhook_status or {
                "status": "unknown",
                "message": "SMS webhook status not available"
            }
        }

    def update_camera_status(self, status: dict):
        """Update camera status from external component"""
        self.camera_status = {
            "status": "healthy" if status.get("healthy", False) else "unhealthy",
            "last_refresh": status.get("last_refresh"),
            "frames_captured": status.get("frames_captured", 0),
            "last_error": status.get("last_error")
        }

    def update_watchdog_status(self, status: dict):
        """Update watchdog status from external component"""
        self.watchdog_status = {
            "status": "healthy" if status.get("running", False) else "stopped",
            "last_heartbeat": status.get("last_heartbeat"),
            "total_restarts": status.get("total_restarts", 0)
        }

    def update_backup_status(self, status: dict):
        """Update backup status from external component"""
        self.backup_status = {
            "status": "healthy" if status.get("running", False) else "stopped",
            "total_backups": status.get("total_backups", 0),
            "latest_backup": status.get("latest_backup"),
            "database_integrity": status.get("database_integrity", "unknown")
        }

    def update_sms_webhook_status(self, status: dict):
        """Update SMS webhook status from external component"""
        self.sms_webhook_status = {
            "status": "healthy" if status.get("running", False) else "stopped",
            "total_received": status.get("total_received", 0),
            "delivered_count": status.get("delivered_count", 0),
            "failed_count": status.get("failed_count", 0)
        }
