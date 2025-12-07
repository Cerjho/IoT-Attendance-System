"""
Tests for lighting analysis and compensation modules
"""

import pytest
import numpy as np
from src.lighting.analyzer import LightingAnalyzer
from src.lighting.compensator import LightingCompensator


class TestLightingAnalyzer:
    """Test LightingAnalyzer functionality"""

    def test_analyzer_initialization_default(self):
        """Test analyzer initializes with default config"""
        analyzer = LightingAnalyzer()
        assert analyzer.brightness_threshold == 80
        assert analyzer.contrast_threshold == 40

    def test_analyzer_initialization_custom(self):
        """Test analyzer with custom thresholds"""
        config = {"brightness_threshold": 100, "contrast_threshold": 50}
        analyzer = LightingAnalyzer(config)
        assert analyzer.brightness_threshold == 100
        assert analyzer.contrast_threshold == 50

    def test_analyze_bright_frame(self):
        """Test analysis of well-lit frame"""
        analyzer = LightingAnalyzer()
        # Create bright frame (200 brightness)
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 200

        result = analyzer.analyze_frame(frame)

        assert "brightness" in result
        assert "contrast" in result
        assert "quality_score" in result
        assert result["brightness"] >= 150  # Bright frame
        assert "is_low_light" in result
        assert "is_high_light" in result

    def test_analyze_dark_frame(self):
        """Test analysis of dark frame"""
        analyzer = LightingAnalyzer()
        # Create dark frame (50 brightness)
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 50

        result = analyzer.analyze_frame(frame)

        assert "brightness" in result
        assert result["brightness"] <= 80  # Dark frame
        assert "is_low_light" in result
        assert "quality_score" in result

    def test_analyze_low_contrast(self):
        """Test analysis of low contrast frame"""
        analyzer = LightingAnalyzer()
        
        # Create uniform frame (low contrast)
        frame = np.full((480, 640, 3), 128, dtype=np.uint8)
        
        result = analyzer.analyze_frame(frame)
        
        assert "contrast" in result
        assert "is_low_contrast" in result
        # Uniform frame should have very low contrast
        assert result["contrast"] < 50

    def test_analyze_normal_frame(self):
        """Test analysis of well-lit frame with good contrast"""
        analyzer = LightingAnalyzer()
        
        # Create frame with good brightness and contrast
        frame = np.random.randint(80, 180, (480, 640, 3), dtype=np.uint8)
        
        result = analyzer.analyze_frame(frame)
        
        assert "quality_score" in result
        assert "brightness" in result
        assert result["brightness"] >= 80  # Within reasonable range


class TestLightingCompensator:
    """Test LightingCompensator functionality"""

    def test_compensator_initialization_default(self):
        """Test compensator initializes with default config"""
        compensator = LightingCompensator()
        assert compensator.enabled is True
        assert compensator.adaptive_exposure is True
        assert compensator.auto_brightness is True
        assert compensator.histogram_eq is True
        assert compensator.low_light_mode == "auto"

    def test_compensator_initialization_custom(self):
        """Test compensator initializes with custom config"""
        config = {
            "enabled": False,
            "adaptive_exposure": False,
            "auto_brightness_adjust": False,
            "histogram_equalization": False,
            "low_light_mode": "never"
        }
        compensator = LightingCompensator(config)
        assert compensator.enabled is False
        assert compensator.adaptive_exposure is False
        assert compensator.auto_brightness is False
        assert compensator.histogram_eq is False
        assert compensator.low_light_mode == "never"

    def test_compensate_when_disabled(self):
        """Test that compensation is skipped when disabled"""
        config = {"enabled": False}
        compensator = LightingCompensator(config)
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
        analysis = {"brightness": 100, "is_low_light": False}

        result = compensator.compensate(frame, analysis)

        # Should return unmodified frame when disabled
        assert np.array_equal(result, frame)

    def test_compensate_dark_frame(self):
        """Test compensation enhances dark frame"""
        compensator = LightingCompensator()
        # Create dark frame
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 50
        analysis = {"brightness": 50, "is_low_light": True, "contrast": 20}

        result = compensator.compensate(frame, analysis)

        # Result should exist and be valid
        assert result is not None
        assert result.shape == frame.shape
        assert result.dtype == frame.dtype

    def test_compensate_bright_frame(self):
        """Test compensation handles bright frame appropriately"""
        compensator = LightingCompensator()
        # Create bright frame
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 200
        analysis = {"brightness": 200, "is_low_light": False, "is_high_light": True, "contrast": 50}

        result = compensator.compensate(frame, analysis)

        # Should return adjusted frame
        assert result is not None
        assert result.shape == frame.shape

    def test_compensate_low_contrast_frame(self):
        """Test compensation improves low contrast frame"""
        compensator = LightingCompensator()
        # Create low contrast frame (uniform gray)
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 120
        analysis = {"brightness": 120, "contrast": 10, "is_low_contrast": True}

        result = compensator.compensate(frame, analysis)

        # Should apply histogram equalization
        assert result is not None
        assert result.shape == frame.shape

    def test_compensate_adaptive_modes(self):
        """Test different low light modes"""
        # Test 'always' mode
        config_always = {"low_light_mode": "always"}
        compensator_always = LightingCompensator(config_always)
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 120
        analysis = {"brightness": 120, "is_low_light": False}
        
        result = compensator_always.compensate(frame, analysis)
        assert result is not None
        
        # Test 'never' mode
        config_never = {"low_light_mode": "never"}
        compensator_never = LightingCompensator(config_never)
        dark_frame = np.ones((480, 640, 3), dtype=np.uint8) * 50
        dark_analysis = {"brightness": 50, "is_low_light": True}
        
        result = compensator_never.compensate(dark_frame, dark_analysis)
        assert result is not None


class TestIntegration:
    """Test integration between analyzer and compensator"""

    def test_full_pipeline_dark_frame(self):
        """Test full analyze + compensate pipeline on dark frame"""
        analyzer = LightingAnalyzer()
        compensator = LightingCompensator()

        # Create dark frame
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 50

        # Analyze
        analysis = analyzer.analyze_frame(frame)
        assert "is_low_light" in analysis
        assert "brightness" in analysis

        # Compensate
        result = compensator.compensate(frame, analysis)
        assert result is not None
        assert result.shape == frame.shape

    def test_full_pipeline_good_frame(self):
        """Test full pipeline on well-lit frame"""
        analyzer = LightingAnalyzer()
        compensator = LightingCompensator()

        # Create good frame
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 120

        # Analyze
        analysis = analyzer.analyze_frame(frame)
        assert "brightness" in analysis
        assert "quality_score" in analysis

        # Compensate
        result = compensator.compensate(frame, analysis)
        assert result is not None
        assert result.shape == frame.shape

    def test_pipeline_with_custom_config(self):
        """Test pipeline with custom configurations"""
        analyzer_config = {"brightness_threshold": 90, "contrast_threshold": 45}
        compensator_config = {"enabled": True, "adaptive_exposure": True}
        
        analyzer = LightingAnalyzer(analyzer_config)
        compensator = LightingCompensator(compensator_config)
        
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
        
        analysis = analyzer.analyze_frame(frame)
        result = compensator.compensate(frame, analysis)
        
        assert result is not None
        assert result.shape == frame.shape
