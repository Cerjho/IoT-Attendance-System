"""
Network Timeout Configuration
Provides configurable timeouts for all network operations
"""
from typing import Dict, Optional, Tuple

from src.utils.logging_factory import get_logger

logger = get_logger(__name__)


class NetworkTimeouts:
    """Centralized network timeout configuration"""

    def __init__(self, config: Dict):
        """
        Initialize network timeouts from config

        Config keys:
            connect_timeout: Time to establish connection (default: 5s)
            read_timeout: Time to wait for response data (default: 10s)
            supabase_connect_timeout: Override for Supabase REST (default: use connect_timeout)
            supabase_read_timeout: Override for Supabase REST (default: use read_timeout)
            storage_connect_timeout: Override for Storage uploads (default: use connect_timeout)
            storage_read_timeout: Override for Storage uploads (default: 30s for large files)
            connectivity_timeout: Timeout for connectivity checks (default: 3s)
            sms_timeout: Timeout for SMS API calls (default: 10s)
        """
        self.connect_timeout = config.get("connect_timeout", 5)
        self.read_timeout = config.get("read_timeout", 10)

        # Service-specific overrides
        self.supabase_connect = config.get("supabase_connect_timeout", self.connect_timeout)
        self.supabase_read = config.get("supabase_read_timeout", self.read_timeout)
        self.storage_connect = config.get("storage_connect_timeout", self.connect_timeout)
        self.storage_read = config.get("storage_read_timeout", 30)  # Longer for uploads
        self.connectivity_timeout = config.get("connectivity_timeout", 3)
        self.sms_timeout = config.get("sms_timeout", 10)

        logger.info(
            f"⏱️  Network timeouts initialized: connect={self.connect_timeout}s, read={self.read_timeout}s"
        )
        logger.debug(
            f"Service timeouts: Supabase({self.supabase_connect}s/{self.supabase_read}s), "
            f"Storage({self.storage_connect}s/{self.storage_read}s), "
            f"Connectivity({self.connectivity_timeout}s), SMS({self.sms_timeout}s)"
        )

    def get_supabase_timeout(self) -> Tuple[int, int]:
        """
        Get timeout tuple for Supabase REST API calls

        Returns:
            (connect_timeout, read_timeout)
        """
        logger.debug(f"Supabase timeout: ({self.supabase_connect}s, {self.supabase_read}s)")
        return (self.supabase_connect, self.supabase_read)

    def get_storage_timeout(self) -> Tuple[int, int]:
        """
        Get timeout tuple for Storage uploads

        Returns:
            (connect_timeout, read_timeout)
        """
        logger.debug(f"Storage timeout: ({self.storage_connect}s, {self.storage_read}s)")
        return (self.storage_connect, self.storage_read)

    def get_connectivity_timeout(self) -> int:
        """
        Get timeout for connectivity checks

        Returns:
            timeout in seconds
        """
        logger.debug(f"Connectivity timeout: {self.connectivity_timeout}s")
        return self.connectivity_timeout

    def get_sms_timeout(self) -> int:
        """
        Get timeout for SMS API calls

        Returns:
            timeout in seconds
        """
        logger.debug(f"SMS timeout: {self.sms_timeout}s")
        return self.sms_timeout

    def get_timeout_dict(self) -> Dict[str, int]:
        """
        Get all timeout values as dict

        Returns:
            dict with all timeout settings
        """
        timeout_dict = {
            "connect_timeout": self.connect_timeout,
            "read_timeout": self.read_timeout,
            "supabase_connect": self.supabase_connect,
            "supabase_read": self.supabase_read,
            "storage_connect": self.storage_connect,
            "storage_read": self.storage_read,
            "connectivity_timeout": self.connectivity_timeout,
            "sms_timeout": self.sms_timeout,
        }
        logger.debug(f"All timeouts retrieved: {timeout_dict}")
        return timeout_dict


# Default timeout configuration
DEFAULT_TIMEOUTS = {
    "connect_timeout": 5,
    "read_timeout": 10,
    "supabase_connect_timeout": 5,
    "supabase_read_timeout": 10,
    "storage_connect_timeout": 5,
    "storage_read_timeout": 30,
    "connectivity_timeout": 3,
    "sms_timeout": 10,
}
