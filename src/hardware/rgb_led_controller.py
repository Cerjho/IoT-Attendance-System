"""
RGB LED Controller for Visual Feedback
Provides color-based visual feedback using RGB LED
"""

import logging
import time
import threading
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger(__name__)

class RGBLEDController:
    """Controls RGB LED for visual feedback using RPi.GPIO with PWM"""
    
    def __init__(self, config: Dict):
        """
        Initialize RGB LED controller
        
        Args:
            config: Dictionary containing RGB LED configuration:
                - enabled: bool (enable/disable RGB LED)
                - gpio_pins: dict (red, green, blue pin numbers)
                - colors: dict (named color patterns)
                - brightness: int (0-100)
                - fade_duration_ms: int (fade in/out duration)
                - hold_duration_ms: int (how long to hold color)
        """
        self.enabled = config.get('enabled', True)
        self.gpio_pins = config.get('gpio_pins', {'red': 11, 'green': 13, 'blue': 15})
        self.colors = config.get('colors', {})
        self.brightness = config.get('brightness', 100) / 100.0  # Convert to 0-1
        self.fade_duration_ms = config.get('fade_duration_ms', 500)
        self.hold_duration_ms = config.get('hold_duration_ms', 2000)
        
        self.gpio_available = False
        self.GPIO = None
        self.pwm_red = None
        self.pwm_green = None
        self.pwm_blue = None
        self._lock = threading.Lock()
        self._active_thread = None
        self._cleaned_up = False
        
        if self.enabled:
            self._initialize_gpio()
    
    def _initialize_gpio(self):
        """Initialize GPIO for RGB LED control with PWM"""
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)
            self.GPIO.setwarnings(False)
            
            # Setup GPIO pins for RGB LED
            self.GPIO.setup(self.gpio_pins['red'], GPIO.OUT)
            self.GPIO.setup(self.gpio_pins['green'], GPIO.OUT)
            self.GPIO.setup(self.gpio_pins['blue'], GPIO.OUT)
            
            # Setup PWM on each pin (1000 Hz frequency)
            self.pwm_red = self.GPIO.PWM(self.gpio_pins['red'], 1000)
            self.pwm_green = self.GPIO.PWM(self.gpio_pins['green'], 1000)
            self.pwm_blue = self.GPIO.PWM(self.gpio_pins['blue'], 1000)
            
            # Start PWM with 0% duty cycle (off)
            self.pwm_red.start(0)
            self.pwm_green.start(0)
            self.pwm_blue.start(0)
            
            self.gpio_available = True
            logger.info(f"RGB LED initialized on GPIO pins R:{self.gpio_pins['red']}, "
                       f"G:{self.gpio_pins['green']}, B:{self.gpio_pins['blue']}")
        except ImportError:
            logger.warning("RPi.GPIO not available - RGB LED disabled (software-only mode)")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize GPIO for RGB LED: {e}")
            self.enabled = False
    
    def set_color(self, red: int, green: int, blue: int, brightness: Optional[float] = None):
        """
        Set RGB LED to specific color
        
        Args:
            red: Red value (0-255)
            green: Green value (0-255)
            blue: Blue value (0-255)
            brightness: Optional brightness multiplier (0-1), uses config default if None
        """
        if not self.enabled or not self.gpio_available:
            return
        
        brightness = brightness if brightness is not None else self.brightness
        
        try:
            # Convert 0-255 to 0-100 duty cycle, apply brightness
            duty_red = (red / 255.0) * 100 * brightness
            duty_green = (green / 255.0) * 100 * brightness
            duty_blue = (blue / 255.0) * 100 * brightness
            
            self.pwm_red.ChangeDutyCycle(duty_red)
            self.pwm_green.ChangeDutyCycle(duty_green)
            self.pwm_blue.ChangeDutyCycle(duty_blue)
            
        except Exception as e:
            logger.error(f"Error setting RGB LED color: {e}")
    
    def fade_to_color(self, target_red: int, target_green: int, target_blue: int, 
                      duration_ms: int = None):
        """
        Fade from current color to target color
        
        Args:
            target_red: Target red value (0-255)
            target_green: Target green value (0-255)
            target_blue: Target blue value (0-255)
            duration_ms: Fade duration in milliseconds
        """
        if not self.enabled or not self.gpio_available:
            return
        
        duration_ms = duration_ms if duration_ms is not None else self.fade_duration_ms
        steps = 50  # Number of fade steps
        step_delay = duration_ms / 1000.0 / steps
        
        # Get current duty cycles (approximate current color)
        current_red = (self.pwm_red.ChangeFrequency(1000) or 0) * 255 / 100
        current_green = (self.pwm_green.ChangeFrequency(1000) or 0) * 255 / 100
        current_blue = (self.pwm_blue.ChangeFrequency(1000) or 0) * 255 / 100
        
        # Calculate step increments
        red_step = (target_red - current_red) / steps
        green_step = (target_green - current_green) / steps
        blue_step = (target_blue - current_blue) / steps
        
        # Fade in steps
        for i in range(steps):
            r = int(current_red + (red_step * i))
            g = int(current_green + (green_step * i))
            b = int(current_blue + (blue_step * i))
            self.set_color(r, g, b)
            time.sleep(step_delay)
        
        # Ensure final color is exact
        self.set_color(target_red, target_green, target_blue)
    
    def show_color(self, color_name: str, fade: bool = True, blocking: bool = False):
        """
        Show a named color from config
        
        Args:
            color_name: Name of color (e.g., 'success', 'error', 'qr_detected')
            fade: If True, fade to color; if False, instant change
            blocking: If True, wait for hold duration to complete
        """
        if not self.enabled:
            return
        
        if color_name not in self.colors:
            logger.warning(f"Unknown RGB LED color: {color_name}")
            return
        
        color = self.colors[color_name]
        if len(color) != 3:
            logger.error(f"Invalid color format for {color_name}: {color}")
            return
        
        if blocking:
            self._show_color_pattern(color, fade)
        else:
            # Cancel any active thread
            if self._active_thread and self._active_thread.is_alive():
                # Let it finish naturally, start new one
                pass
            
            # Show in separate thread
            thread = threading.Thread(target=self._show_color_pattern, args=(color, fade))
            thread.daemon = True
            self._active_thread = thread
            thread.start()
    
    def _show_color_pattern(self, color: List[int], fade: bool):
        """Internal method to show color pattern with fade and hold"""
        with self._lock:
            try:
                red, green, blue = color
                
                # Fade to color or instant change
                if fade:
                    self.fade_to_color(red, green, blue, self.fade_duration_ms)
                else:
                    self.set_color(red, green, blue)
                
                # Hold the color
                time.sleep(self.hold_duration_ms / 1000.0)
                
                # Fade out to off
                if fade:
                    self.fade_to_color(0, 0, 0, self.fade_duration_ms)
                else:
                    self.set_color(0, 0, 0)
                    
            except Exception as e:
                logger.error(f"Error showing RGB LED color pattern: {e}")
    
    def blink(self, color: List[int], times: int = 3, on_time_ms: int = 200, 
              off_time_ms: int = 200):
        """
        Blink LED with specific color
        
        Args:
            color: RGB color [r, g, b] (0-255 each)
            times: Number of blinks
            on_time_ms: Time LED is on (milliseconds)
            off_time_ms: Time LED is off (milliseconds)
        """
        if not self.enabled or not self.gpio_available:
            return
        
        def blink_pattern():
            with self._lock:
                try:
                    for _ in range(times):
                        self.set_color(*color)
                        time.sleep(on_time_ms / 1000.0)
                        self.set_color(0, 0, 0)
                        time.sleep(off_time_ms / 1000.0)
                except Exception as e:
                    logger.error(f"Error blinking RGB LED: {e}")
        
        thread = threading.Thread(target=blink_pattern)
        thread.daemon = True
        thread.start()
    
    def pulse(self, color: List[int], duration_ms: int = 2000, cycles: int = 2):
        """
        Pulse LED (breathing effect)
        
        Args:
            color: RGB color [r, g, b] (0-255 each)
            duration_ms: Duration of one pulse cycle
            cycles: Number of pulse cycles
        """
        if not self.enabled or not self.gpio_available:
            return
        
        def pulse_pattern():
            with self._lock:
                try:
                    steps = 50
                    step_delay = duration_ms / 1000.0 / steps / 2
                    
                    for _ in range(cycles):
                        # Fade in
                        for i in range(steps):
                            brightness = i / steps
                            self.set_color(*color, brightness=brightness * self.brightness)
                            time.sleep(step_delay)
                        
                        # Fade out
                        for i in range(steps, 0, -1):
                            brightness = i / steps
                            self.set_color(*color, brightness=brightness * self.brightness)
                            time.sleep(step_delay)
                    
                    self.set_color(0, 0, 0)
                    
                except Exception as e:
                    logger.error(f"Error pulsing RGB LED: {e}")
        
        thread = threading.Thread(target=pulse_pattern)
        thread.daemon = True
        thread.start()
    
    def off(self):
        """Turn off RGB LED immediately"""
        if self.enabled and self.gpio_available:
            self.set_color(0, 0, 0)
    
    def cleanup(self):
        """Clean up GPIO resources"""
        if self.gpio_available and not self._cleaned_up:
            try:
                self._cleaned_up = True
                
                # Stop PWM
                if self.pwm_red:
                    self.pwm_red.stop()
                if self.pwm_green:
                    self.pwm_green.stop()
                if self.pwm_blue:
                    self.pwm_blue.stop()
                
                # Turn off LEDs
                self.GPIO.output(self.gpio_pins['red'], self.GPIO.LOW)
                self.GPIO.output(self.gpio_pins['green'], self.GPIO.LOW)
                self.GPIO.output(self.gpio_pins['blue'], self.GPIO.LOW)
                
                # Cleanup GPIO
                self.GPIO.cleanup([
                    self.gpio_pins['red'],
                    self.gpio_pins['green'],
                    self.gpio_pins['blue']
                ])
                
                logger.info("RGB LED GPIO cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up RGB LED GPIO: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
