#!/usr/bin/env python3
"""
Face Quality Assessment Module
Checks face quality for automatic capture without dlib dependency
Uses OpenCV-based methods for all checks
"""
import logging
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from src.utils.logging_factory import get_logger

logger = get_logger(__name__)


class FaceQualityChecker:
    """
    Comprehensive face quality assessment for automatic capture
    All checks use OpenCV - no dlib required
    """

    def __init__(self, config: dict = None):
        """Initialize face quality checker with configuration"""
        config = config or {}

        # Quality thresholds (optimized for faster capture)
        self.min_face_size = config.get(
            "min_face_size", 60
        )  # Face width minimum (relaxed for easier capture)
        self.center_tolerance_x = config.get("center_tolerance_x", 0.25)  # 25% of width (more relaxed)
        self.center_tolerance_y = config.get(
            "center_tolerance_y", 0.25
        )  # 25% of height (more relaxed)
        self.max_yaw = config.get("max_yaw", 35.0)  # degrees (very relaxed)
        self.max_pitch = config.get("max_pitch", 35.0)  # degrees (very relaxed)
        self.max_roll = config.get("max_roll", 80.0)  # degrees (very relaxed for rotated cameras)
        self.min_eye_aspect_ratio = config.get("min_eye_aspect_ratio", 0.18)
        self.min_sharpness = config.get("min_sharpness", 40.0)  # Laplacian variance (very relaxed)
        self.min_brightness = config.get("min_brightness", 40)  # Very relaxed for poor lighting
        self.max_brightness = config.get("max_brightness", 220)  # Very relaxed for bright lighting
        self.max_mouth_openness = config.get("max_mouth_openness", 0.6)

        # Load cascade classifiers
        cascade_path = cv2.data.haarcascades
        self.face_cascade = cv2.CascadeClassifier(
            cascade_path + "haarcascade_frontalface_default.xml"
        )
        self.eye_cascade = cv2.CascadeClassifier(cascade_path + "haarcascade_eye.xml")
        self.mouth_cascade = cv2.CascadeClassifier(
            cascade_path + "haarcascade_smile.xml"
        )

        logger.info(
            f"Face quality checker initialized with thresholds: "
            f"face_size={self.min_face_size}px, center_tol={self.center_tolerance_x*100}%, "
            f"pose=±{self.max_yaw}/±{self.max_pitch}/±{self.max_roll}°"
        )

    def check_quality(
        self, frame: np.ndarray, face_box: Tuple[int, int, int, int]
    ) -> Dict:
        """
        Comprehensive quality check for a detected face

        Args:
            frame: Input image (BGR)
            face_box: (x, y, w, h) of detected face

        Returns:
            dict with 'passed', 'score', 'checks', 'reason'
        """
        x, y, w, h = face_box

        if h <= 0 or w <= 0:
            return {
                "passed": False,
                "score": 0.0,
                "checks": {},
                "reason": "Invalid face box",
            }

        face_roi = frame[y : y + h, x : x + w]

        if face_roi.size == 0:
            return {
                "passed": False,
                "score": 0.0,
                "checks": {},
                "reason": "Invalid face ROI",
            }

        checks = {}

        # Run all quality checks
        checks["face_count"] = self._check_face_count(frame)
        checks["face_size"] = self._check_face_size(face_box)
        checks["face_centered"] = self._check_face_centered(frame, face_box)
        checks["head_pose"] = self._check_head_pose(frame, face_box)
        checks["eyes_open"] = self._check_eyes_open(face_roi)
        checks["mouth_closed"] = self._check_mouth_closed(face_roi)
        checks["sharpness"] = self._check_sharpness(face_roi)
        checks["brightness"] = self._check_brightness(face_roi)
        checks["illumination"] = self._check_illumination(face_roi)

        # Aggregate results
        all_passed = all(check["passed"] for check in checks.values())
        scores = [check.get("score", 0.0) for check in checks.values()]
        overall_score = np.mean(scores) if scores else 0.0

        # Find first failure reason
        reason = "All checks passed"
        if not all_passed:
            for check_name, check_result in checks.items():
                if not check_result["passed"]:
                    reason = f"{check_name}: {check_result.get('reason', 'Failed')}"
                    break

        return {
            "passed": all_passed,
            "score": overall_score,
            "checks": checks,
            "reason": reason,
        }

    def _check_face_count(self, frame: np.ndarray) -> Dict:
        """Check that at least 1 face is detected (allow background faces, we use largest)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        # Allow 1-2 faces (main person + possible reflection/background)
        passed = 1 <= len(faces) <= 2
        return {
            "passed": passed,
            "score": 1.0 if len(faces) == 1 else 0.8,  # Slight penalty for multiple
            "value": len(faces),
            "reason": f"Detected {len(faces)} face(s)" if passed else f"Detected {len(faces)} faces (need 1-2)",
        }

    def _check_face_size(self, face_box: Tuple[int, int, int, int]) -> Dict:
        """Check face is large enough"""
        x, y, w, h = face_box
        passed = w >= self.min_face_size
        score = min(1.0, w / self.min_face_size)
        return {
            "passed": passed,
            "score": score,
            "value": w,
            "reason": f"Face width {w}px (need ≥{self.min_face_size}px)",
        }

    def _check_face_centered(
        self, frame: np.ndarray, face_box: Tuple[int, int, int, int]
    ) -> Dict:
        """Check face is centered (±12% of image center)"""
        h_img, w_img = frame.shape[:2]
        x, y, w, h = face_box
        face_cx, face_cy = x + w / 2, y + h / 2
        img_cx, img_cy = w_img / 2, h_img / 2
        dev_x = abs(face_cx - img_cx) / w_img
        dev_y = abs(face_cy - img_cy) / h_img
        passed = dev_x <= self.center_tolerance_x and dev_y <= self.center_tolerance_y
        score_x = 1.0 - min(1.0, dev_x / self.center_tolerance_x)
        score_y = 1.0 - min(1.0, dev_y / self.center_tolerance_y)
        score = (score_x + score_y) / 2
        return {
            "passed": passed,
            "score": score,
            "value": (dev_x * 100, dev_y * 100),
            "reason": f"Deviation: {dev_x*100:.1f}%x, {dev_y*100:.1f}%y",
        }

    def _check_head_pose(
        self, frame: np.ndarray, face_box: Tuple[int, int, int, int]
    ) -> Dict:
        """Estimate head pose using eyes"""
        x, y, w, h = face_box
        face_roi = frame[y : y + h, x : x + w]
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(gray_roi, 1.1, 3, minSize=(20, 20))

        if len(eyes) < 2:
            return {
                "passed": False,
                "score": 0.0,
                "value": (0, 0, 0),
                "reason": "Cannot detect both eyes",
            }

        eyes = sorted(eyes, key=lambda e: e[0])
        left_eye, right_eye = eyes[0], eyes[1]
        left_center = (left_eye[0] + left_eye[2] // 2, left_eye[1] + left_eye[3] // 2)
        right_center = (
            right_eye[0] + right_eye[2] // 2,
            right_eye[1] + right_eye[3] // 2,
        )

        # Calculate roll
        dy = right_center[1] - left_center[1]
        dx = right_center[0] - left_center[0]
        roll = np.degrees(np.arctan2(dy, dx)) if dx != 0 else 0

        # Estimate yaw from eye position asymmetry
        face_center_x = w / 2
        left_dist = abs(left_center[0] - face_center_x)
        right_dist = abs(right_center[0] - face_center_x)
        asymmetry = abs(left_dist - right_dist) / w
        yaw = asymmetry * 30

        # Estimate pitch from eye vertical position
        avg_eye_y = (left_center[1] + right_center[1]) / 2
        relative_y = avg_eye_y / h
        pitch = abs(relative_y - 0.4) * 50

        passed = (
            abs(yaw) <= self.max_yaw
            and abs(pitch) <= self.max_pitch
            and abs(roll) <= self.max_roll
        )
        score_yaw = 1.0 - min(1.0, abs(yaw) / self.max_yaw)
        score_pitch = 1.0 - min(1.0, abs(pitch) / self.max_pitch)
        score_roll = 1.0 - min(1.0, abs(roll) / self.max_roll)
        score = (score_yaw + score_pitch + score_roll) / 3

        return {
            "passed": passed,
            "score": score,
            "value": (yaw, pitch, roll),
            "reason": f"Pose: yaw={yaw:.1f}°, pitch={pitch:.1f}°, roll={roll:.1f}°",
        }

    def _check_eyes_open(self, face_roi: np.ndarray) -> Dict:
        """Check both eyes are open"""
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(gray_roi, 1.1, 3, minSize=(20, 20))

        if len(eyes) < 2:
            return {
                "passed": False,
                "score": 0.0,
                "value": 0.0,
                "reason": f"Detected {len(eyes)} eyes (need 2)",
            }

        ears = [eh / ew if ew > 0 else 0 for (ex, ey, ew, eh) in eyes]
        avg_ear = np.mean(ears)
        passed = avg_ear >= self.min_eye_aspect_ratio
        score = min(1.0, avg_ear / self.min_eye_aspect_ratio)

        return {
            "passed": passed,
            "score": score,
            "value": avg_ear,
            "reason": f"Eye EAR={avg_ear:.2f}",
        }

    def _check_mouth_closed(self, face_roi: np.ndarray) -> Dict:
        """Check mouth is closed or only slightly open"""
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        h_roi = face_roi.shape[0]
        mouth_region = gray_roi[int(h_roi * 0.6) :, :]
        mouths = self.mouth_cascade.detectMultiScale(
            mouth_region, 1.5, 5, minSize=(25, 15)
        )

        if len(mouths) == 0:
            return {
                "passed": True,
                "score": 1.0,
                "value": 0.0,
                "reason": "Mouth closed",
            }

        largest_mouth = max(mouths, key=lambda m: m[2] * m[3])
        openness = largest_mouth[3] / face_roi.shape[0]
        passed = openness <= self.max_mouth_openness
        score = 1.0 - min(1.0, openness / self.max_mouth_openness)

        return {
            "passed": passed,
            "score": score,
            "value": openness,
            "reason": f"Mouth openness={openness:.2f}",
        }

    def _check_sharpness(self, face_roi: np.ndarray) -> Dict:
        """Check image sharpness using Laplacian variance"""
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray_roi, cv2.CV_64F)
        sharpness = laplacian.var()
        passed = sharpness >= self.min_sharpness
        score = min(1.0, sharpness / self.min_sharpness)
        return {
            "passed": passed,
            "score": score,
            "value": sharpness,
            "reason": f"Sharpness={sharpness:.1f}",
        }

    def _check_brightness(self, face_roi: np.ndarray) -> Dict:
        """Check face brightness is in acceptable range"""
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray_roi)
        passed = self.min_brightness <= avg_brightness <= self.max_brightness
        ideal_brightness = (self.min_brightness + self.max_brightness) / 2
        deviation = abs(avg_brightness - ideal_brightness) / (
            ideal_brightness - self.min_brightness
        )
        score = 1.0 - min(1.0, deviation)
        return {
            "passed": passed,
            "score": score,
            "value": avg_brightness,
            "reason": f"Brightness={avg_brightness:.1f}",
        }

    def _check_illumination(self, face_roi: np.ndarray) -> Dict:
        """Check illumination uniformity (no mask/sunglasses/heavy shadows)"""
        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
        std_dev = np.std(gray_roi)
        dark_pixels = np.sum(gray_roi < 50)
        dark_ratio = dark_pixels / gray_roi.size
        uniformity_ok = std_dev < 70
        dark_ok = dark_ratio < 0.40
        passed = uniformity_ok and dark_ok
        uniformity_score = 1.0 - min(1.0, std_dev / 70)
        dark_score = 1.0 - min(1.0, dark_ratio / 0.40)
        score = (uniformity_score + dark_score) / 2
        return {
            "passed": passed,
            "score": score,
            "value": (std_dev, dark_ratio),
            "reason": "Good illumination" if passed else "Poor illumination",
        }


class AutoCaptureStateMachine:
    """
    State machine for automatic face capture
    Manages 3-second stability timer with all quality checks
    """

    def __init__(
        self,
        quality_checker: FaceQualityChecker,
        stability_duration: float = 1.5,
        timeout: float = 20.0,
    ):
        """
        Initialize auto-capture state machine

        Args:
            quality_checker: FaceQualityChecker instance
            stability_duration: Seconds of perfect stability required (default 2)
            timeout: Maximum seconds to wait for capture (default 15)
        """
        self.quality_checker = quality_checker
        self.stability_duration = stability_duration
        self.timeout = timeout
        self.reset()
        logger.info(
            f"Auto-capture state machine initialized: stability={stability_duration}s, timeout={timeout}s"
        )

    def reset(self):
        """Reset state machine"""
        self.state = "IDLE"
        self.start_time = None
        self.stability_start_time = None
        self.last_quality_result = None
        self.capture_triggered = False
        self.last_countdown = None

    def start_session(self):
        """Start a new capture session (called after QR scan)"""
        self.reset()
        self.state = "WAITING"
        self.start_time = cv2.getTickCount() / cv2.getTickFrequency()
        logger.info("Auto-capture session started")

    def update(
        self, frame: np.ndarray, face_box: Optional[Tuple[int, int, int, int]]
    ) -> Dict:
        """
        Update state machine with current frame

        Returns:
            dict with state info and capture trigger
        """
        current_time = cv2.getTickCount() / cv2.getTickFrequency()

        if self.state == "IDLE":
            return {
                "state": "IDLE",
                "should_capture": False,
                "elapsed": 0.0,
                "stability_elapsed": 0.0,
                "quality_result": None,
                "message": "Idle",
                "countdown": None,
            }

        elapsed = current_time - self.start_time

        # Check timeout
        if elapsed > self.timeout:
            self.state = "TIMEOUT"
            logger.warning(f"Auto-capture timeout after {elapsed:.1f}s")
            return {
                "state": "TIMEOUT",
                "should_capture": False,
                "elapsed": elapsed,
                "stability_elapsed": 0.0,
                "quality_result": self.last_quality_result,
                "message": "Timeout - conditions not met",
                "countdown": None,
            }

        # Check if face detected
        if face_box is None:
            if self.stability_start_time is not None:
                logger.debug("Face lost - resetting stability timer")
            self.stability_start_time = None
            return {
                "state": "WAITING",
                "should_capture": False,
                "elapsed": elapsed,
                "stability_elapsed": 0.0,
                "quality_result": None,
                "message": "Waiting for face detection",
                "countdown": None,
            }

        # Run quality check
        quality_result = self.quality_checker.check_quality(frame, face_box)
        self.last_quality_result = quality_result

        if not quality_result["passed"]:
            # Quality check failed - reset stability timer
            if self.stability_start_time is not None:
                logger.debug(
                    f"Quality check failed: {quality_result['reason']} - resetting timer"
                )
            self.stability_start_time = None
            return {
                "state": "WAITING",
                "should_capture": False,
                "elapsed": elapsed,
                "stability_elapsed": 0.0,
                "quality_result": quality_result,
                "message": quality_result["reason"],
                "countdown": None,
            }

        # All quality checks passed!
        if self.stability_start_time is None:
            # Start stability timer
            self.stability_start_time = current_time
            logger.info("All quality checks passed - starting 3-second countdown")
            countdown = int(np.ceil(self.stability_duration))
            return {
                "state": "STABLE",
                "should_capture": False,
                "elapsed": elapsed,
                "stability_elapsed": 0.0,
                "quality_result": quality_result,
                "message": "Perfect! Hold still...",
                "countdown": countdown,
            }

        # Check stability duration
        stability_elapsed = current_time - self.stability_start_time

        if stability_elapsed >= self.stability_duration:
            # Capture trigger!
            if not self.capture_triggered:
                self.capture_triggered = True
                self.state = "CAPTURED"
                logger.info(
                    f"Capture triggered after {stability_elapsed:.1f}s of stability"
                )
                return {
                    "state": "CAPTURED",
                    "should_capture": True,
                    "elapsed": elapsed,
                    "stability_elapsed": stability_elapsed,
                    "quality_result": quality_result,
                    "message": "Capture complete!",
                    "countdown": None,
                }

        # Still in stable state - update countdown
        remaining = self.stability_duration - stability_elapsed
        countdown = int(np.ceil(remaining))

        return {
            "state": "STABLE",
            "should_capture": False,
            "elapsed": elapsed,
            "stability_elapsed": stability_elapsed,
            "quality_result": quality_result,
            "message": f"Hold still... {countdown}",
            "countdown": countdown,
        }

    def get_countdown(self) -> Optional[int]:
        """Get current countdown value (3, 2, 1) or None"""
        if self.state != "STABLE" or self.stability_start_time is None:
            return None
        current_time = cv2.getTickCount() / cv2.getTickFrequency()
        stability_elapsed = current_time - self.stability_start_time
        remaining = self.stability_duration - stability_elapsed
        return int(np.ceil(remaining)) if remaining > 0 else None
