#!/usr/bin/env python3
"""System Status Probe
Outputs JSON with sync queue metrics, cloud sync status, and SMS notifier stats.
Run: python scripts/status.py
"""
import json
import os
import sys
from datetime import datetime

# Ensure module search path
sys.path.insert(0, os.path.dirname(__file__) + '/..')

from src.utils import load_config
from src.database.sync_queue import SyncQueueManager
from src.cloud.cloud_sync import CloudSyncManager
from src.notifications.sms_notifier import SMSNotifier, TimeProvider
from src.network.connectivity import ConnectivityMonitor

DB_PATH = "data/attendance.db"


def main():
    cfg_loader = load_config("config/config.json")
    cfg_loader.validate()
    config = cfg_loader.get_all()

    cloud_cfg = config.get("cloud", {})
    cloud_cfg["url"] = os.getenv("SUPABASE_URL", cloud_cfg.get("url"))
    cloud_cfg["api_key"] = os.getenv("SUPABASE_KEY", cloud_cfg.get("api_key"))
    cloud_cfg["device_id"] = os.getenv("DEVICE_ID", cloud_cfg.get("device_id", "device_001"))

    # Initialize queue + connectivity (no camera)
    queue = SyncQueueManager(DB_PATH)
    connectivity = ConnectivityMonitor(config.get("offline_mode", {}))
    # Disable cloud if placeholders remain
    def _is_placeholder(v):
        return isinstance(v, str) and v.startswith("${")

    if _is_placeholder(cloud_cfg.get("url")) or _is_placeholder(cloud_cfg.get("api_key")):
        cloud_cfg["enabled"] = False

    try:
        cloud_sync = CloudSyncManager(cloud_cfg, queue, connectivity)
    except Exception as e:
        cloud_sync = None

    sms_cfg = config.get("sms_notifications", {})
    sms = SMSNotifier(sms_cfg, time_provider=TimeProvider())

    sync_status = {}
    try:
        if cloud_sync and cloud_sync.enabled:
            sync_status = cloud_sync.get_sync_status()
        else:
            sync_status = {
                "enabled": False,
                "online": False,
                "device_id": cloud_cfg.get("device_id"),
                "reason": "cloud disabled or missing credentials",
            }
    except Exception as e:
        sync_status = {"error": f"failed to get sync status: {e}"}

    # SMS simple stats
    sms_stats = {
        "enabled": sms.enabled,
        "cooldown_minutes": sms.cooldown_minutes if sms.enabled else None,
        "quiet_hours": sms.quiet_hours if sms.enabled else None,
        "recent_notifications": len(sms.recent_notifications),
    }

    out = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cloud_sync": sync_status,
        "sms": sms_stats,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
