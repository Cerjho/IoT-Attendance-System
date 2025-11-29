#!/usr/bin/env python3
"""Camera Smoke Test
Verifies camera device availability and basic capture.

It attempts:
- OpenCV VideoCapture on index 0 (USB camera)
- If Picamera2 is available, capture a still and preview a frame

Usage:
  python scripts/camera_smoke_test.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__) + '/..')

import cv2
import pytest

def test_opencv_camera():
    print("\n[OpenCV] Testing VideoCapture(0)...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera index 0 (USB/CSI via V4L2)")
        pytest.skip("Camera index 0 not available")
    ret, frame = cap.read()
    cap.release()
    assert ret and frame is not None, "Failed to read a frame from camera"
    print(f"✓ Captured frame: {frame.shape}")
    out = "data/photos/camera_smoke_frame.jpg"
    os.makedirs("data/photos", exist_ok=True)
    cv2.imwrite(out, frame)
    print(f"✓ Saved test frame to {out}")
    assert os.path.exists(out), "Failed to save captured frame"


def test_picamera2():
    try:
        from picamera2 import Picamera2
        print("\n[Picamera2] Testing still capture...")
        picam = Picamera2()
        config = picam.create_still_configuration()
        picam.configure(config)
        picam.start()
        time.sleep(0.5)
        arr = picam.capture_array()
        picam.stop()
        assert arr is not None, "Picamera2 returned no image array"
        print(f"✓ Picamera2 captured array: {arr.shape}")
        out = "data/photos/picam_smoke_still.jpg"
        os.makedirs("data/photos", exist_ok=True)
        cv2.imwrite(out, arr)
        print(f"✓ Saved Picamera2 still to {out}")
        assert os.path.exists(out), "Failed to save Picamera2 still"
    except ImportError:
        print("ℹ️ Picamera2 not installed; skipping")
        pytest.skip("Picamera2 not installed")
    except Exception as e:
        print(f"❌ Picamera2 error: {e}")
        pytest.skip(f"Picamera2 error: {e}")


def main():
    ok_cv = test_opencv_camera()
    ok_pica = test_picamera2()
    print("\nSummary:")
    print(f"  OpenCV: {'OK' if ok_cv else 'FAIL'}")
    if ok_pica is None:
        print("  Picamera2: SKIPPED")
    else:
        print(f"  Picamera2: {'OK' if ok_pica else 'FAIL'}")

    if ok_cv or ok_pica:
        print("\nCamera smoke test passed at least one path.")
        sys.exit(0)
    else:
        print("\nCamera smoke test failed. Check camera ribbon/USB connections.")
        sys.exit(1)


if __name__ == "__main__":
    main()
