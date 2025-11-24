"""
Network Connectivity Monitor
Monitors internet connectivity for cloud sync operations
"""

import logging
import socket
import time
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ConnectivityMonitor:
    """Monitors network connectivity for cloud operations"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize connectivity monitor
        
        Args:
            config: Dictionary with settings:
                - check_interval: int (seconds between checks)
                - timeout: int (connection timeout in seconds)
                - test_url: str (URL to ping for connectivity test)
        """
        self.config = config or {}
        self.check_interval = self.config.get('check_connection_interval', 30)
        self.timeout = self.config.get('timeout', 5)
        self.test_url = self.config.get('test_url', 'https://www.google.com')
        
        self._is_online = None
        self._last_check = None
        self._consecutive_failures = 0
    
    def is_online(self, force_check: bool = False) -> bool:
        """
        Check if internet connection is available
        
        Args:
            force_check: Force new check even if recently checked
        
        Returns:
            True if online, False otherwise
        """
        # Use cached result if recent
        if not force_check and self._last_check:
            time_since_check = (datetime.now() - self._last_check).total_seconds()
            if time_since_check < self.check_interval:
                return self._is_online
        
        # Perform new connectivity check
        self._is_online = self._check_connectivity()
        self._last_check = datetime.now()
        
        if self._is_online:
            if self._consecutive_failures > 0:
                logger.info(f"Connection restored after {self._consecutive_failures} failures")
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1
            if self._consecutive_failures == 1:
                logger.warning("Internet connection lost")
            else:
                logger.debug(f"Still offline (failure #{self._consecutive_failures})")
        
        return self._is_online
    
    def _check_connectivity(self) -> bool:
        """
        Internal method to check connectivity
        Tries multiple methods for reliability
        """
        # Method 1: DNS resolution test
        if self._check_dns():
            return True
        
        # Method 2: HTTP request test
        if self._check_http():
            return True
        
        # Method 3: Socket connection test
        if self._check_socket():
            return True
        
        return False
    
    def _check_dns(self) -> bool:
        """Check connectivity via DNS resolution"""
        try:
            socket.gethostbyname('www.google.com')
            logger.debug("Connectivity confirmed via DNS")
            return True
        except socket.error:
            return False
    
    def _check_http(self) -> bool:
        """Check connectivity via HTTP request"""
        try:
            response = requests.get(self.test_url, timeout=self.timeout)
            if response.status_code == 200:
                logger.debug("Connectivity confirmed via HTTP")
                return True
            return False
        except (requests.RequestException, requests.ConnectionError, requests.Timeout):
            return False
    
    def _check_socket(self) -> bool:
        """Check connectivity via socket connection"""
        try:
            # Try to connect to Google DNS
            sock = socket.create_connection(("8.8.8.8", 53), timeout=self.timeout)
            sock.close()
            logger.debug("Connectivity confirmed via socket")
            return True
        except socket.error:
            return False
    
    def wait_for_connection(self, timeout: int = 30, retry_interval: int = 5) -> bool:
        """
        Wait for internet connection to become available
        
        Args:
            timeout: Maximum time to wait in seconds
            retry_interval: Time between retry attempts in seconds
        
        Returns:
            True if connection established, False if timeout
        """
        start_time = time.time()
        attempts = 0
        
        logger.info(f"Waiting for internet connection (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            attempts += 1
            
            if self.is_online(force_check=True):
                logger.info(f"Connection established after {attempts} attempts")
                return True
            
            logger.debug(f"Connection attempt {attempts} failed, retrying in {retry_interval}s...")
            time.sleep(retry_interval)
        
        logger.warning(f"Connection timeout after {timeout}s ({attempts} attempts)")
        return False
    
    def get_connection_quality(self) -> Dict:
        """
        Get connection quality metrics
        
        Returns:
            Dictionary with quality metrics:
                - online: bool
                - latency_ms: float (ping latency)
                - consecutive_failures: int
                - last_check: str (ISO timestamp)
        """
        latency = None
        
        if self._is_online:
            # Measure latency
            try:
                start = time.time()
                response = requests.get(self.test_url, timeout=self.timeout)
                latency = (time.time() - start) * 1000  # Convert to ms
            except:
                pass
        
        return {
            'online': self._is_online or False,
            'latency_ms': latency,
            'consecutive_failures': self._consecutive_failures,
            'last_check': self._last_check.isoformat() if self._last_check else None
        }
    
    def reset_failure_count(self):
        """Reset consecutive failure counter"""
        self._consecutive_failures = 0
    
    def get_status_string(self) -> str:
        """Get human-readable status string"""
        if self._is_online is None:
            return "Not checked"
        elif self._is_online:
            return "Online"
        else:
            return f"Offline ({self._consecutive_failures} failures)"
