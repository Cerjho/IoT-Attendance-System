#!/usr/bin/env python3
"""
Real-time Monitoring System
Provides live system status, events, and metrics visualization
"""

import json
import logging
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RealtimeMonitor:
    """Real-time monitoring with event streaming and metrics tracking"""

    def __init__(self, db_path: str = "data/attendance.db", max_events: int = 100):
        """
        Initialize real-time monitor

        Args:
            db_path: Path to attendance database
            max_events: Maximum events to keep in memory
        """
        self.db_path = db_path
        self.max_events = max_events
        
        # Event streams
        self.events = deque(maxlen=max_events)
        self.alerts = deque(maxlen=50)
        
        # Metrics
        self.metrics = {
            "scans_today": 0,
            "scans_last_hour": 0,
            "success_rate": 100.0,
            "avg_process_time": 0.0,
            "queue_size": 0,
            "failed_syncs": 0,
            "uptime_seconds": 0,
        }
        
        # System state
        self.system_state = {
            "status": "initializing",
            "camera_status": "unknown",
            "cloud_status": "unknown",
            "sms_status": "unknown",
            "last_scan": None,
            "last_sync": None,
        }
        
        # Thread control
        self._running = False
        self._lock = threading.Lock()
        self._monitor_thread = None
        self._start_time = datetime.now()
        
        # Subscribers for real-time updates
        self._subscribers = []

    def start(self):
        """Start real-time monitoring"""
        if self._running:
            logger.warning("Monitor already running")
            return
        
        self._running = True
        self._start_time = datetime.now()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Real-time monitor started")

    def stop(self):
        """Stop real-time monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Real-time monitor stopped")

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                self._update_metrics()
                self._check_alerts()
                time.sleep(5)  # Update every 5 seconds
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(10)

    def _update_metrics(self):
        """Update system metrics"""
        try:
            with self._lock:
                # Update uptime
                self.metrics["uptime_seconds"] = int(
                    (datetime.now() - self._start_time).total_seconds()
                )
                
                # Get database metrics
                conn = sqlite3.connect(self.db_path, timeout=5)
                cursor = conn.cursor()
                
                # Scans today
                today = datetime.now().date().isoformat()
                cursor.execute(
                    "SELECT COUNT(*) FROM attendance WHERE date(timestamp) = ?",
                    (today,)
                )
                self.metrics["scans_today"] = cursor.fetchone()[0]
                
                # Scans last hour
                one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                cursor.execute(
                    "SELECT COUNT(*) FROM attendance WHERE timestamp >= ?",
                    (one_hour_ago,)
                )
                self.metrics["scans_last_hour"] = cursor.fetchone()[0]
                
                # Queue size
                cursor.execute("SELECT COUNT(*) FROM sync_queue")
                self.metrics["queue_size"] = cursor.fetchone()[0]
                
                # Failed syncs (retry count > 0)
                cursor.execute(
                    "SELECT COUNT(*) FROM sync_queue WHERE retry_count > 0"
                )
                self.metrics["failed_syncs"] = cursor.fetchone()[0]
                
                # Success rate (synced / total today)
                cursor.execute(
                    "SELECT COUNT(*) FROM attendance WHERE date(timestamp) = ? AND synced = 1",
                    (today,)
                )
                synced_count = cursor.fetchone()[0]
                
                if self.metrics["scans_today"] > 0:
                    self.metrics["success_rate"] = (
                        synced_count / self.metrics["scans_today"] * 100
                    )
                
                conn.close()
                
                # Notify subscribers
                self._notify_subscribers("metrics", self.metrics)
                
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")

    def _check_alerts(self):
        """Check for alert conditions"""
        try:
            with self._lock:
                # Check queue size
                if self.metrics["queue_size"] > 50:
                    self._add_alert(
                        "warning",
                        f"Queue size high: {self.metrics['queue_size']} records pending"
                    )
                
                # Check failed syncs
                if self.metrics["failed_syncs"] > 10:
                    self._add_alert(
                        "error",
                        f"Multiple sync failures: {self.metrics['failed_syncs']} records failing"
                    )
                
                # Check success rate
                if self.metrics["success_rate"] < 80 and self.metrics["scans_today"] > 10:
                    self._add_alert(
                        "warning",
                        f"Low success rate: {self.metrics['success_rate']:.1f}%"
                    )
                
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")

    def log_event(self, event_type: str, message: str, data: Dict = None):
        """
        Log a real-time event

        Args:
            event_type: Type of event (scan, sync, sms, error, etc.)
            message: Event message
            data: Additional event data
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "data": data or {}
        }
        
        with self._lock:
            self.events.append(event)
        
        # Notify subscribers
        self._notify_subscribers("event", event)
        
        # Log to file
        if event_type in ["error", "warning"]:
            logger.warning(f"[{event_type.upper()}] {message}")
        else:
            logger.info(f"[{event_type.upper()}] {message}")

    def _add_alert(self, level: str, message: str):
        """Add alert to alert stream"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message
        }
        
        # Check if similar alert already exists (within last 5 minutes)
        recent_alerts = [a for a in self.alerts if 
                        (datetime.now() - datetime.fromisoformat(a["timestamp"])).seconds < 300]
        
        if not any(a["message"] == message for a in recent_alerts):
            with self._lock:
                self.alerts.append(alert)
            
            self._notify_subscribers("alert", alert)

    def update_system_state(self, component: str, status: str, details: str = None):
        """
        Update system component status

        Args:
            component: Component name (camera, cloud, sms, etc.)
            status: Status (online, offline, error, etc.)
            details: Additional details
        """
        with self._lock:
            self.system_state[f"{component}_status"] = status
            if details:
                self.system_state[f"{component}_details"] = details
            
            # Update overall status
            statuses = [
                self.system_state.get("camera_status", "unknown"),
                self.system_state.get("cloud_status", "unknown"),
                self.system_state.get("sms_status", "unknown")
            ]
            
            if "error" in statuses:
                self.system_state["status"] = "error"
            elif "offline" in statuses:
                self.system_state["status"] = "degraded"
            elif all(s == "online" for s in statuses):
                self.system_state["status"] = "healthy"
            else:
                self.system_state["status"] = "partial"
        
        self._notify_subscribers("state", self.system_state)

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent events"""
        with self._lock:
            return list(self.events)[-limit:]

    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """Get recent alerts"""
        with self._lock:
            return list(self.alerts)[-limit:]

    def get_metrics(self) -> Dict:
        """Get current metrics"""
        with self._lock:
            return self.metrics.copy()

    def get_system_state(self) -> Dict:
        """Get system state"""
        with self._lock:
            return self.system_state.copy()

    def get_dashboard_data(self) -> Dict:
        """Get complete dashboard data"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.get_metrics(),
            "system_state": self.get_system_state(),
            "recent_events": self.get_recent_events(20),
            "recent_alerts": self.get_recent_alerts(10),
            "uptime": self._format_uptime(self.metrics["uptime_seconds"])
        }

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime as human-readable string"""
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def subscribe(self, callback):
        """
        Subscribe to real-time updates

        Args:
            callback: Function to call with (event_type, data)
        """
        self._subscribers.append(callback)

    def unsubscribe(self, callback):
        """Unsubscribe from real-time updates"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify_subscribers(self, event_type: str, data: Dict):
        """Notify all subscribers of an event"""
        for callback in self._subscribers[:]:  # Copy list to avoid modification during iteration
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Subscriber callback error: {e}")

    def export_metrics(self, filepath: str = None) -> str:
        """
        Export current metrics to JSON file

        Args:
            filepath: Output file path (default: data/metrics_export_TIMESTAMP.json)

        Returns:
            Path to exported file
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"data/metrics_export_{timestamp}.json"
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "metrics": self.get_metrics(),
            "system_state": self.get_system_state(),
            "recent_events": self.get_recent_events(100),
            "recent_alerts": self.get_recent_alerts(50)
        }
        
        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Metrics exported to {filepath}")
        return filepath


# Global monitor instance
_monitor_instance = None


def get_monitor(db_path: str = "data/attendance.db") -> RealtimeMonitor:
    """Get or create global monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = RealtimeMonitor(db_path)
    return _monitor_instance
