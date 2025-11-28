"""
Configuration Loader Module
Loads and manages application configuration
"""

import json
import logging
import os
from typing import Any, Dict, Optional

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
            with open(filepath, "r") as f:
                self.config = json.load(f)
            logger.info(f"Configuration loaded from: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error loading config file: {str(e)}")
            return False

    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            "SUPABASE_URL": ("cloud", "url"),
            "SUPABASE_KEY": ("cloud", "api_key"),
            "DEVICE_ID": ("cloud", "device_id"),
            "SMS_ENABLED": ("sms_notifications", "enabled"),
            "SMS_USERNAME": ("sms_notifications", "username"),
            "SMS_PASSWORD": ("sms_notifications", "password"),
            "SMS_DEVICE_ID": ("sms_notifications", "device_id"),
            "SMS_API_URL": ("sms_notifications", "api_url"),
            "CAMERA_INDEX": ("camera", "index"),
            "CAMERA_RESOLUTION_WIDTH": ("camera", "resolution", "width"),
            "CAMERA_RESOLUTION_HEIGHT": ("camera", "resolution", "height"),
            "RECOGNITION_TOLERANCE": ("recognition", "tolerance"),
            "DUPLICATE_WINDOW": ("attendance", "duplicate_window_seconds"),
            "LOG_LEVEL": ("logging", "level"),
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
            elif (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                env_var = value[2:-1]
                env_value = os.getenv(env_var)
                if env_value:
                    config[key] = env_value
                    logger.debug(f"Resolved {env_var} from environment")
                else:
                    logger.warning(
                        f"Environment variable {env_var} not set for config key {key}"
                    )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Key path (e.g., 'supabase.url')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
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

    def validate(self) -> Dict[str, str]:
        """Validate configuration values and required sections.

        Returns:
            Dict mapping field paths to error messages (empty if valid)
        """
        errors: Dict[str, str] = {}

        def require(path: str, value, condition=lambda v: v is not None):
            if not condition(value):
                errors[path] = "Missing or invalid value"

        # Cloud config (only if enabled)
        cloud_cfg = self.get("cloud", {}) or {}
        if cloud_cfg.get("enabled", True):  # default assume enabled unless explicit false
            require("cloud.url", cloud_cfg.get("url"), lambda v: isinstance(v, str) and v and not v.startswith("${"))
            require("cloud.api_key", cloud_cfg.get("api_key"), lambda v: isinstance(v, str) and v and not v.startswith("${"))
            require("cloud.device_id", cloud_cfg.get("device_id"), lambda v: isinstance(v, str) and v)

        # SMS notifications (only if enabled)
        sms_cfg = self.get("sms_notifications", {}) or {}
        if sms_cfg.get("enabled", False):
            require("sms_notifications.username", sms_cfg.get("username"), lambda v: isinstance(v, str) and v and not v.startswith("${"))
            require("sms_notifications.password", sms_cfg.get("password"), lambda v: isinstance(v, str) and v and not v.startswith("${"))
            require("sms_notifications.device_id", sms_cfg.get("device_id"), lambda v: isinstance(v, str) and v and not v.startswith("${"))
            # Quiet hours format HH:MM
            qh = sms_cfg.get("quiet_hours", {}) or {}
            def valid_hhmm(v: str) -> bool:
                if not isinstance(v, str) or len(v) != 5 or v[2] != ":":
                    return False
                try:
                    h = int(v[:2]); m = int(v[3:]); return 0 <= h < 24 and 0 <= m < 60
                except Exception:
                    return False
            if qh.get("enabled", True):
                require("sms_notifications.quiet_hours.start", qh.get("start"), valid_hhmm)
                require("sms_notifications.quiet_hours.end", qh.get("end"), valid_hhmm)
            # Cooldown numeric
            require("sms_notifications.duplicate_sms_cooldown_minutes", sms_cfg.get("duplicate_sms_cooldown_minutes"), lambda v: isinstance(v, (int, float)) and v >= 0)

        # Camera resolution sanity
        cam = self.get("camera", {}) or {}
        if isinstance(cam.get("resolution", {}), dict):
            width = cam.get("resolution", {}).get("width")
            height = cam.get("resolution", {}).get("height")
            if width is not None and (not isinstance(width, int) or width <= 0):
                errors["camera.resolution.width"] = "Width must be positive integer"
            if height is not None and (not isinstance(height, int) or height <= 0):
                errors["camera.resolution.height"] = "Height must be positive integer"

        # Logging level if present
        log_cfg = self.get("logging", {}) or {}
        if "level" in log_cfg and log_cfg["level"] not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors["logging.level"] = "Invalid logging level"

        if errors:
            logger.error(f"Configuration validation failed: {len(errors)} issues")
            for k, v in errors.items():
                logger.error(f"  {k}: {v}")
        else:
            logger.info("Configuration validation passed")

        return errors

    def save_to_file(self, filepath: str) -> bool:
        """
        Save current configuration to file.

        Args:
            filepath: Path to save config file

        Returns:
            bool: True if successful
        """
        try:
            with open(filepath, "w") as f:
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
