#!/usr/bin/env python3
"""
IoT Face Detection & Photo Capture System
Detects faces and captures photos without identity recognition
"""
import logging
import os
from datetime import datetime
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class SimpleFaceDetector:
    """Detects faces using OpenCV Haar Cascade (no face_recognition library needed)"""

    def __init__(self):
        """Initialize face detector with Haar Cascade"""
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.cascade = cv2.CascadeClassifier(cascade_path)
        logger.info("Face detector initialized (OpenCV Haar Cascade)")

    def detect_faces(self, frame: np.ndarray) -> list:
        """
        Detect faces in frame using Haar Cascade

        Args:
            frame: Input frame (BGR)

        Returns:
            List of (x, y, w, h) tuples for detected faces
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        return faces

    def draw_face_boxes(self, frame: np.ndarray, faces: list) -> np.ndarray:
        """Draw boxes around detected faces"""
        frame_copy = frame.copy()
        for x, y, w, h in faces:
            cv2.rectangle(frame_copy, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return frame_copy

    def crop_face(self, frame: np.ndarray, face: Tuple) -> np.ndarray:
        """Extract face region from frame"""
        x, y, w, h = face
        return frame[y : y + h, x : x + w]


class PhotoCaptureManager:
    """Manages photo capture and storage"""

    def __init__(self, photo_dir: str = "photos"):
        """
        Initialize photo capture manager

        Args:
            photo_dir: Directory to store captured photos
        """
        self.photo_dir = photo_dir
        os.makedirs(photo_dir, exist_ok=True)
        self.capture_count = 0
        logger.info(f"Photo capture manager initialized. Storage: {photo_dir}")

    def capture_photo(self, frame: np.ndarray, face_index: int = 0) -> Optional[str]:
        """
        Capture and save photo of detected face

        Args:
            frame: Input frame
            face_index: Index of face in frame (for multiple faces)

        Returns:
            Path to saved photo, or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"face_capture_{timestamp}_{face_index}.jpg"
            filepath = os.path.join(self.photo_dir, filename)

            success = cv2.imwrite(filepath, frame)
            if success:
                self.capture_count += 1
                logger.info(f"Photo captured: {filename}")
                return filepath
            else:
                logger.error(f"Failed to save photo: {filename}")
                return None

        except Exception as e:
            logger.error(f"Error capturing photo: {str(e)}")
            return None

    def get_capture_count(self) -> int:
        """Get total photos captured"""
        return self.capture_count


class FaceDetectionEvent:
    """Represents a face detection event"""

    def __init__(self, timestamp: datetime, face_count: int, photos: list):
        """
        Args:
            timestamp: When detection occurred
            face_count: Number of faces detected
            photos: List of photo file paths
        """
        self.timestamp = timestamp
        self.face_count = face_count
        self.photos = photos

    def to_dict(self):
        """Convert to dictionary for logging/export"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "faces_detected": self.face_count,
            "photos_captured": self.photos,
            "photo_count": len(self.photos),
        }


class DetectionLogger:
    """Logs face detection events"""

    def __init__(self):
        """Initialize detection logger"""
        self.events = []
        logger.info("Detection logger initialized")

    def log_event(self, event: FaceDetectionEvent) -> None:
        """Log a detection event"""
        self.events.append(event)
        logger.info(
            f"Detection logged: {event.face_count} faces, {len(event.photos)} photos"
        )

    def get_summary(self) -> dict:
        """Get summary statistics"""
        total_detections = len(self.events)
        total_faces = sum(e.face_count for e in self.events)
        total_photos = sum(len(e.photos) for e in self.events)

        return {
            "total_detection_events": total_detections,
            "total_faces_detected": total_faces,
            "total_photos_captured": total_photos,
            "average_faces_per_event": (
                total_faces / total_detections if total_detections > 0 else 0
            ),
        }

    def export_log(self, filepath: str) -> bool:
        """Export detection log to JSON"""
        try:
            import json

            data = {
                "summary": self.get_summary(),
                "events": [e.to_dict() for e in self.events],
            }
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Detection log exported to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting log: {str(e)}")
            return False

    def clear(self) -> None:
        """Clear all logged events"""
        self.events.clear()
        logger.info("Detection log cleared")
