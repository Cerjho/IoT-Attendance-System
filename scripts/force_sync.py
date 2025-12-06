#!/usr/bin/env python3
"""
Force sync all unsynced attendance records to Supabase via REST.
Uses project config loader and connectivity monitor.
"""
import sys
import os

# Add project root to Python path to allow imports from src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cloud.cloud_sync import CloudSyncManager
from src.database.sync_queue import SyncQueueManager
from src.network.connectivity import ConnectivityMonitor
from src.utils.config_loader import load_config
from src.database.sync_queue import SyncQueueManager
from src.network.connectivity import ConnectivityMonitor
from src.utils.config_loader import load_config


def main():
    config_obj = load_config("config/config.json")
    
    # Extract cloud config as dict and ensure safe defaults
    cloud_config = config_obj.get("cloud", {})
    if not isinstance(cloud_config, dict):
        cloud_config = {}
    
    cloud_config.setdefault("enabled", True)
    cloud_config.setdefault("retry_attempts", 3)
    cloud_config.setdefault("retry_delay", 30)
    
    # Get credentials from environment
    cloud_config["url"] = os.getenv("SUPABASE_URL", cloud_config.get("url"))
    cloud_config["api_key"] = os.getenv("SUPABASE_KEY", cloud_config.get("api_key"))
    cloud_config["device_id"] = os.getenv("DEVICE_ID", cloud_config.get("device_id", "device_001"))

    sync_queue = SyncQueueManager(db_path="data/attendance.db")
    connectivity = ConnectivityMonitor(config_obj.get("offline_mode", {}))
    cloud = CloudSyncManager(cloud_config, sync_queue, connectivity)

    result = cloud.force_sync_all()
    print(result)


if __name__ == "__main__":
    sys.exit(main())
