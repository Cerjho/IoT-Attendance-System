"""
Lighting Compensator
Applies adaptive image enhancements to improve photo quality in various lighting conditions
"""

import logging
from typing import Dict, Optional

import cv2
import numpy as np

from src.utils.logging_factory import get_logger

logger = get_logger(__name__)


class LightingCompensator:
    """Applies lighting compensation to improve image quality"""

    def __init__(self, config: Dict = None):
        """
        Initialize lighting compensator

        Args:
            config: Dictionary with settings:
                - enabled: bool
                - adaptive_exposure: bool
                - auto_brightness_adjust: bool
                - histogram_equalization: bool (CLAHE)
                - low_light_mode: str ('auto', 'always', 'never')
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.adaptive_exposure = self.config.get("adaptive_exposure", True)
        self.auto_brightness = self.config.get("auto_brightness_adjust", True)
        self.histogram_eq = self.config.get("histogram_equalization", True)
        self.low_light_mode = self.config.get("low_light_mode", "auto")

    def compensate(self, frame: np.ndarray, lighting_analysis: Dict) -> np.ndarray:
        """
        Apply lighting compensation to frame

        Args:
            frame: BGR image (numpy array)
            lighting_analysis: Output from LightingAnalyzer.analyze_frame()

        Returns:
            Compensated BGR image
        """
        if not self.enabled:
            return frame

        compensated = frame.copy()

        # Determine if we should apply low-light enhancements
        apply_low_light = self._should_apply_low_light(lighting_analysis)

        if apply_low_light:
            logger.debug("Applying low-light compensation")
            compensated = self._apply_low_light_enhancement(
                compensated, lighting_analysis
            )

        # Apply contrast enhancement if needed
        if lighting_analysis.get("is_low_contrast", False):
            logger.debug("Applying contrast enhancement")
            compensated = self._apply_contrast_enhancement(compensated)

        # Apply brightness adjustment if needed
        if self.auto_brightness:
            brightness = lighting_analysis.get("brightness", 128)
            if brightness < 80 or brightness > 200:
                logger.debug(
                    f"Applying brightness adjustment (current: {brightness:.1f})"
                )
                compensated = self._adjust_brightness(compensated, brightness)

        return compensated

    def _should_apply_low_light(self, lighting_analysis: Dict) -> bool:
        """Determine if low-light enhancement should be applied"""
        if self.low_light_mode == "always":
            return True
        elif self.low_light_mode == "never":
            return False
        else:  # 'auto'
            return lighting_analysis.get("is_low_light", False)

    def _apply_low_light_enhancement(
        self, frame: np.ndarray, lighting_analysis: Dict
    ) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)"""
        if not self.histogram_eq:
            return frame

        # Convert to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)

        # Merge channels
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        return enhanced_bgr

    def _apply_contrast_enhancement(self, frame: np.ndarray) -> np.ndarray:
        """Apply contrast enhancement using CLAHE"""
        # Convert to LAB
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE with moderate settings
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)

        # Merge and convert back
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        return enhanced_bgr

    def _adjust_brightness(
        self, frame: np.ndarray, current_brightness: float
    ) -> np.ndarray:
        """Adjust brightness using gamma correction"""
        target_brightness = 140

        if abs(current_brightness - target_brightness) < 20:
            return frame

        # Calculate gamma value
        # If too dark (low brightness), gamma > 1 to brighten
        # If too bright (high brightness), gamma < 1 to darken
        if current_brightness > 0:
            gamma = np.log(target_brightness / 255.0) / np.log(
                current_brightness / 255.0
            )
            # Clamp gamma to avoid extreme adjustments
            gamma = max(0.5, min(2.0, gamma))
        else:
            gamma = 1.5

        # Build lookup table for gamma correction
        lut = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype(
            np.uint8
        )

        # Apply gamma correction
        adjusted = cv2.LUT(frame, lut)

        logger.debug(f"Gamma correction applied: {gamma:.2f}")

        return adjusted

    def apply_quick_enhancement(self, frame: np.ndarray) -> np.ndarray:
        """
        Quick enhancement without full analysis (for real-time preview)

        Args:
            frame: BGR image

        Returns:
            Enhanced BGR image
        """
        if not self.enabled:
            return frame

        # Quick brightness check
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)

        enhanced = frame.copy()

        # Apply CLAHE if brightness is low
        if brightness < 100:
            lab = cv2.cvtColor(enhanced, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        return enhanced
