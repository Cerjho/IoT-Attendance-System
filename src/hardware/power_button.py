#!/usr/bin/env python3
"""
Power Button Controller
Handles safe shutdown and power on for Raspberry Pi
GPIO 3 (Pin 5) → Button → GND (Pin 6)
"""

import time
import os
import logging
import threading

logger = logging.getLogger(__name__)


class PowerButtonController:
    """
    Controls power button for safe shutdown
    
    Features:
    - Short press (< 3s): Safe shutdown
    - Long press (> 5s): Force shutdown
    - Uses GPIO 3 which can wake Pi from halt state
    """
    
    def __init__(self, config: dict):
        """
        Initialize power button controller
        
        Args:
            config: Power button configuration
        """
        self.enabled = config.get('enabled', True)
        self.gpio_pin = config.get('gpio_pin', 3)  # GPIO 3 for wake capability
        self.short_press_time = config.get('short_press_seconds', 3)
        self.long_press_time = config.get('long_press_seconds', 5)
        self.debounce_time = config.get('debounce_ms', 50)
        
        self._monitoring = False
        self._monitor_thread = None
        self._cleanup_done = False
        self.gpio_available = False
        self.GPIO = None
        
        if self.enabled:
            self._initialize_gpio()
    
    def _initialize_gpio(self):
        """Initialize GPIO for power button"""
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)
            self.GPIO.setwarnings(False)
            
            # Setup with internal pull-up resistor
            # Button connects GPIO 3 to GND when pressed
            self.GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            self.gpio_available = True
            logger.info(f"✅ Power button initialized on GPIO {self.gpio_pin}")
            logger.info("   Short press (< 3s): Safe shutdown")
            logger.info("   Long press (> 5s): Force shutdown")
        except ImportError:
            logger.warning("RPi.GPIO not available - power button disabled")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize power button: {e}")
            self.enabled = False
    
    def start_monitoring(self):
        """Start monitoring power button in background thread"""
        if not self.enabled or not self.gpio_available:
            return
        
        if self._monitoring:
            logger.warning("Power button monitoring already running")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_button, daemon=True)
        self._monitor_thread.start()
        logger.info("🔘 Power button monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring power button"""
        if self._monitoring:
            self._monitoring = False
            if self._monitor_thread:
                self._monitor_thread.join(timeout=2)
            logger.info("Power button monitoring stopped")
    
    def _monitor_button(self):
        """Monitor button presses in background thread"""
        try:
            while self._monitoring:
                # Wait for button press (GPIO goes LOW when pressed)
                if self.GPIO.input(self.gpio_pin) == self.GPIO.LOW:
                    # Debounce
                    time.sleep(self.debounce_time / 1000.0)
                    
                    if self.GPIO.input(self.gpio_pin) == self.GPIO.LOW:
                        self._handle_button_press()
                
                time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Error in power button monitoring: {e}")
    
    def _handle_button_press(self):
        """Handle button press event"""
        press_start = time.time()
        logger.info("🔘 Power button pressed...")
        
        # Wait for button release or timeout
        while self.GPIO.input(self.gpio_pin) == self.GPIO.LOW:
            press_duration = time.time() - press_start
            
            # Long press - force shutdown
            if press_duration >= self.long_press_time:
                logger.warning(f"⚠️  LONG PRESS ({press_duration:.1f}s) - FORCE SHUTDOWN!")
                self._shutdown(force=True)
                return
            
            time.sleep(0.1)
        
        # Button released - calculate press duration
        press_duration = time.time() - press_start
        
        # Short press - safe shutdown
        if press_duration < self.short_press_time:
            logger.info(f"✅ Short press ({press_duration:.1f}s) - SAFE SHUTDOWN")
            self._shutdown(force=False)
        else:
            logger.info(f"⏱️  Press duration: {press_duration:.1f}s")
    
    def _shutdown(self, force: bool = False):
        """
        Perform system shutdown
        
        Args:
            force: If True, force immediate shutdown
        """
        try:
            if force:
                logger.warning("🔴 FORCE SHUTDOWN - Immediate halt!")
                os.system("sudo shutdown -h now")
            else:
                logger.info("🔵 SAFE SHUTDOWN - Closing applications...")
                # Give time for cleanup
                time.sleep(1)
                os.system("sudo shutdown -h now")
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def cleanup(self):
        """Cleanup GPIO resources"""
        if self._cleanup_done or not self.gpio_available:
            return
        
        try:
            self.stop_monitoring()
            
            if self.GPIO:
                self.GPIO.cleanup(self.gpio_pin)
                logger.info("Power button GPIO cleaned up")
            
            self._cleanup_done = True
        
        except Exception as e:
            logger.error(f"Error cleaning up power button GPIO: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()


def test_power_button():
    """Test power button functionality"""
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("POWER BUTTON TEST")
    print("=" * 70)
    print()
    print("Wiring:")
    print("  Button Pin 1 → GPIO 3 (Physical Pin 5)")
    print("  Button Pin 2 → GND (Physical Pin 6)")
    print()
    print("Test:")
    print("  Short press (< 3s): Safe shutdown")
    print("  Long press (> 5s): Force shutdown")
    print()
    print("Press Ctrl+C to cancel test (no actual shutdown)")
    print("=" * 70)
    print()
    
    config = {
        'enabled': True,
        'gpio_pin': 3,
        'short_press_seconds': 3,
        'long_press_seconds': 5,
        'debounce_ms': 50
    }
    
    button = PowerButtonController(config)
    
    if not button.gpio_available:
        print("ERROR: GPIO not available")
        return
    
    try:
        print("Monitoring power button... Press the button to test")
        print("(Shutdown commands disabled for testing)")
        print()
        
        import RPi.GPIO as GPIO
        
        while True:
            if GPIO.input(3) == GPIO.LOW:
                print("🔘 Button pressed!")
                press_start = time.time()
                
                while GPIO.input(3) == GPIO.LOW:
                    duration = time.time() - press_start
                    print(f"   Holding: {duration:.1f}s", end='\r')
                    time.sleep(0.1)
                
                duration = time.time() - press_start
                print(f"\n   Released after {duration:.1f}s")
                
                if duration < 3:
                    print("   ✅ Short press detected - Would shutdown safely")
                elif duration >= 5:
                    print("   ⚠️  Long press detected - Would force shutdown")
                else:
                    print("   ⏱️  Medium press")
                
                print()
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\nTest cancelled")
    
    finally:
        button.cleanup()
        print("Cleanup complete")


if __name__ == "__main__":
    test_power_button()
