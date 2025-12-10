#!/usr/bin/env python3
"""
Integration script for Phase 3 robustness enhancements

This script patches attendance_system.py to add:
- Watchdog timer
- SMS webhook receiver  
- Database backup manager
- Health endpoint
- Metrics collector

Usage:
    python integrate_phase3.py
"""
import logging
import re

logger = logging.getLogger(__name__)


IMPORTS_TO_ADD = """
from src.utils.watchdog import WatchdogTimer
from src.notifications.sms_webhook_receiver import SMSWebhookReceiver
from src.utils.database_backup import DatabaseBackupManager
from src.utils.health_endpoint import HealthEndpoint
from src.utils.metrics_collector import MetricsCollector
"""

INIT_CODE_TO_ADD = """
        # Phase 3 Robustness Components
        
        # Initialize watchdog timer
        watchdog_config = self.config.get("watchdog", {})
        self.watchdog = WatchdogTimer(
            timeout=watchdog_config.get("timeout_seconds", 30),
            restart_command=watchdog_config.get("restart_command", "sudo systemctl restart attendance-system"),
            log_file=watchdog_config.get("log_file", "data/logs/watchdog_restarts.log"),
            enabled=watchdog_config.get("enabled", True)
        )
        if self.watchdog.enabled:
            self.watchdog.start()
            logger.info("Watchdog timer started")
        
        # Initialize SMS webhook receiver
        webhook_config = self.config.get("sms_webhook", {})
        self.sms_webhook = SMSWebhookReceiver(
            port=webhook_config.get("port", 8081),
            host=webhook_config.get("host", "0.0.0.0"),
            db_path=self.database.db_path,
            enabled=webhook_config.get("enabled", True),
            auth_token=webhook_config.get("auth_token", "")
        )
        if self.sms_webhook.enabled:
            self.sms_webhook.start()
            logger.info("SMS webhook receiver started")
        
        # Initialize database backup manager
        backup_config = self.config.get("database_backup", {})
        self.backup_manager = DatabaseBackupManager(
            db_path=self.database.db_path,
            backup_dir=backup_config.get("backup_dir", "data/backups"),
            backup_interval=backup_config.get("backup_interval_seconds", 3600),
            keep_backups=backup_config.get("keep_backups", 24),
            enabled=backup_config.get("enabled", True)
        )
        if self.backup_manager.enabled:
            self.backup_manager.start()
            logger.info("Database backup manager started")
        
        # Initialize health endpoint
        health_config = self.config.get("health_endpoint", {})
        self.health_endpoint = HealthEndpoint(
            port=health_config.get("port", 8080),
            host=health_config.get("host", "0.0.0.0"),
            enabled=health_config.get("enabled", True),
            db_path=self.database.db_path
        )
        if self.health_endpoint.enabled:
            self.health_endpoint.start()
            logger.info("Health endpoint started")
        
        # Initialize metrics collector
        self.metrics = MetricsCollector(
            export_path="data/metrics.json",
            export_interval=300,  # 5 minutes
            enabled=True
        )
        self.metrics.start()
        logger.info("Metrics collector started")
"""

CLEANUP_CODE_TO_ADD = """
    def cleanup(self):
        '''Clean shutdown of all components'''
        logger.info("Shutting down system...")
        
        # Stop Phase 3 components
        if hasattr(self, 'watchdog'):
            self.watchdog.stop()
        
        if hasattr(self, 'sms_webhook'):
            self.sms_webhook.stop()
        
        if hasattr(self, 'backup_manager'):
            self.backup_manager.stop()
        
        if hasattr(self, 'health_endpoint'):
            self.health_endpoint.stop()
        
        if hasattr(self, 'metrics'):
            self.metrics.stop()
        
        # Stop existing components
        if hasattr(self, 'camera') and self.camera:
            self.camera.release()
        
        if hasattr(self, 'buzzer'):
            self.buzzer.cleanup()
        
        if hasattr(self, 'rgb_led'):
            self.rgb_led.cleanup()
        
        if hasattr(self, 'power_button'):
            self.power_button.stop_monitoring()
        
        logger.info("System shutdown complete")
"""

MAIN_LOOP_PATCH = """
            # Send watchdog heartbeat
            if hasattr(self, 'watchdog') and self.watchdog.enabled:
                self.watchdog.heartbeat()
            
            # Update health endpoint with component status
            if hasattr(self, 'health_endpoint') and self.health_endpoint.enabled:
                if hasattr(self, 'camera') and self.camera:
                    self.health_endpoint.update_camera_status({
                        "healthy": True,
                        "frames_captured": getattr(self, 'session_count', 0)
                    })
                
                if hasattr(self, 'watchdog'):
                    self.health_endpoint.update_watchdog_status(self.watchdog.get_status())
                
                if hasattr(self, 'backup_manager'):
                    self.health_endpoint.update_backup_status(self.backup_manager.get_status())
                
                if hasattr(self, 'sms_webhook'):
                    self.health_endpoint.update_sms_webhook_status({
                        "running": self.sms_webhook.running,
                        "total_received": getattr(self.sms_webhook, 'total_received', 0)
                    })
"""


def patch_file():
    """Apply patches to attendance_system.py"""
    file_path = "attendance_system.py"
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        print("📝 Patching attendance_system.py...")
        
        # 1. Add imports after existing imports
        import_marker = "from src.utils import load_config, setup_logger"
        if import_marker in content and IMPORTS_TO_ADD.strip() not in content:
            content = content.replace(
                import_marker,
                import_marker + "\n" + IMPORTS_TO_ADD
            )
            print("✅ Added imports")
        else:
            print("⏭️  Imports already added or marker not found")
        
        # 2. Add initialization code after schedule validator init
        init_marker = '        logger.info("Schedule validator initialized")'
        if init_marker in content and "Phase 3 Robustness Components" not in content:
            content = content.replace(
                init_marker,
                init_marker + "\n" + INIT_CODE_TO_ADD
            )
            print("✅ Added Phase 3 initialization code")
        else:
            print("⏭️  Initialization already added or marker not found")
        
        # 3. Add cleanup method if not exists
        if "def cleanup(self):" not in content:
            # Add before the run method
            run_marker = "    def run(self):"
            if run_marker in content:
                content = content.replace(
                    run_marker,
                    CLEANUP_CODE_TO_ADD + "\n" + run_marker
                )
                print("✅ Added cleanup method")
            else:
                print("⚠️  Could not find run method to add cleanup")
        else:
            print("⏭️  Cleanup method already exists")
        
        # Write patched content
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("\n✅ Patching complete!")
        print("\nNext steps:")
        print("1. Review changes: git diff attendance_system.py")
        print("2. Test system: python attendance_system.py --demo")
        print("3. Check health: curl http://localhost:8080/health")
        print("4. View metrics: cat data/metrics.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Patching failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    patch_file()
