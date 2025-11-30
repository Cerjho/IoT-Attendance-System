"""
Device Registry Database

Manages multiple IoT attendance devices for centralized administration.
Tracks device status, configuration, location, and health metrics.
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DeviceRegistry:
    """Manage multiple IoT attendance devices."""

    def __init__(self, db_path: str = "data/devices.db"):
        """Initialize device registry database."""
        self.db_path = db_path
        self._lock = threading.Lock()

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()
        logger.info(f"Device registry initialized: {db_path}")

    def _init_database(self):
        """Create device registry tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Devices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                device_type TEXT DEFAULT 'raspberry_pi',
                ip_address TEXT,
                port INTEGER DEFAULT 8080,
                location TEXT,
                building TEXT,
                floor TEXT,
                room TEXT,
                mac_address TEXT,
                api_key TEXT,
                status TEXT DEFAULT 'offline',
                last_heartbeat TEXT,
                last_scan TEXT,
                total_scans INTEGER DEFAULT 0,
                version TEXT,
                config_json TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Device groups (for organizing devices by location/purpose)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Device group membership
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_group_members (
                device_id TEXT,
                group_id INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (device_id, group_id),
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES device_groups(group_id) ON DELETE CASCADE
            )
        """)

        # Device heartbeat log (last 24 hours)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT,
                cpu_usage REAL,
                memory_usage REAL,
                disk_usage REAL,
                queue_count INTEGER,
                camera_ok INTEGER,
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            )
        """)

        # Device events/alerts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                message TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0,
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_location ON devices(building, floor, room)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_heartbeats_device_time ON device_heartbeats(device_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_device ON device_events(device_id, timestamp)")

        conn.commit()
        conn.close()

        logger.info("Device registry tables initialized")

    def register_device(
        self,
        device_id: str,
        device_name: str,
        ip_address: str,
        location: str = None,
        building: str = None,
        floor: str = None,
        room: str = None,
        api_key: str = None,
        config: Dict = None
    ) -> bool:
        """Register a new device or update existing."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                config_json = json.dumps(config) if config else None
                now = datetime.now().isoformat()

                cursor.execute("""
                    INSERT INTO devices (
                        device_id, device_name, ip_address, location,
                        building, floor, room, api_key, config_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(device_id) DO UPDATE SET
                        device_name = excluded.device_name,
                        ip_address = excluded.ip_address,
                        location = excluded.location,
                        building = excluded.building,
                        floor = excluded.floor,
                        room = excluded.room,
                        api_key = excluded.api_key,
                        config_json = excluded.config_json,
                        updated_at = excluded.updated_at
                """, (device_id, device_name, ip_address, location, building,
                      floor, room, api_key, config_json, now))

                conn.commit()
                conn.close()

                logger.info(f"Device registered: {device_id} at {ip_address}")
                return True

            except Exception as e:
                logger.error(f"Failed to register device {device_id}: {e}")
                return False

    def update_heartbeat(
        self,
        device_id: str,
        status: str = "online",
        metrics: Dict = None
    ) -> bool:
        """Update device heartbeat and status."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                now = datetime.now().isoformat()

                # Update device status
                cursor.execute("""
                    UPDATE devices
                    SET status = ?, last_heartbeat = ?, updated_at = ?
                    WHERE device_id = ?
                """, (status, now, now, device_id))

                # Log heartbeat
                if metrics:
                    cursor.execute("""
                        INSERT INTO device_heartbeats (
                            device_id, timestamp, status, cpu_usage,
                            memory_usage, disk_usage, queue_count, camera_ok
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        device_id, now, status,
                        metrics.get('cpu_usage'),
                        metrics.get('memory_usage'),
                        metrics.get('disk_usage'),
                        metrics.get('queue_count'),
                        metrics.get('camera_ok', 1)
                    ))

                # Cleanup old heartbeats (keep last 24 hours)
                cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
                cursor.execute("""
                    DELETE FROM device_heartbeats
                    WHERE timestamp < ?
                """, (cutoff,))

                conn.commit()
                conn.close()

                return True

            except Exception as e:
                logger.error(f"Failed to update heartbeat for {device_id}: {e}")
                return False

    def get_device(self, device_id: str) -> Optional[Dict]:
        """Get device details."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM devices WHERE device_id = ?
            """, (device_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                device = dict(row)
                if device['config_json']:
                    device['config'] = json.loads(device['config_json'])
                return device

            return None

        except Exception as e:
            logger.error(f"Failed to get device {device_id}: {e}")
            return None

    def get_all_devices(
        self,
        status: str = None,
        building: str = None,
        floor: str = None
    ) -> List[Dict]:
        """Get all devices with optional filtering."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM devices WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)
            if building:
                query += " AND building = ?"
                params.append(building)
            if floor:
                query += " AND floor = ?"
                params.append(floor)

            query += " ORDER BY building, floor, room, device_name"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            devices = []
            for row in rows:
                device = dict(row)
                if device['config_json']:
                    device['config'] = json.loads(device['config_json'])
                devices.append(device)

            return devices

        except Exception as e:
            logger.error(f"Failed to get all devices: {e}")
            return []

    def get_device_status_summary(self) -> Dict:
        """Get summary of device statuses."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM devices
                GROUP BY status
            """)

            summary = {
                'total': 0,
                'online': 0,
                'offline': 0,
                'error': 0,
                'unknown': 0
            }

            for row in cursor.fetchall():
                status, count = row
                summary[status] = count
                summary['total'] += count

            conn.close()
            return summary

        except Exception as e:
            logger.error(f"Failed to get device status summary: {e}")
            return {}

    def log_device_event(
        self,
        device_id: str,
        event_type: str,
        message: str,
        severity: str = "info"
    ) -> bool:
        """Log a device event/alert."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO device_events (device_id, event_type, severity, message)
                    VALUES (?, ?, ?, ?)
                """, (device_id, event_type, severity, message))

                conn.commit()
                conn.close()

                logger.info(f"Event logged for {device_id}: {event_type} - {message}")
                return True

            except Exception as e:
                logger.error(f"Failed to log event for {device_id}: {e}")
                return False

    def get_device_events(
        self,
        device_id: str = None,
        severity: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get device events/alerts."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM device_events WHERE 1=1"
            params = []

            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            if severity:
                query += " AND severity = ?"
                params.append(severity)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get device events: {e}")
            return []

    def create_device_group(self, group_name: str, description: str = None) -> Optional[int]:
        """Create a device group."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO device_groups (group_name, description)
                    VALUES (?, ?)
                """, (group_name, description))

                group_id = cursor.lastrowid
                conn.commit()
                conn.close()

                logger.info(f"Device group created: {group_name} (ID: {group_id})")
                return group_id

            except sqlite3.IntegrityError:
                logger.warning(f"Device group already exists: {group_name}")
                return None
            except Exception as e:
                logger.error(f"Failed to create device group: {e}")
                return None

    def add_device_to_group(self, device_id: str, group_id: int) -> bool:
        """Add device to a group."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO device_group_members (device_id, group_id)
                    VALUES (?, ?)
                    ON CONFLICT DO NOTHING
                """, (device_id, group_id))

                conn.commit()
                conn.close()

                logger.info(f"Device {device_id} added to group {group_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to add device to group: {e}")
                return False

    def get_devices_in_group(self, group_id: int) -> List[Dict]:
        """Get all devices in a group."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT d.* FROM devices d
                JOIN device_group_members dgm ON d.device_id = dgm.device_id
                WHERE dgm.group_id = ?
                ORDER BY d.device_name
            """, (group_id,))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get devices in group: {e}")
            return []

    def mark_device_offline_if_stale(self, timeout_minutes: int = 5):
        """Mark devices as offline if no heartbeat in timeout period."""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cutoff = (datetime.now() - timedelta(minutes=timeout_minutes)).isoformat()

                cursor.execute("""
                    UPDATE devices
                    SET status = 'offline'
                    WHERE status != 'offline'
                    AND (last_heartbeat IS NULL OR last_heartbeat < ?)
                """, (cutoff,))

                affected = cursor.rowcount
                conn.commit()
                conn.close()

                if affected > 0:
                    logger.warning(f"Marked {affected} devices as offline (no heartbeat)")

                return affected

            except Exception as e:
                logger.error(f"Failed to mark stale devices offline: {e}")
                return 0

    def get_device_locations(self) -> Dict:
        """Get hierarchy of device locations."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT building, floor, room, COUNT(*) as device_count
                FROM devices
                WHERE building IS NOT NULL
                GROUP BY building, floor, room
                ORDER BY building, floor, room
            """)

            rows = cursor.fetchall()
            conn.close()

            # Build hierarchy
            locations = {}
            for row in rows:
                building = row['building']
                floor = row['floor'] or 'Unknown Floor'
                room = row['room'] or 'Unknown Room'
                count = row['device_count']

                if building not in locations:
                    locations[building] = {}
                if floor not in locations[building]:
                    locations[building][floor] = {}
                locations[building][floor][room] = count

            return locations

        except Exception as e:
            logger.error(f"Failed to get device locations: {e}")
            return {}

    def close(self):
        """Close database connections (placeholder for cleanup)."""
        pass
