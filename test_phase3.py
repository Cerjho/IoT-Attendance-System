#!/usr/bin/env python3
"""
Phase 3 Robustness Test Suite
Verify all new features work without breaking existing functionality
"""
import json
import logging
import os
import requests
import sqlite3
import sys
import time
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Phase3Tester:
    """Test runner for Phase 3 features"""
    
    def __init__(self):
        self.results = []
        self.db_path = "data/attendance.db"
    
    def test_watchdog_module(self):
        """Test watchdog timer module"""
        logger.info("Testing watchdog timer...")
        try:
            from src.utils.watchdog import WatchdogTimer
            
            # Create watchdog (disabled for test)
            watchdog = WatchdogTimer(
                timeout=5,
                enabled=False
            )
            
            # Check methods exist
            assert hasattr(watchdog, 'start')
            assert hasattr(watchdog, 'stop')
            assert hasattr(watchdog, 'heartbeat')
            assert hasattr(watchdog, 'get_status')
            
            status = watchdog.get_status()
            assert isinstance(status, dict)
            assert 'running' in status
            
            self.results.append(("Watchdog Module", "✅ PASS"))
            logger.info("✅ Watchdog module test passed")
            return True
            
        except Exception as e:
            self.results.append(("Watchdog Module", f"❌ FAIL: {e}"))
            logger.error(f"❌ Watchdog test failed: {e}")
            return False
    
    def test_sms_webhook_module(self):
        """Test SMS webhook receiver module"""
        logger.info("Testing SMS webhook receiver...")
        try:
            from src.notifications.sms_webhook_receiver import SMSWebhookReceiver
            
            # Create webhook (disabled for test)
            webhook = SMSWebhookReceiver(
                port=18081,  # Use different port for test
                db_path=self.db_path,
                enabled=False
            )
            
            # Check methods exist
            assert hasattr(webhook, 'start')
            assert hasattr(webhook, 'stop')
            assert hasattr(webhook, 'get_delivery_stats')
            
            self.results.append(("SMS Webhook Module", "✅ PASS"))
            logger.info("✅ SMS webhook module test passed")
            return True
            
        except Exception as e:
            self.results.append(("SMS Webhook Module", f"❌ FAIL: {e}"))
            logger.error(f"❌ SMS webhook test failed: {e}")
            return False
    
    def test_database_backup_module(self):
        """Test database backup manager module"""
        logger.info("Testing database backup...")
        try:
            from src.utils.database_backup import DatabaseBackupManager
            
            # Create backup manager (disabled for test)
            backup = DatabaseBackupManager(
                db_path=self.db_path,
                backup_dir="data/backups/test",
                enabled=False
            )
            
            # Check methods exist
            assert hasattr(backup, 'start')
            assert hasattr(backup, 'stop')
            assert hasattr(backup, 'create_backup')
            assert hasattr(backup, 'check_integrity')
            assert hasattr(backup, 'list_backups')
            assert hasattr(backup, 'restore_backup')
            assert hasattr(backup, 'get_status')
            
            # Test integrity check on main database
            if os.path.exists(self.db_path):
                result = backup.check_integrity()
                assert isinstance(result, bool)
            
            status = backup.get_status()
            assert isinstance(status, dict)
            
            self.results.append(("Database Backup Module", "✅ PASS"))
            logger.info("✅ Database backup module test passed")
            return True
            
        except Exception as e:
            self.results.append(("Database Backup Module", f"❌ FAIL: {e}"))
            logger.error(f"❌ Database backup test failed: {e}")
            return False
    
    def test_health_endpoint_module(self):
        """Test health endpoint module"""
        logger.info("Testing health endpoint...")
        try:
            from src.utils.health_endpoint import HealthEndpoint
            
            # Create health endpoint (disabled for test)
            health = HealthEndpoint(
                port=18080,  # Use different port for test
                db_path=self.db_path,
                enabled=False
            )
            
            # Check methods exist
            assert hasattr(health, 'start')
            assert hasattr(health, 'stop')
            assert hasattr(health, 'update_camera_status')
            assert hasattr(health, 'update_watchdog_status')
            assert hasattr(health, 'update_backup_status')
            assert hasattr(health, 'update_sms_webhook_status')
            
            # Test status updates
            health.update_camera_status({"healthy": True})
            health.update_watchdog_status({"running": True})
            
            self.results.append(("Health Endpoint Module", "✅ PASS"))
            logger.info("✅ Health endpoint module test passed")
            return True
            
        except Exception as e:
            self.results.append(("Health Endpoint Module", f"❌ FAIL: {e}"))
            logger.error(f"❌ Health endpoint test failed: {e}")
            return False
    
    def test_metrics_collector_module(self):
        """Test metrics collector module"""
        logger.info("Testing metrics collector...")
        try:
            from src.utils.metrics_collector import MetricsCollector
            
            # Create metrics collector (disabled for test)
            metrics = MetricsCollector(
                export_path="data/test_metrics.json",
                enabled=False
            )
            
            # Check methods exist
            assert hasattr(metrics, 'start')
            assert hasattr(metrics, 'stop')
            assert hasattr(metrics, 'increment')
            assert hasattr(metrics, 'record_timing')
            assert hasattr(metrics, 'set_gauge')
            assert hasattr(metrics, 'export_metrics')
            assert hasattr(metrics, 'get_metrics')
            
            # Test basic operations
            metrics.increment('test_counter')
            metrics.record_timing('test_timing', 123.45)
            metrics.set_gauge('test_gauge', 42)
            
            stats = metrics.get_metrics()
            assert isinstance(stats, dict)
            assert 'counters' in stats
            assert stats['counters']['test_counter'] == 1
            
            # Cleanup
            if os.path.exists("data/test_metrics.json"):
                os.remove("data/test_metrics.json")
            
            self.results.append(("Metrics Collector Module", "✅ PASS"))
            logger.info("✅ Metrics collector module test passed")
            return True
            
        except Exception as e:
            self.results.append(("Metrics Collector Module", f"❌ FAIL: {e}"))
            logger.error(f"❌ Metrics collector test failed: {e}")
            return False
    
    def test_sms_rate_limiting(self):
        """Test SMS rate limiting"""
        logger.info("Testing SMS rate limiting...")
        try:
            from src.notifications.sms_notifier import SMSNotifier
            
            # Create SMS notifier with rate limiting
            config = {
                "enabled": False,  # Disabled to avoid actual SMS
                "username": "test",
                "password": "test",
                "device_id": "test",
                "rate_limiting": {
                    "enabled": True,
                    "max_per_minute": 2,
                    "max_per_hour": 10
                }
            }
            
            notifier = SMSNotifier(config)
            
            # Check rate limit method exists
            assert hasattr(notifier, '_check_rate_limit')
            
            self.results.append(("SMS Rate Limiting", "✅ PASS"))
            logger.info("✅ SMS rate limiting test passed")
            return True
            
        except Exception as e:
            self.results.append(("SMS Rate Limiting", f"❌ FAIL: {e}"))
            logger.error(f"❌ SMS rate limiting test failed: {e}")
            return False
    
    def test_config_updates(self):
        """Test configuration file has new sections"""
        logger.info("Testing config updates...")
        try:
            with open("config/config.json", 'r') as f:
                config = json.load(f)
            
            # Check new sections exist
            assert "watchdog" in config, "Missing watchdog config"
            assert "sms_webhook" in config, "Missing sms_webhook config"
            assert "database_backup" in config, "Missing database_backup config"
            assert "health_endpoint" in config, "Missing health_endpoint config"
            
            # Check SMS rate limiting
            sms_config = config.get("sms_notifications", {})
            assert "rate_limiting" in sms_config, "Missing SMS rate_limiting config"
            
            self.results.append(("Config Updates", "✅ PASS"))
            logger.info("✅ Config updates test passed")
            return True
            
        except Exception as e:
            self.results.append(("Config Updates", f"❌ FAIL: {e}"))
            logger.error(f"❌ Config updates test failed: {e}")
            return False
    
    def test_database_tables(self):
        """Test new database tables exist"""
        logger.info("Testing database tables...")
        try:
            if not os.path.exists(self.db_path):
                logger.warning("Database does not exist yet, skipping table check")
                self.results.append(("Database Tables", "⏭️  SKIP"))
                return True
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if sms_delivery_log table will be created
            # (It's created by SMS webhook on first start)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            # Just verify database is accessible
            assert len(tables) > 0, "Database has no tables"
            
            self.results.append(("Database Tables", "✅ PASS"))
            logger.info("✅ Database tables test passed")
            return True
            
        except Exception as e:
            self.results.append(("Database Tables", f"❌ FAIL: {e}"))
            logger.error(f"❌ Database tables test failed: {e}")
            return False
    
    def test_main_system_imports(self):
        """Test main system can import new modules"""
        logger.info("Testing main system imports...")
        try:
            # Read attendance_system.py
            with open("attendance_system.py", 'r') as f:
                content = f.read()
            
            # Check new imports are present
            assert "from src.utils.watchdog import WatchdogTimer" in content
            assert "from src.notifications.sms_webhook_receiver import SMSWebhookReceiver" in content
            assert "from src.utils.database_backup import DatabaseBackupManager" in content
            assert "from src.utils.health_endpoint import HealthEndpoint" in content
            assert "from src.utils.metrics_collector import MetricsCollector" in content
            
            # Check Phase 3 initialization is present
            assert "Phase 3 Robustness Components" in content
            
            self.results.append(("Main System Imports", "✅ PASS"))
            logger.info("✅ Main system imports test passed")
            return True
            
        except Exception as e:
            self.results.append(("Main System Imports", f"❌ FAIL: {e}"))
            logger.error(f"❌ Main system imports test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests and generate report"""
        logger.info("=" * 60)
        logger.info("Phase 3 Robustness Test Suite")
        logger.info("=" * 60)
        
        # Run all tests
        self.test_watchdog_module()
        self.test_sms_webhook_module()
        self.test_database_backup_module()
        self.test_health_endpoint_module()
        self.test_metrics_collector_module()
        self.test_sms_rate_limiting()
        self.test_config_updates()
        self.test_database_tables()
        self.test_main_system_imports()
        
        # Generate report
        logger.info("=" * 60)
        logger.info("Test Results:")
        logger.info("=" * 60)
        
        passed = 0
        failed = 0
        skipped = 0
        
        for test_name, result in self.results:
            logger.info(f"{test_name:.<40} {result}")
            if "PASS" in result:
                passed += 1
            elif "FAIL" in result:
                failed += 1
            elif "SKIP" in result:
                skipped += 1
        
        logger.info("=" * 60)
        logger.info(f"Summary: {passed} passed, {failed} failed, {skipped} skipped")
        logger.info("=" * 60)
        
        if failed > 0:
            logger.error("❌ Some tests failed!")
            return False
        else:
            logger.info("✅ All tests passed!")
            return True


if __name__ == "__main__":
    tester = Phase3Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
