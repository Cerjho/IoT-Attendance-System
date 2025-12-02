"""
Camera Handler Module - Bookworm/Picamera2 Version
Manages camera for Raspberry Pi OS Bookworm using libcamera
"""

import logging
import time
from datetime import datetime
from typing import Optional, Tuple

import cv2
import numpy as np

# Try to import picamera2 for Bookworm support
try:
    from picamera2 import Picamera2

    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

logger = logging.getLogger(__name__)


class CameraHandler:
    """
    Handles camera operations for IoT attendance system.
    Supports both legacy OpenCV and modern Picamera2 (Bookworm).
    """

    def __init__(
        self,
        camera_index: int = 0,
        resolution: Tuple[int, int] = (640, 480),
        controls: Optional[dict] = None,
        still_settle_ms: int = 700,
        max_init_retries: int = 3,
        init_retry_delay: int = 5,
        health_check_interval: int = 30,
    ):
        """
        Initialize camera handler.

        Args:
            camera_index: Camera device index (default: 0 for primary camera)
            resolution: Tuple of (width, height) for camera resolution
            max_init_retries: Max attempts to initialize camera
            init_retry_delay: Seconds between init retries
            health_check_interval: Seconds between health checks
        """
        self.camera_index = camera_index
        self.resolution = resolution
        self.cap = None
        self.picam2 = None
        self.is_open = False
        self.frame_count = 0
        self.last_frame_time = None
        self.use_picamera2 = PICAMERA2_AVAILABLE
        self.controls = controls or {}
        self.full_still_size: Optional[Tuple[int, int]] = None
        self.still_settle_ms = still_settle_ms
        
        # Recovery parameters
        self.max_init_retries = max_init_retries
        self.init_retry_delay = init_retry_delay
        self.health_check_interval = health_check_interval
        self.last_health_check = None
        self.consecutive_failures = 0
        self.recovery_mode = False

    def start(self) -> bool:
        """
        Start camera capture with retry logic.

        Returns:
            bool: True if camera started successfully, False otherwise
        """
        for attempt in range(1, self.max_init_retries + 1):
            logger.info(f"Camera init attempt {attempt}/{self.max_init_retries}")
            
            if self._start_internal():
                self.consecutive_failures = 0
                self.recovery_mode = False
                return True
            
            if attempt < self.max_init_retries:
                logger.warning(f"Camera init failed, retrying in {self.init_retry_delay}s...")
                time.sleep(self.init_retry_delay)
        
        logger.error(f"Camera failed to initialize after {self.max_init_retries} attempts")
        self.recovery_mode = True
        return False

    def _start_internal(self) -> bool:
        """
        Internal camera start implementation.

        Returns:
            bool: True if camera started successfully, False otherwise
        """
        # Try Picamera2 first (for Bookworm)
        print(f"DEBUG: Camera init: use_picamera2={self.use_picamera2}, PICAMERA2_AVAILABLE={PICAMERA2_AVAILABLE}")
        logger.info(f"Camera init: use_picamera2={self.use_picamera2}, PICAMERA2_AVAILABLE={PICAMERA2_AVAILABLE}")
        if self.use_picamera2 and PICAMERA2_AVAILABLE:
            try:
                logger.info("Attempting to start camera with Picamera2 (libcamera)...")
                self.picam2 = Picamera2()

                # Determine largest sensor mode for high-res still capture
                try:
                    modes = getattr(self.picam2, "sensor_modes", [])
                    if modes:
                        self.full_still_size = max(
                            modes, key=lambda m: m["size"][0] * m["size"][1]
                        )["size"]
                except Exception:
                    self.full_still_size = None

                # Configure preview
                config = self.picam2.create_preview_configuration(
                    main={"size": self.resolution, "format": "RGB888"}
                )
                self.preview_config = config
                self.picam2.configure(self.preview_config)

                # Start camera
                self.picam2.start()

                # Warmup period
                logger.info("Warming up camera...")
                time.sleep(2)

                # Apply optional controls before first capture (Picamera2)
                self._apply_initial_controls()
                # Test frame capture
                frame = self.picam2.capture_array()
                if frame is not None and frame.size > 0:
                    self.is_open = True
                    logger.info(
                        f"✓✓✓ Camera started successfully with Picamera2! Resolution: {frame.shape}"
                    )
                    return True
                else:
                    logger.error("Camera started but frame is empty")
                    self.picam2.stop()
                    self.picam2 = None

            except Exception as e:
                logger.warning(f"Picamera2 failed: {str(e)}, falling back to OpenCV...")
                if self.picam2:
                    try:
                        self.picam2.stop()
                    except:
                        pass
                    self.picam2 = None
                self.use_picamera2 = False

        # Fallback to OpenCV (legacy)
        try:
            logger.info("Attempting to start camera with OpenCV (V4L2)...")
            # Explicitly use V4L2 backend for better systemd compatibility
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)

            if not self.cap.isOpened():
                logger.error(f"Failed to open camera at index {self.camera_index}")
                return False

            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Warmup period
            logger.info(f"Warming up camera {self.camera_index}...")
            success_count = 0
            max_attempts = 10

            for i in range(max_attempts):
                try:
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        success_count += 1
                        logger.debug(f"Warmup frame {i+1}: Success")
                    time.sleep(0.2)
                except Exception as e:
                    logger.debug(f"Warmup frame {i+1}: Exception - {str(e)}")
                    time.sleep(0.2)

            if success_count == 0:
                logger.error(
                    f"Camera {self.camera_index} opened but cannot read frames"
                )
                self.cap.release()
                self.cap = None
                return False

            self.is_open = True
            logger.info(
                f"Camera {self.camera_index} started with OpenCV ({success_count}/{max_attempts} frames)"
            )
            return True

        except Exception as e:
            logger.error(f"Error starting camera: {str(e)}")
            return False

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Capture and return a single frame from camera with health checks.

        Returns:
            np.ndarray: Frame from camera (BGR format), or None if capture failed
        """
        # Periodic health check
        self._check_health()
        
        if not self.is_open:
            if self.recovery_mode:
                # Attempt recovery
                logger.info("Attempting camera recovery...")
                if self.start():
                    logger.info("Camera recovery successful")
                else:
                    return None
            else:
                logger.warning("Camera is not open")
                return None

        try:
            # Use Picamera2
            if self.use_picamera2 and self.picam2:
                frame = self.picam2.capture_array()
                if frame is not None and frame.size > 0:
                    # Convert RGB to BGR for OpenCV compatibility
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    self.frame_count += 1
                    self.last_frame_time = datetime.now()
                    self.consecutive_failures = 0
                    return frame_bgr
                else:
                    logger.warning("Failed to capture frame from Picamera2")
                    self._on_frame_failure()
                    return None

            # Use OpenCV
            elif self.cap is not None:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Failed to read frame from OpenCV")
                    self._on_frame_failure()
                    return None

                self.frame_count += 1
                self.last_frame_time = datetime.now()
                self.consecutive_failures = 0
                return frame

            else:
                logger.error("No camera backend available")
                return None

        except Exception as e:
            logger.error(f"Error capturing frame: {str(e)}")
            self._on_frame_failure()
            return None

    def capture_still_array(
        self, size: Optional[Tuple[int, int]] = None
    ) -> Optional[np.ndarray]:
        """Capture a high-resolution still image (Picamera2 only) and return BGR array."""
        if not (self.use_picamera2 and self.picam2):
            return None
        try:
            still_size = size or self.full_still_size or self.resolution
            still_config = self.picam2.create_still_configuration(
                main={"size": still_size, "format": "RGB888"}
            )
            # Switch to still mode
            self.picam2.stop()
            self.picam2.configure(still_config)
            self.picam2.start()
            # Allow 3A to settle
            time.sleep(self.still_settle_ms / 1000.0)
            arr_rgb = self.picam2.capture_array()
            # Return to preview
            self.picam2.stop()
            self.picam2.configure(self.preview_config)
            self.picam2.start()
            if arr_rgb is None or arr_rgb.size == 0:
                return None
            return cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.warning(f"High-res still capture failed: {e}")
            # Try to ensure preview is running again
            try:
                self.picam2.configure(self.preview_config)
                self.picam2.start()
            except Exception:
                pass
            return None

    # ---------------- Picamera2 Control Helpers -----------------
    def _apply_initial_controls(self):
        """Apply exposure / AWB controls if provided in self.controls."""
        if not (self.use_picamera2 and self.picam2 and self.controls):
            return
        try:
            ctrl_dict = {}
            exposure_cfg = self.controls.get("exposure", {})
            awb_cfg = self.controls.get("awb", {})
            # Exposure mode: if manual requested, set ExposureTime & AnalogueGain
            mode = exposure_cfg.get("mode", "auto")
            if isinstance(mode, str) and mode.lower() == "manual":
                try:
                    exp_us = int(float(exposure_cfg.get("manual_exposure_us", 10000)))
                    gain = float(exposure_cfg.get("manual_analogue_gain", 1.0))
                    ctrl_dict["ExposureTime"] = exp_us
                    ctrl_dict["AnalogueGain"] = gain
                    ctrl_dict["AeEnable"] = False
                except Exception as conv_err:
                    logger.warning(
                        f"Invalid manual exposure/gain values, skipping manual exposure: {conv_err}"
                    )
            else:
                ctrl_dict["AeEnable"] = True
            # AWB mode: only set if provided as integer enum; skip strings to avoid cast errors
            awb_mode = awb_cfg.get("mode", None)
            if isinstance(awb_mode, int):
                ctrl_dict["AwbMode"] = awb_mode
            # Manual colour gains (disable AWB if provided and valid)
            colour_gains = awb_cfg.get("colour_gains")
            if isinstance(colour_gains, (list, tuple)) and len(colour_gains) == 2:
                try:
                    r_gain = float(colour_gains[0])
                    b_gain = float(colour_gains[1])
                    ctrl_dict["AwbEnable"] = False
                    ctrl_dict["ColourGains"] = (r_gain, b_gain)
                except Exception:
                    logger.warning("Invalid colour_gains provided; ignoring.")
            elif "AwbEnable" not in ctrl_dict:
                ctrl_dict["AwbEnable"] = True
            # Apply controls if any
            if ctrl_dict:
                self.picam2.set_controls(ctrl_dict)
                logger.info(f"Applied Picamera2 controls: {ctrl_dict}")
        except Exception as e:
            logger.warning(f"Failed to apply Picamera2 controls: {e}")

    def get_frame_rgb(self) -> Optional[np.ndarray]:
        """
        Capture frame and return in RGB format.

        Returns:
            np.ndarray: RGB frame from camera, or None if capture failed
        """
        frame = self.get_frame()
        if frame is None:
            return None

        # get_frame returns BGR, convert to RGB
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def release(self) -> None:
        """Release camera resources."""
        if self.picam2 is not None:
            try:
                self.picam2.stop()
                self.picam2.close()
            except:
                pass
            self.picam2 = None
            logger.info("Picamera2 released")

        if self.cap is not None:
            self.cap.release()
            self.cap = None
            logger.info("OpenCV camera released")

        self.is_open = False

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()

    def _check_health(self):
        """Periodic health check to detect camera issues"""
        now = time.time()
        if self.last_health_check is None:
            self.last_health_check = now
            return
        
        elapsed = now - self.last_health_check
        if elapsed >= self.health_check_interval:
            logger.debug(f"Camera health check: consecutive_failures={self.consecutive_failures}")
            self.last_health_check = now
            
            # If too many consecutive failures, trigger recovery
            if self.consecutive_failures >= 5:
                logger.warning("Camera health check failed, entering recovery mode")
                self.recovery_mode = True
                self.release()

    def _on_frame_failure(self):
        """Handle frame capture failure"""
        self.consecutive_failures += 1
        if self.consecutive_failures >= 10:
            logger.error(f"Camera failing consistently ({self.consecutive_failures} consecutive failures)")
            self.recovery_mode = True
            self.release()

    def get_camera_info(self) -> dict:
        """
        Get camera information and status.

        Returns:
            dict: Camera information including status, frames captured, etc.
        """
        backend = "Picamera2" if self.use_picamera2 else "OpenCV"
        return {
            "camera_index": self.camera_index,
            "resolution": self.resolution,
            "is_open": self.is_open,
            "frame_count": self.frame_count,
            "last_frame_time": (
                self.last_frame_time.isoformat() if self.last_frame_time else None
            ),
            "backend": backend,
            "consecutive_failures": self.consecutive_failures,
            "recovery_mode": self.recovery_mode,
        }
