#!/usr/bin/env python3
"""
Production Monitoring Script
Monitors system health and sends alerts if issues detected
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.config_loader import ConfigLoader
from src.utils.logging_factory import get_logger
from src.utils.audit_logger import get_business_logger

logger = get_logger(__name__)
business_logger = get_business_logger()


class ProductionMonitor:
    """Monitor production system health."""
    
    def __init__(self, config_path="config/config.json"):
        self.config = ConfigLoader(config_path).config
        self.db_path = "data/attendance.db"
        self.alerts = []
    
    def check_database(self):
        """Check database health."""
        logger.info("Checking database...")
        
        if not Path(self.db_path).exists():
            self.alerts.append("❌ Database file missing")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM attendance 
                WHERE timestamp > datetime('now', '-24 hours')
            """)
            recent_count = cursor.fetchone()[0]
            logger.info(f"Recent attendance records (24h): {recent_count}")
            
            # Check sync queue (if table exists)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_queue'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM sync_queue")
                queue_size = cursor.fetchone()[0]
            else:
                queue_size = 0
                logger.info("Sync queue table not found (system may not have run yet)")
            
            if queue_size > 100:
                self.alerts.append(f"⚠️  Large sync queue: {queue_size} records")
            else:
                logger.info(f"Sync queue: {queue_size} records")
            
            conn.close()
            return True
            
        except Exception as e:
            self.alerts.append(f"❌ Database error: {e}")
            return False
    
    def check_disk_space(self):
        """Check disk space."""
        logger.info("Checking disk space...")
        
        import shutil
        stat = shutil.disk_usage(".")
        
        free_gb = stat.free / (1024**3)
        percent_used = (stat.used / stat.total) * 100
        
        logger.info(f"Disk space: {free_gb:.1f}GB free ({percent_used:.1f}% used)")
        
        if percent_used > 90:
            self.alerts.append(f"❌ Disk space critical: {percent_used:.1f}% used")
        elif percent_used > 80:
            self.alerts.append(f"⚠️  Disk space high: {percent_used:.1f}% used")
    
    def check_logs(self):
        """Check recent logs for errors."""
        logger.info("Checking logs...")
        
        log_file = Path("data/logs/system.log")
        if not log_file.exists():
            logger.info("No system log found")
            return
        
        # Check last 1000 lines for errors
        try:
            with open(log_file) as f:
                lines = f.readlines()[-1000:]
            
            error_count = sum(1 for line in lines if "ERROR" in line)
            warning_count = sum(1 for line in lines if "WARNING" in line)
            
            logger.info(f"Recent log analysis: {error_count} errors, {warning_count} warnings")
            
            if error_count > 10:
                self.alerts.append(f"⚠️  High error count: {error_count} errors in recent logs")
            
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
    
    def check_connectivity(self):
        """Check network connectivity."""
        logger.info("Checking connectivity...")
        
        import requests
        
        try:
            # Check Supabase
            url = self.config.get("cloud", {}).get("url")
            if url and not url.startswith("${"):
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Supabase reachable")
                else:
                    self.alerts.append(f"⚠️  Supabase returned HTTP {response.status_code}")
            
        except requests.RequestException as e:
            self.alerts.append(f"⚠️  Network issue: {str(e)[:50]}")
    
    def check_services(self):
        """Check service status."""
        logger.info("Checking services...")
        
        import subprocess
        
        services = ["attendance-dashboard", "attendance-system"]
        
        for service in services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True
                )
                
                if result.stdout.strip() == "active":
                    logger.info(f"✅ {service} active")
                else:
                    self.alerts.append(f"❌ {service} not running")
                    
            except Exception as e:
                logger.warning(f"Could not check {service}: {e}")
    
    def save_report(self):
        """Save monitoring report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if not self.alerts else "issues",
            "alerts": self.alerts
        }
        
        report_file = Path("data/logs/monitoring_report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {report_file}")
    
    def run(self):
        """Run all checks."""
        logger.info("=" * 60)
        logger.info("PRODUCTION MONITORING")
        logger.info("=" * 60)
        
        self.check_services()
        self.check_database()
        self.check_disk_space()
        self.check_connectivity()
        self.check_logs()
        
        self.save_report()
        
        # Summary
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        
        if not self.alerts:
            logger.info("✅ All checks passed - System healthy")
            return 0
        else:
            logger.warning(f"⚠️  {len(self.alerts)} issue(s) detected:")
            for alert in self.alerts:
                logger.warning(f"  {alert}")
            return 1


if __name__ == "__main__":
    monitor = ProductionMonitor()
    sys.exit(monitor.run())
