"""
Configuration Loader Module
Loads and manages application configuration
"""
import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and manages application configuration."""
    
    def __init__(self, config_file: str = None):
        """
        Initialize config loader.
        
        Args:
            config_file: Path to config JSON file
        """
        self.config: Dict[str, Any] = {}
        self.config_file = config_file
        
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
        
        # Resolve environment variable placeholders in config
        self._resolve_env_placeholders(self.config)
        
        # Load from environment variables (override file config)
        self.load_from_env()
    
    def load_from_file(self, filepath: str) -> bool:
        """
        Load configuration from JSON file.
        
        Args:
            filepath: Path to config file
        
        Returns:
            bool: True if successful
        """
        try:
            with open(filepath, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Configuration loaded from: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading config file: {str(e)}")
            return False
    
    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            'SUPABASE_URL': ('cloud', 'url'),
            'SUPABASE_KEY': ('cloud', 'api_key'),
            'DEVICE_ID': ('cloud', 'device_id'),
            'SMS_ENABLED': ('sms_notifications', 'enabled'),
            'SMS_USERNAME': ('sms_notifications', 'username'),
            'SMS_PASSWORD': ('sms_notifications', 'password'),
            'SMS_DEVICE_ID': ('sms_notifications', 'device_id'),
            'SMS_API_URL': ('sms_notifications', 'api_url'),
            'CAMERA_INDEX': ('camera', 'index'),
            'CAMERA_RESOLUTION_WIDTH': ('camera', 'resolution', 'width'),
            'CAMERA_RESOLUTION_HEIGHT': ('camera', 'resolution', 'height'),
            'RECOGNITION_TOLERANCE': ('recognition', 'tolerance'),
            'DUPLICATE_WINDOW': ('attendance', 'duplicate_window_seconds'),
            'LOG_LEVEL': ('logging', 'level'),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_value(self.config, config_path, value)
                logger.debug(f"Config from env: {env_var}")
    
    def _set_nested_value(self, config: dict, path: tuple, value: Any) -> None:
        """Set nested dictionary value using tuple path."""
        for key in path[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[path[-1]] = value
    
    def _resolve_env_placeholders(self, config: dict) -> None:
        """Recursively resolve ${ENV_VAR} placeholders in config values."""
        for key, value in config.items():
            if isinstance(value, dict):
                self._resolve_env_placeholders(value)
            elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                env_value = os.getenv(env_var)
                if env_value:
                    config[key] = env_value
                    logger.debug(f"Resolved {env_var} from environment")
                else:
                    logger.warning(f"Environment variable {env_var} not set for config key {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.
        
        Args:
            key: Key path (e.g., 'supabase.url')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self.config.copy()
    
    def save_to_file(self, filepath: str) -> bool:
        """
        Save current configuration to file.
        
        Args:
            filepath: Path to save config file
        
        Returns:
            bool: True if successful
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config file: {str(e)}")
            return False


def load_config(config_file: str = None) -> ConfigLoader:
    """
    Factory function to load configuration.
    
    Args:
        config_file: Path to config file (optional)
    
    Returns:
        ConfigLoader: Configured loader instance
    """
    return ConfigLoader(config_file)
