"""
Buzzer Controller for Audio Feedback
Provides pattern-based buzzer control for user interaction feedback
"""

import logging
import time
import threading
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class BuzzerController:
    """Controls buzzer for audio feedback using RPi.GPIO"""
    
    def __init__(self, config: Dict):
        """
        Initialize buzzer controller
        
        Args:
            config: Dictionary containing buzzer configuration:
                - enabled: bool (enable/disable buzzer)
                - gpio_pin: int (BCM pin number)
                - patterns: dict (named patterns with timing)
        """
        self.enabled = config.get('enabled', True)
        self.gpio_pin = config.get('gpio_pin', 17)
        self.patterns = config.get('patterns', {})
        self.gpio_available = False
        self.GPIO = None
        self._lock = threading.Lock()
        self._cleaned_up = False
        
        if self.enabled:
            self._initialize_gpio()
    
    def _initialize_gpio(self):
        """Initialize GPIO for buzzer control"""
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)
            self.GPIO.setwarnings(False)
            self.GPIO.setup(self.gpio_pin, GPIO.OUT)
            self.GPIO.output(self.gpio_pin, GPIO.LOW)
            self.gpio_available = True
            logger.info(f"Buzzer initialized on GPIO pin {self.gpio_pin}")
        except ImportError:
            logger.warning("RPi.GPIO not available - buzzer disabled (software-only mode)")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize GPIO for buzzer: {e}")
            self.enabled = False
    
    def beep_pattern(self, pattern: List[int], blocking: bool = False):
        """
        Play a beep pattern
        
        Args:
            pattern: List of milliseconds [on, off, on, off, ...]
            blocking: If True, wait for pattern to complete
        """
        if not self.enabled or not self.gpio_available:
            return
        
        if blocking:
            self._play_pattern(pattern)
        else:
            # Play in separate thread to avoid blocking
            thread = threading.Thread(target=self._play_pattern, args=(pattern,))
            thread.daemon = True
            thread.start()
    
    def _play_pattern(self, pattern: List[int]):
        """Internal method to play pattern with GPIO control"""
        with self._lock:
            try:
                for i, duration_ms in enumerate(pattern):
                    if duration_ms <= 0:
                        continue
                    
                    # Alternate between HIGH (odd indices) and LOW (even indices)
                    # Pattern format: [on, off, on, off, ...]
                    if i % 2 == 0:  # Even index = buzzer ON
                        self.GPIO.output(self.gpio_pin, self.GPIO.HIGH)
                    else:  # Odd index = buzzer OFF
                        self.GPIO.output(self.gpio_pin, self.GPIO.LOW)
                    
                    time.sleep(duration_ms / 1000.0)
                
                # Ensure buzzer is off after pattern
                self.GPIO.output(self.gpio_pin, self.GPIO.LOW)
                
            except Exception as e:
                logger.error(f"Error playing buzzer pattern: {e}")
    
    def beep(self, pattern_name: str, blocking: bool = False):
        """
        Play a named pattern from config
        
        Args:
            pattern_name: Name of pattern (e.g., 'qr_detected', 'success', 'error')
            blocking: If True, wait for pattern to complete
        """
        if not self.enabled:
            return
        
        if pattern_name in self.patterns:
            pattern = self.patterns[pattern_name]
            self.beep_pattern(pattern, blocking)
        else:
            logger.warning(f"Unknown buzzer pattern: {pattern_name}")
    
    def beep_simple(self, duration_ms: int = 100):
        """
        Simple single beep
        
        Args:
            duration_ms: Duration of beep in milliseconds
        """
        self.beep_pattern([duration_ms], blocking=False)
    
    def cleanup(self):
        """Clean up GPIO resources"""
        if self.gpio_available and self.GPIO and not self._cleaned_up:
            try:
                self._cleaned_up = True
                self.GPIO.output(self.gpio_pin, self.GPIO.LOW)
                self.GPIO.cleanup(self.gpio_pin)
                logger.info("Buzzer GPIO cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up buzzer GPIO: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
