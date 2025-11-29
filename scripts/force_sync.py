#!/usr/bin/env python3
"""
Force sync all unsynced attendance records to Supabase via REST.
Uses project config loader and connectivity monitor.
"""
import sys
from src.cloud.cloud_sync import CloudSyncManager
from src.database.sync_queue import SyncQueueManager
from src.network.connectivity import ConnectivityMonitor
from src.utils.config_loader import load_config


def main():
    config = load_config("config/config.json")
    # Ensure safe defaults
    config.setdefault("enabled", True)
    config.setdefault("retry_attempts", 3)
    config.setdefault("retry_delay", 30)

    sync_queue = SyncQueueManager(db_path="data/attendance.db")
    connectivity = ConnectivityMonitor(config)
    cloud = CloudSyncManager(config, sync_queue, connectivity)

    result = cloud.force_sync_all()
    print(result)


if __name__ == "__main__":
    sys.exit(main())
