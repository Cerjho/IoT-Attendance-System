#!/usr/bin/env python3
"""
Test script for Face Quality Checker
Tests all 9 quality checks with camera feed
"""
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from src.face_quality import AutoCaptureStateMachine, FaceQualityChecker

# Simple face detector (inlined since detection_only was removed)
class SimpleFaceDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    
    def detect_faces(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
        return [(x, y, w, h) for (x, y, w, h) in faces]


def main():
    print("\n" + "=" * 70)
    print("🧪 Face Quality Checker Test")
    print("=" * 70)

    # Initialize components
    print("\n[1] Initializing components...")
    quality_checker = FaceQualityChecker()
    auto_capture = AutoCaptureStateMachine(
        quality_checker, stability_duration=3.0, timeout=15.0
    )
    face_detector = SimpleFaceDetector()

    # Try to open camera
    print("\n[2] Opening camera...")
    try:
        from src.camera import CameraHandler

        camera = CameraHandler(
            {"camera": {"index": 0, "resolution": {"width": 640, "height": 480}}}
        )
        camera.start()
        print("✓ Camera initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize camera: {e}")
        print("  Falling back to default OpenCV camera...")
        camera = None
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("✗ Cannot open camera")
            return

    print("\n[3] Starting test...")
    print("Instructions:")
    print("  - Press SPACE to start auto-capture test")
    print("  - Press 'q' to quit")
    print("  - Look at the camera and hold still when all checks pass")
    print("\n" + "=" * 70 + "\n")

    testing = False
    last_countdown = None

    try:
        while True:
            # Get frame
            if camera:
                frame = camera.get_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
            else:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to read frame")
                    break

            display_frame = frame.copy()

            # Detect faces
            faces = face_detector.detect_faces(frame)

            # Get largest face
            largest_face = None
            if len(faces) > 0:
                largest_face = max(faces, key=lambda f: f[2] * f[3])

            # Draw face boxes
            for x, y, w, h in faces:
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Run quality checks if testing
            if testing and largest_face:
                # Update auto-capture
                status = auto_capture.update(frame, largest_face)

                # Display status
                state_colors = {
                    "IDLE": (128, 128, 128),
                    "WAITING": (0, 255, 255),
                    "STABLE": (0, 255, 0),
                    "CAPTURED": (0, 255, 0),
                    "TIMEOUT": (0, 0, 255),
                }
                color = state_colors.get(status["state"], (255, 255, 255))

                cv2.putText(
                    display_frame,
                    f"State: {status['state']}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )
                cv2.putText(
                    display_frame,
                    status["message"],
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )

                # Display countdown
                if status.get("countdown"):
                    countdown = status["countdown"]
                    cv2.putText(
                        display_frame,
                        str(countdown),
                        (display_frame.shape[1] // 2 - 50, display_frame.shape[0] // 2),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        4.0,
                        (0, 255, 0),
                        8,
                    )

                    # Print countdown changes
                    if countdown != last_countdown:
                        print(f"⏱️  Countdown: {countdown}")
                        last_countdown = countdown

                # Display quality checks
                quality_result = status.get("quality_result")
                if quality_result:
                    y_offset = 100
                    checks = quality_result.get("checks", {})
                    for check_name, check_result in checks.items():
                        passed = check_result.get("passed", False)
                        check_color = (0, 255, 0) if passed else (0, 0, 255)
                        symbol = "✓" if passed else "✗"
                        text = f"{symbol} {check_name}: {check_result.get('reason', 'N/A')}"
                        cv2.putText(
                            display_frame,
                            text,
                            (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.4,
                            check_color,
                            1,
                        )
                        y_offset += 20

                # Check if capture triggered
                if status["should_capture"]:
                    print("\n🎉 CAPTURE TRIGGERED!")
                    print(f"   Quality score: {status['quality_result']['score']:.2f}")
                    print(f"   Stability time: {status['stability_elapsed']:.1f}s")

                    # Save test image
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"test_capture_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"   Saved: {filename}\n")

                    # Reset for next test
                    testing = False
                    auto_capture.reset()
                    last_countdown = None

                # Check timeout
                elif status["state"] == "TIMEOUT":
                    print("\n⏱️  TIMEOUT - Quality conditions not met within 15 seconds")
                    if quality_result:
                        print(f"   Last failure: {quality_result['reason']}\n")
                    testing = False
                    auto_capture.reset()
                    last_countdown = None

            elif testing and not largest_face:
                cv2.putText(
                    display_frame,
                    "Waiting for face...",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            else:
                cv2.putText(
                    display_frame,
                    "Press SPACE to start test",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            # Display frame
            cv2.imshow("Face Quality Test", display_frame)

            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord(" ") and not testing:
                print("\n🎬 Starting auto-capture test...")
                auto_capture.start_session()
                testing = True
                last_countdown = None

    except KeyboardInterrupt:
        print("\n\nTest interrupted")

    finally:
        print("\nCleaning up...")
        if camera:
            camera.stop()
        else:
            cap.release()
        cv2.destroyAllWindows()
        print("Done!")


if __name__ == "__main__":
    main()
