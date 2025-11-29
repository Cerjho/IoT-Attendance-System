"""
Network Timeout Configuration
Provides configurable timeouts for all network operations
"""
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


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
            f"Network timeouts: connect={self.connect_timeout}s, read={self.read_timeout}s"
        )

    def get_supabase_timeout(self) -> Tuple[int, int]:
        """
        Get timeout tuple for Supabase REST API calls

        Returns:
            (connect_timeout, read_timeout)
        """
        return (self.supabase_connect, self.supabase_read)

    def get_storage_timeout(self) -> Tuple[int, int]:
        """
        Get timeout tuple for Storage uploads

        Returns:
            (connect_timeout, read_timeout)
        """
        return (self.storage_connect, self.storage_read)

    def get_connectivity_timeout(self) -> int:
        """
        Get timeout for connectivity checks

        Returns:
            timeout in seconds
        """
        return self.connectivity_timeout

    def get_sms_timeout(self) -> int:
        """
        Get timeout for SMS API calls

        Returns:
            timeout in seconds
        """
        return self.sms_timeout

    def get_timeout_dict(self) -> Dict[str, int]:
        """
        Get all timeout values as dict

        Returns:
            dict with all timeout settings
        """
        return {
            "connect_timeout": self.connect_timeout,
            "read_timeout": self.read_timeout,
            "supabase_connect": self.supabase_connect,
            "supabase_read": self.supabase_read,
            "storage_connect": self.storage_connect,
            "storage_read": self.storage_read,
            "connectivity_timeout": self.connectivity_timeout,
            "sms_timeout": self.sms_timeout,
        }


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
