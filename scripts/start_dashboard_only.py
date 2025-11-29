#!/usr/bin/env python3
"""
Standalone Admin Dashboard
Runs the admin dashboard API without requiring the camera system.
Use this to access endpoints when you don't need camera/attendance functionality.
"""
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config, setup_logger
from src.utils.admin_dashboard import AdminDashboard
from src.utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)


def main():
    """Start standalone admin dashboard."""
    print("\n" + "=" * 70)
    print("IoT ATTENDANCE SYSTEM - ADMIN DASHBOARD ONLY")
    print("=" * 70)
    print("\nStarting dashboard without camera/attendance system...")
    print("This allows you to access monitoring endpoints.\n")

    # Setup logger
    setup_logger(name="admin_dashboard")

    # Load config
    config = load_config("config/config.json")
    
    # Get dashboard config
    dashboard_config = config.get("admin_dashboard", {})
    enabled = dashboard_config.get("enabled", True)
    host = dashboard_config.get("host", "0.0.0.0")
    port = dashboard_config.get("port", 8080)
    
    if not enabled:
        print("❌ Admin dashboard is disabled in config.json")
        print("   Set 'admin_dashboard.enabled' to true")
        return 1

    # Initialize metrics if enabled
    metrics_collector = None
    if config.get("metrics", {}).get("enabled", True):
        metrics_collector = MetricsCollector(config.get("metrics", {}))
        logger.info("Metrics collector initialized")

    # Get database path
    db_path = "data/attendance.db"
    if not Path(db_path).exists():
        print(f"⚠️  Warning: Database not found at {db_path}")
        print("   Some endpoints may return empty results")
    
    # Create dashboard
    dashboard = AdminDashboard(
        config=config,
        metrics_collector=metrics_collector,
        shutdown_manager=None,
        db_path=db_path,
        host=host,
        port=port,
    )

    try:
        # Start dashboard
        dashboard.start()
        
        print(f"\n✅ Admin Dashboard Running!")
        print(f"   Access at: http://localhost:{port}")
        if host == "0.0.0.0":
            # Get IP address
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                print(f"   Or from network: http://{ip}:{port}")
            except:
                pass
        
        print("\n📍 Available Endpoints:")
        print(f"   • GET  /health              - Health check")
        print(f"   • GET  /status              - System status")
        print(f"   • GET  /metrics             - Metrics (JSON)")
        print(f"   • GET  /metrics/prometheus  - Metrics (Prometheus)")
        print(f"   • GET  /scans/recent        - Recent scans")
        print(f"   • GET  /queue/status        - Sync queue status")
        print(f"   • GET  /config              - Configuration (sanitized)")
        print(f"   • GET  /system/info         - System information")
        
        print("\n💡 Example:")
        print(f"   curl http://localhost:{port}/health")
        print(f"   curl http://localhost:{port}/status | jq .")
        
        print("\nPress Ctrl+C to stop")
        print("=" * 70 + "\n")
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutdown requested...")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1
        
    finally:
        # Cleanup
        if dashboard:
            dashboard.stop()
        print("\n✅ Dashboard stopped")
        print("=" * 70 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
