"""
Lighting Analyzer
Analyzes frame brightness, contrast, and histogram for lighting quality assessment
"""

import logging
from typing import Dict, Tuple

import cv2
import numpy as np

from src.utils.logging_factory import get_logger

logger = get_logger(__name__)


class LightingAnalyzer:
    """Analyzes lighting conditions in camera frames"""

    def __init__(self, config: Dict = None):
        """
        Initialize lighting analyzer

        Args:
            config: Dictionary with thresholds:
                - brightness_threshold: int (0-255, default 80)
                - contrast_threshold: int (default 40)
        """
        self.config = config or {}
        self.brightness_threshold = self.config.get("brightness_threshold", 80)
        self.contrast_threshold = self.config.get("contrast_threshold", 40)
        
        logger.info(
            f"💡 Lighting analyzer initialized: brightness_threshold={self.brightness_threshold}, "
            f"contrast_threshold={self.contrast_threshold}"
        )

    def analyze_frame(self, frame: np.ndarray) -> Dict:
        """
        Analyze lighting conditions in a frame

        Args:
            frame: BGR image (numpy array)

        Returns:
            Dictionary with lighting metrics:
                - brightness: float (0-255)
                - contrast: float
                - histogram: numpy array
                - is_low_light: bool
                - is_high_light: bool
                - is_low_contrast: bool
                - quality_score: float (0-1)
        """
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Calculate brightness (mean intensity)
        brightness = np.mean(gray)

        # Calculate contrast (standard deviation)
        contrast = np.std(gray)

        # Get histogram
        histogram = cv2.calcHist([gray], [0], None, [256], [0, 256])

        # Determine lighting conditions
        is_low_light = brightness < self.brightness_threshold
        is_high_light = brightness > 200
        is_low_contrast = contrast < self.contrast_threshold

        # Calculate quality score (0-1, higher is better)
        # Ideal brightness: 100-180, ideal contrast: 50+
        brightness_score = self._calculate_brightness_score(brightness)
        contrast_score = self._calculate_contrast_score(contrast)
        quality_score = (brightness_score + contrast_score) / 2.0

        result = {
            "brightness": float(brightness),
            "contrast": float(contrast),
            "histogram": histogram,
            "is_low_light": is_low_light,
            "is_high_light": is_high_light,
            "is_low_contrast": is_low_contrast,
            "quality_score": quality_score,
        }

        # Log with quality indicators
        quality_emoji = "✅" if quality_score >= 0.7 else "⚠️" if quality_score >= 0.4 else "❌"
        logger.debug(
            f"{quality_emoji} Lighting: brightness={brightness:.1f}, contrast={contrast:.1f}, "
            f"quality={quality_score:.2f}, low_light={is_low_light}, high_light={is_high_light}, "
            f"low_contrast={is_low_contrast}"
        )
        
        # Log warnings for poor conditions
        if is_low_light:
            logger.warning(f"⚠️ Low light detected: brightness={brightness:.1f} < {self.brightness_threshold}")
        if is_high_light:
            logger.warning(f"⚠️ High light detected: brightness={brightness:.1f} > 200")
        if is_low_contrast:
            logger.warning(f"⚠️ Low contrast detected: contrast={contrast:.1f} < {self.contrast_threshold}")

        return result

    def _calculate_brightness_score(self, brightness: float) -> float:
        """Calculate brightness quality score (0-1)"""
        if 100 <= brightness <= 180:
            score = 1.0
        elif brightness < 100:
            score = max(0.0, brightness / 100.0)
        else:  # brightness > 180
            score = max(0.0, 1.0 - (brightness - 180) / 75.0)
        
        logger.debug(f"Brightness score: {score:.2f} (brightness={brightness:.1f})")
        return score

    def _calculate_contrast_score(self, contrast: float) -> float:
        """Calculate contrast quality score (0-1)"""
        if contrast >= 50:
            score = 1.0
        else:
            score = max(0.0, contrast / 50.0)
        
        logger.debug(f"Contrast score: {score:.2f} (contrast={contrast:.1f})")
        return score

    def suggest_exposure_adjustment(
        self, brightness: float, current_exposure: int = 10000
    ) -> int:
        """
        Suggest exposure adjustment based on brightness

        Args:
            brightness: Current frame brightness (0-255)
            current_exposure: Current exposure time in microseconds

        Returns:
            Suggested exposure time in microseconds
        """
        target_brightness = 140  # Target brightness level

        if abs(brightness - target_brightness) < 20:
            # Close enough, no adjustment needed
            logger.debug(
                f"✅ Exposure OK: brightness={brightness:.1f} near target={target_brightness}"
            )
            return current_exposure

        # Calculate adjustment ratio
        if brightness > 0:
            ratio = target_brightness / brightness
            # Clamp ratio to avoid extreme adjustments
            ratio = max(0.5, min(2.0, ratio))
            new_exposure = int(current_exposure * ratio)
        else:
            new_exposure = current_exposure * 2

        # Clamp to reasonable exposure range (1ms to 100ms)
        new_exposure = max(1000, min(100000, new_exposure))

        logger.info(
            f"🔆 Exposure adjustment: {current_exposure}µs → {new_exposure}µs "
            f"(brightness {brightness:.1f} → target {target_brightness})"
        )
        
        if new_exposure != int(current_exposure * ratio):
            logger.debug(f"Exposure clamped to safe range [1000, 100000]µs")

        return new_exposure
