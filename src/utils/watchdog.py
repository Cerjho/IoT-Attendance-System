#!/usr/bin/env python3
"""
Watchdog Timer for System Health Monitoring
Prevents system hangs by monitoring heartbeat and triggering restart if timeout occurs
"""
import logging
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class WatchdogTimer:
    """
    Watchdog timer to detect system hangs and trigger recovery
    
    Usage:
        watchdog = WatchdogTimer(timeout=30)
        watchdog.start()
        
        # In main loop:
        watchdog.heartbeat()  # Reset timer
        
        # On shutdown:
        watchdog.stop()
    """

    def __init__(
        self,
        timeout: int = 30,
        restart_command: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Initialize watchdog timer
        
        Args:
            timeout: Seconds without heartbeat before triggering restart
            restart_command: Command to execute on timeout (default: systemctl restart)
            enabled: Enable/disable watchdog
        """
        self.timeout = timeout
        self.restart_command = restart_command or "sudo systemctl restart attendance-system"
        self.enabled = enabled
        
        self.last_heartbeat = time.time()
        self.running = False
        self.thread = None
        
        if self.enabled:
            logger.info(f"Watchdog timer initialized: timeout={timeout}s")
        else:
            logger.info("Watchdog timer disabled")

    def start(self):
        """Start watchdog monitoring thread"""
        if not self.enabled:
            logger.debug("Watchdog disabled, not starting")
            return
        
        if self.running:
            logger.warning("Watchdog already running")
            return
        
        self.running = True
        self.last_heartbeat = time.time()
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
        logger.info("Watchdog timer started")

    def stop(self):
        """Stop watchdog monitoring"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Watchdog timer stopped")

    def heartbeat(self):
        """Reset watchdog timer (call this regularly in main loop)"""
        self.last_heartbeat = time.time()
        logger.debug("Watchdog heartbeat received")

    def _monitor(self):
        """Monitor loop - runs in background thread"""
        logger.info("Watchdog monitoring started")
        
        while self.running:
            try:
                time.sleep(5)  # Check every 5 seconds
                
                elapsed = time.time() - self.last_heartbeat
                
                if elapsed > self.timeout:
                    logger.critical(
                        f"⚠️ WATCHDOG TIMEOUT! No heartbeat for {elapsed:.1f}s "
                        f"(timeout: {self.timeout}s)"
                    )
                    logger.critical("System appears hung, initiating recovery...")
                    
                    self._trigger_restart()
                    break
                
                elif elapsed > self.timeout * 0.7:
                    # Warning at 70% of timeout
                    logger.warning(
                        f"Watchdog warning: {elapsed:.1f}s since last heartbeat "
                        f"({(elapsed/self.timeout)*100:.0f}% of timeout)"
                    )
                
            except Exception as e:
                logger.error(f"Watchdog monitor error: {e}")
                time.sleep(1)
        
        logger.info("Watchdog monitoring stopped")

    def _trigger_restart(self):
        """Trigger system restart"""
        try:
            logger.critical(f"Executing restart command: {self.restart_command}")
            
            # Log to file before restart
            try:
                with open("data/logs/watchdog_restarts.log", "a") as f:
                    f.write(
                        f"{datetime.now().isoformat()} - Watchdog triggered restart "
                        f"(timeout: {self.timeout}s)\n"
                    )
            except Exception as e:
                logger.error(f"Failed to log restart: {e}")
            
            # Execute restart command
            subprocess.Popen(
                self.restart_command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
        except Exception as e:
            logger.critical(f"Failed to execute restart command: {e}")

    def get_status(self) -> dict:
        """Get watchdog status"""
        elapsed = time.time() - self.last_heartbeat
        return {
            "enabled": self.enabled,
            "running": self.running,
            "timeout_seconds": self.timeout,
            "elapsed_since_heartbeat": round(elapsed, 2),
            "timeout_percentage": round((elapsed / self.timeout) * 100, 1) if self.timeout > 0 else 0,
            "last_heartbeat": datetime.fromtimestamp(self.last_heartbeat).isoformat()
        }
