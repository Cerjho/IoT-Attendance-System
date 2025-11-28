#!/usr/bin/env python3
"""
Hardware Test Script - Buzzer and RGB LED
Tests active buzzer on GPIO 16 and RGB LED on GPIO 11, 13, 15
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

load_dotenv()

import time

from src.hardware.buzzer_controller import BuzzerController
from src.hardware.rgb_led_controller import RGBLEDController
from src.utils.config_loader import load_config


def test_buzzer(buzzer: BuzzerController):
    """Test buzzer patterns"""
    print("\n" + "=" * 80)
    print("TESTING BUZZER (GPIO 16)")
    print("=" * 80)

    if not buzzer.enabled:
        print("❌ Buzzer is disabled")
        return

    print("\n🔊 Test 1: Simple beep")
    buzzer.beep_simple(200)
    time.sleep(1)

    print("🔊 Test 2: QR Detected pattern [100, 50, 100]")
    buzzer.beep_pattern([100, 50, 100], blocking=True)
    time.sleep(0.5)

    print("🔊 Test 3: Face Detected pattern [50]")
    buzzer.beep_pattern([50], blocking=True)
    time.sleep(0.5)

    print("🔊 Test 4: Success pattern [200, 100, 200, 100, 200]")
    buzzer.beep_pattern([200, 100, 200, 100, 200], blocking=True)
    time.sleep(0.5)

    print("🔊 Test 5: Error pattern [1000]")
    buzzer.beep_pattern([1000], blocking=True)
    time.sleep(0.5)

    print("🔊 Test 6: Duplicate pattern [100, 100, 100, 100, 100]")
    buzzer.beep_pattern([100, 100, 100, 100, 100], blocking=True)
    time.sleep(0.5)

    print("\n✅ Buzzer tests complete!")


def test_rgb_led(rgb: RGBLEDController):
    """Test RGB LED colors"""
    print("\n" + "=" * 80)
    print("TESTING RGB LED (GPIO R:11, G:13, B:15)")
    print("=" * 80)

    if not rgb.enabled:
        print("❌ RGB LED is disabled")
        return

    print("\n💡 Test 1: Primary Colors")
    print("   Red...")
    rgb.set_color(255, 0, 0)
    time.sleep(1)

    print("   Green...")
    rgb.set_color(0, 255, 0)
    time.sleep(1)

    print("   Blue...")
    rgb.set_color(0, 0, 255)
    time.sleep(1)

    rgb.off()
    time.sleep(0.5)

    print("\n💡 Test 2: Named Colors from Config")

    print("   QR Detected (Blue)...")
    rgb.show_color("qr_detected", fade=False, blocking=True)
    time.sleep(0.5)

    print("   Face Detected (Orange)...")
    rgb.show_color("face_detected", fade=False, blocking=True)
    time.sleep(0.5)

    print("   Success (Green)...")
    rgb.show_color("success", fade=False, blocking=True)
    time.sleep(0.5)

    print("   Error (Red)...")
    rgb.show_color("error", fade=False, blocking=True)
    time.sleep(0.5)

    print("   Duplicate (Yellow)...")
    rgb.show_color("duplicate", fade=False, blocking=True)
    time.sleep(0.5)

    print("   Late (Orange)...")
    rgb.show_color("late", fade=False, blocking=True)
    time.sleep(0.5)

    print("   Processing (Magenta)...")
    rgb.show_color("processing", fade=False, blocking=True)
    time.sleep(0.5)

    print("\n💡 Test 3: Fade Effect")
    print("   Fading to green...")
    rgb.fade_to_color(0, 255, 0, duration_ms=1000)
    time.sleep(1.5)

    print("   Fading to off...")
    rgb.fade_to_color(0, 0, 0, duration_ms=1000)
    time.sleep(1.5)

    print("\n💡 Test 4: Blink Effect")
    print("   Blinking red 3 times...")
    rgb.blink([255, 0, 0], times=3, on_time_ms=200, off_time_ms=200)
    time.sleep(2)

    print("\n💡 Test 5: Pulse Effect (Breathing)")
    print("   Pulsing blue...")
    rgb.pulse([0, 0, 255], duration_ms=2000, cycles=2)
    time.sleep(5)

    print("\n✅ RGB LED tests complete!")


def test_combined(buzzer: BuzzerController, rgb: RGBLEDController):
    """Test buzzer and RGB LED together"""
    print("\n" + "=" * 80)
    print("TESTING COMBINED EFFECTS")
    print("=" * 80)

    if not buzzer.enabled or not rgb.enabled:
        print("⚠️  Skipping combined tests (one or both devices disabled)")
        return

    print("\n🎭 Scenario 1: QR Code Detected")
    print("   Blue LED + Double beep")
    rgb.show_color("qr_detected", fade=True, blocking=False)
    buzzer.beep_pattern([100, 50, 100], blocking=False)
    time.sleep(3)

    print("\n🎭 Scenario 2: Face Detected")
    print("   Orange LED + Single beep")
    rgb.show_color("face_detected", fade=True, blocking=False)
    buzzer.beep_pattern([50], blocking=False)
    time.sleep(3)

    print("\n🎭 Scenario 3: Success")
    print("   Green LED + Success melody")
    rgb.show_color("success", fade=True, blocking=False)
    buzzer.beep_pattern([200, 100, 200, 100, 200], blocking=False)
    time.sleep(3)

    print("\n🎭 Scenario 4: Error")
    print("   Red LED + Long beep")
    rgb.show_color("error", fade=True, blocking=False)
    buzzer.beep_pattern([1000], blocking=False)
    time.sleep(3)

    print("\n🎭 Scenario 5: Duplicate Scan")
    print("   Yellow LED + Rapid beeps")
    rgb.show_color("duplicate", fade=True, blocking=False)
    buzzer.beep_pattern([100, 100, 100, 100, 100], blocking=False)
    time.sleep(3)

    print("\n✅ Combined tests complete!")


def main():
    """Run hardware tests"""
    print("=" * 80)
    print("HARDWARE TEST - BUZZER & RGB LED")
    print("=" * 80)
    print("\nHardware Configuration:")
    print("  • Buzzer: GPIO 16 (with 1kΩ resistor)")
    print("  • RGB LED Red: GPIO 11 (with 1kΩ resistor)")
    print("  • RGB LED Green: GPIO 13 (with 1kΩ resistor)")
    print("  • RGB LED Blue: GPIO 15 (with 1kΩ resistor)")
    print("\nLoading configuration...")

    # Load config
    config = load_config("config/config.json")

    # Initialize hardware
    print("Initializing hardware...")
    buzzer = BuzzerController(config.get("buzzer", {}))
    rgb = RGBLEDController(config.get("rgb_led", {}))

    try:
        # Run tests
        test_buzzer(buzzer)
        test_rgb_led(rgb)
        test_combined(buzzer, rgb)

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETE!")
        print("=" * 80)
        print("\n✅ Hardware is working correctly!")
        print("\nPress Ctrl+C to exit...")

        # Keep script running to see final state
        time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")

    except Exception as e:
        print(f"\n❌ Error during tests: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\nCleaning up GPIO...")
        buzzer.cleanup()
        rgb.cleanup()
        print("Done!")


if __name__ == "__main__":
    main()
