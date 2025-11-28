#!/usr/bin/env python3
"""Hardware Check Script
Cycles buzzer patterns and RGB LED colors, and listens for power button presses.

Usage:
  python scripts/hw_check.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__) + '/..')

from src.utils import load_config, setup_logger
from src.hardware import BuzzerController
from src.hardware.rgb_led_controller import RGBLEDController
from src.hardware.power_button import PowerButtonController


def main():
    setup_logger("hw_check")
    cfg = load_config("config/config.json").get_all()

    # Buzzer
    buzzer_cfg = cfg.get("buzzer", {})
    buzzer_cfg["patterns"] = {
        "qr_detected": buzzer_cfg.get("qr_detected_pattern", [100, 50, 100]),
        "face_detected": buzzer_cfg.get("face_detected_pattern", [50]),
        "success": buzzer_cfg.get("success_pattern", [200, 100, 200, 100, 200]),
        "error": buzzer_cfg.get("error_pattern", [1000]),
        "duplicate": buzzer_cfg.get("duplicate_pattern", [100, 100, 100, 100, 100]),
    }
    buzzer = BuzzerController(buzzer_cfg)

    # RGB LED
    led_cfg = cfg.get("rgb_led", {})
    rgb = RGBLEDController(led_cfg)

    # Power button
    pb_cfg = cfg.get("power_button", {})
    button = PowerButtonController(pb_cfg)

    print("\n=== Hardware Check ===")
    print("1) Cycling buzzer patterns...")
    for pattern in ["qr_detected", "face_detected", "success", "error", "duplicate"]:
        print(f"  - Beep: {pattern}")
        buzzer.beep(pattern)
        time.sleep(0.5)

    print("2) Cycling RGB LED colors...")
    sequence = [
        ("success", "green"),
        ("error", "red"),
        ("qr_detected", "blue"),
        ("duplicate", "yellow"),
    ]
    for name, _ in sequence:
        rgb.show_color(name, fade=True, blocking=False)
        time.sleep(1.0)

    print("3) Listening for power button (10 seconds)... Press button now.")
    button.start_monitoring()
    start = time.time()
    try:
        while time.time() - start < 10:
            time.sleep(0.1)
    finally:
        # Cleanup
        button.cleanup()
        rgb.cleanup()
        buzzer.cleanup()

    print("\nDone. If you heard beeps, saw LED colors, and button press was logged, hardware is OK.")


if __name__ == "__main__":
    main()
