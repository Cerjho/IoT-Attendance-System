"""
Multi-Device Manager

Handles device discovery, registration, heartbeat monitoring,
and centralized management for multiple IoT attendance devices.
"""

import json
import logging
import socket
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

from ..database.device_registry import DeviceRegistry

logger = logging.getLogger(__name__)


class MultiDeviceManager:
    """Manage multiple IoT attendance devices from central dashboard."""

    def __init__(self, config: Dict, registry: DeviceRegistry):
        """Initialize multi-device manager."""
        self.config = config
        self.registry = registry
        self.running = False
        self.heartbeat_thread = None
        self.discovery_thread = None

        # Get current device info
        self.current_device_id = config.get('device_id', 'unknown')
        self.current_device_name = config.get('device_name', 'Unknown Device')

        logger.info("Multi-device manager initialized")

    def start(self):
        """Start background monitoring threads."""
        if self.running:
            return

        self.running = True

        # Start heartbeat checker
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_checker_loop,
            daemon=True
        )
        self.heartbeat_thread.start()

        # Auto-register current device
        self._register_current_device()

        logger.info("Multi-device manager started")

    def stop(self):
        """Stop background threads."""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        logger.info("Multi-device manager stopped")

    def _register_current_device(self):
        """Auto-register the current device."""
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            # Extract location from config
            location_config = self.config.get('location', {})
            building = location_config.get('building')
            floor = location_config.get('floor')
            room = location_config.get('room')
            location = location_config.get('description', f"{building}/{floor}/{room}")

            # Register this device
            self.registry.register_device(
                device_id=self.current_device_id,
                device_name=self.current_device_name,
                ip_address=local_ip,
                location=location,
                building=building,
                floor=floor,
                room=room,
                config=self.config
            )

            logger.info(f"Current device registered: {self.current_device_id} at {local_ip}")

        except Exception as e:
            logger.error(f"Failed to auto-register current device: {e}")

    def _heartbeat_checker_loop(self):
        """Background thread to check device heartbeats."""
        while self.running:
            try:
                # Mark stale devices as offline
                self.registry.mark_device_offline_if_stale(timeout_minutes=5)

                # Sleep for 60 seconds
                time.sleep(60)

            except Exception as e:
                logger.error(f"Heartbeat checker error: {e}")
                time.sleep(10)

    def discover_devices(self, network: str = "192.168.1.0/24") -> List[Dict]:
        """
        Discover attendance devices on the network.
        
        Scans for devices listening on port 8080 with admin dashboard API.
        """
        discovered = []

        try:
            import ipaddress

            network_obj = ipaddress.ip_network(network, strict=False)

            logger.info(f"Scanning network {network} for devices...")

            for ip in network_obj.hosts():
                ip_str = str(ip)

                # Skip current device
                if self._is_current_device_ip(ip_str):
                    continue

                # Try to connect
                if self._probe_device(ip_str):
                    device_info = self._get_device_info(ip_str)
                    if device_info:
                        discovered.append(device_info)
                        logger.info(f"Discovered device: {device_info['device_id']} at {ip_str}")

            logger.info(f"Discovery complete: found {len(discovered)} devices")

        except Exception as e:
            logger.error(f"Device discovery failed: {e}")

        return discovered

    def _is_current_device_ip(self, ip: str) -> bool:
        """Check if IP belongs to current device."""
        try:
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            return ip in local_ips or ip == '127.0.0.1'
        except:
            return False

    def _probe_device(self, ip: str, port: int = 8080, timeout: int = 2) -> bool:
        """Check if device is reachable."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False

    def _get_device_info(self, ip: str, port: int = 8080) -> Optional[Dict]:
        """Get device information from API."""
        try:
            # Try without auth first (for initial discovery)
            response = requests.get(
                f"http://{ip}:{port}/system/info",
                timeout=3
            )

            if response.status_code == 200:
                info = response.json()
                return {
                    'device_id': info.get('device_id', f'device_{ip.replace(".", "_")}'),
                    'device_name': info.get('hostname', 'Unknown'),
                    'ip_address': ip,
                    'port': port,
                    'version': info.get('python_version', 'Unknown'),
                    'platform': info.get('platform', 'Unknown'),
                    'status': 'online'
                }

            return None

        except Exception as e:
            logger.debug(f"Failed to get device info from {ip}: {e}")
            return None

    def register_discovered_devices(self, devices: List[Dict]) -> int:
        """Register multiple discovered devices."""
        count = 0
        for device in devices:
            success = self.registry.register_device(
                device_id=device['device_id'],
                device_name=device['device_name'],
                ip_address=device['ip_address'],
                location=device.get('location'),
                api_key=device.get('api_key')
            )
            if success:
                count += 1

        logger.info(f"Registered {count}/{len(devices)} discovered devices")
        return count

    def send_command_to_device(
        self,
        device_id: str,
        command: str,
        params: Dict = None
    ) -> Dict:
        """Send command to a specific device."""
        device = self.registry.get_device(device_id)
        if not device:
            return {'success': False, 'error': 'Device not found'}

        try:
            ip = device['ip_address']
            port = device.get('port', 8080)
            api_key = device.get('api_key')

            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'

            # Map commands to API endpoints
            endpoint_map = {
                'status': '/status',
                'health': '/health',
                'config': '/config',
                'metrics': '/metrics',
                'scans': '/scans/recent',
                'queue': '/queue/status',
                'sync': '/force_sync',  # If implemented
                'restart': '/restart',  # If implemented
            }

            endpoint = endpoint_map.get(command)
            if not endpoint:
                return {'success': False, 'error': f'Unknown command: {command}'}

            url = f"http://{ip}:{port}{endpoint}"

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'details': response.text
                }

        except Exception as e:
            logger.error(f"Failed to send command to {device_id}: {e}")
            return {'success': False, 'error': str(e)}

    def get_all_devices_status(self) -> List[Dict]:
        """Get status of all registered devices."""
        devices = self.registry.get_all_devices()
        results = []

        for device in devices:
            device_id = device['device_id']

            # Try to get current status
            status_result = self.send_command_to_device(device_id, 'status')

            results.append({
                'device_id': device_id,
                'device_name': device['device_name'],
                'ip_address': device['ip_address'],
                'location': device['location'],
                'building': device['building'],
                'floor': device['floor'],
                'room': device['room'],
                'status': device['status'],
                'last_heartbeat': device['last_heartbeat'],
                'total_scans': device['total_scans'],
                'online': status_result.get('success', False),
                'current_data': status_result.get('data') if status_result.get('success') else None
            })

        return results

    def get_aggregated_metrics(self) -> Dict:
        """Get aggregated metrics across all devices."""
        devices = self.registry.get_all_devices(status='online')

        total_scans = 0
        total_queue = 0
        devices_with_issues = 0

        for device in devices:
            device_id = device['device_id']

            # Get metrics from device
            metrics_result = self.send_command_to_device(device_id, 'metrics')
            if metrics_result.get('success'):
                data = metrics_result['data']
                total_scans += data.get('total_scans', 0)
                total_queue += data.get('queue_count', 0)

                # Check for issues
                if data.get('queue_count', 0) > 100:
                    devices_with_issues += 1

        status_summary = self.registry.get_device_status_summary()

        return {
            'total_devices': status_summary.get('total', 0),
            'online_devices': status_summary.get('online', 0),
            'offline_devices': status_summary.get('offline', 0),
            'devices_with_issues': devices_with_issues,
            'total_scans_today': total_scans,
            'total_queue_pending': total_queue,
            'timestamp': datetime.now().isoformat()
        }

    def bulk_send_command(
        self,
        device_ids: List[str],
        command: str,
        params: Dict = None
    ) -> Dict:
        """Send command to multiple devices."""
        results = {}

        for device_id in device_ids:
            result = self.send_command_to_device(device_id, command, params)
            results[device_id] = result

        success_count = sum(1 for r in results.values() if r.get('success'))

        return {
            'total': len(device_ids),
            'success': success_count,
            'failed': len(device_ids) - success_count,
            'results': results
        }

    def update_device_heartbeat_from_remote(self, device_id: str, metrics: Dict):
        """Update heartbeat when device reports in."""
        self.registry.update_heartbeat(
            device_id=device_id,
            status='online',
            metrics=metrics
        )

    def get_device_groups_summary(self) -> List[Dict]:
        """Get summary of device groups."""
        # TODO: Implement group listing
        return []
