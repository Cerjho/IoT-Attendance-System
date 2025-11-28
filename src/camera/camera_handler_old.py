"""
Camera Handler Module
Manages single camera for frame capture and processing
"""

import logging
import time
from datetime import datetime
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CameraHandler:
    """
    Handles camera operations for IoT attendance system.
    Uses a single camera for continuous frame capture and processing.
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
        self.is_open = False
        self.frame_count = 0
        self.last_frame_time = None

    def start(self) -> bool:
        """
        Start camera capture.

        Returns:
            bool: True if camera started successfully, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_index)

            if not self.cap.isOpened():
                logger.error(f"Failed to open camera at index {self.camera_index}")
                return False

            # Set camera properties with V4L2 specific settings for Raspberry Pi
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Try to set encoding to MJPEG for better compatibility
            try:
                self.cap.set(
                    cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G")
                )
            except:
                pass

            # Warmup period: discard first few frames, with shorter timeout
            logger.info(f"Warming up camera {self.camera_index}...")
            success_count = 0
            max_attempts = 10

            for i in range(max_attempts):
                try:
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        success_count += 1
                        logger.debug(
                            f"Warmup frame {i+1}: Success, shape={frame.shape}"
                        )
                    else:
                        logger.debug(
                            f"Warmup frame {i+1}: Failed (read returned {ret})"
                        )
                    time.sleep(0.2)
                except Exception as e:
                    logger.debug(f"Warmup frame {i+1}: Exception - {str(e)}")
                    time.sleep(0.2)

            if success_count == 0:
                logger.error(
                    f"Camera {self.camera_index} opened but cannot read frames after {max_attempts} attempts. This is typically a driver/configuration issue. See CAMERA_TROUBLESHOOTING.md"
                )
                self.cap.release()
                self.cap = None
                return False

            self.is_open = True
            logger.info(
                f"Camera {self.camera_index} started successfully ({success_count}/{max_attempts} warmup frames)"
            )
            return True

        except Exception as e:
            logger.error(f"Error starting camera: {str(e)}")
            return False

    def get_frame(self) -> Optional[np.ndarray]:
        """
        Capture and return a single frame from camera.

        Returns:
            np.ndarray: Frame from camera, or None if capture failed
        """
        if not self.is_open or self.cap is None:
            logger.warning("Camera is not open")
            return None

        try:
            ret, frame = self.cap.read()

            if not ret:
                logger.warning("Failed to read frame from camera")
                return None

            self.frame_count += 1
            self.last_frame_time = datetime.now()

            return frame

        except Exception as e:
            logger.error(f"Error capturing frame: {str(e)}")
            return None

    def get_frame_rgb(self) -> Optional[np.ndarray]:
        """
        Capture frame and convert to RGB.

        Returns:
            np.ndarray: RGB frame from camera, or None if capture failed
        """
        frame = self.get_frame()
        if frame is None:
            return None

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def release(self) -> None:
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
            self.is_open = False
            logger.info("Camera released")

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
        return {
            "camera_index": self.camera_index,
            "resolution": self.resolution,
            "is_open": self.is_open,
            "frame_count": self.frame_count,
            "last_frame_time": (
                self.last_frame_time.isoformat() if self.last_frame_time else None
            ),
        }
