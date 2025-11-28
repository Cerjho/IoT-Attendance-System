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

    def __init__(self, camera_index: int = 0, resolution: Tuple[int, int] = (640, 480)):
        """
        Initialize camera handler.

        Args:
            camera_index: Camera device index (default: 0 for primary camera)
            resolution: Tuple of (width, height) for camera resolution
        """
        self.camera_index = camera_index
        self.resolution = resolution
        self.cap = None
        self.picam2 = None
        self.is_open = False
        self.frame_count = 0
        self.last_frame_time = None
        self.use_picamera2 = PICAMERA2_AVAILABLE

    def start(self) -> bool:
        """
        Start camera capture.

        Returns:
            bool: True if camera started successfully, False otherwise
        """
        # Try Picamera2 first (for Bookworm)
        if self.use_picamera2 and PICAMERA2_AVAILABLE:
            try:
                logger.info("Attempting to start camera with Picamera2 (libcamera)...")
                self.picam2 = Picamera2()

                # Configure camera
                config = self.picam2.create_preview_configuration(
                    main={"size": self.resolution, "format": "RGB888"}
                )
                self.picam2.configure(config)

                # Start camera
                self.picam2.start()

                # Warmup period
                logger.info("Warming up camera...")
                time.sleep(2)

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
            self.cap = cv2.VideoCapture(self.camera_index)

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
        Capture and return a single frame from camera.

        Returns:
            np.ndarray: Frame from camera (BGR format), or None if capture failed
        """
        if not self.is_open:
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
                    return frame_bgr
                else:
                    logger.warning("Failed to capture frame from Picamera2")
                    return None

            # Use OpenCV
            elif self.cap is not None:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Failed to read frame from OpenCV")
                    return None

                self.frame_count += 1
                self.last_frame_time = datetime.now()
                return frame

            else:
                logger.error("No camera backend available")
                return None

        except Exception as e:
            logger.error(f"Error capturing frame: {str(e)}")
            return None

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
        }
