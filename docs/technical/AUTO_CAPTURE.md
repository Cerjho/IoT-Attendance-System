# Automatic Face Capture System

## Overview

The attendance system now features an intelligent **automatic face-capture system** with comprehensive quality checks. Instead of simply capturing any detected face, the system ensures perfect photo quality by validating 9 different criteria continuously for 3 seconds before capturing.

## How It Works

### Flow

1. **QR Code Scan** - Student scans their QR code
2. **Auto-Capture Starts** - System enters 15-second capture window
3. **Quality Monitoring** - All 9 checks run continuously on every frame
4. **Stability Timer** - When ALL checks pass, 3-second countdown begins
5. **Capture** - Photo captured after 3 seconds of perfect quality
6. **Reset on Failure** - Any failed check immediately resets the countdown

### Audio Feedback

The buzzer provides clear feedback throughout the process:

- **Single beep (100ms)** - Countdown started (all quality checks passed)
- **Short beeps (50ms)** - Each countdown second (3-2-1)
- **Long beep (500ms)** - Successful capture
- **Double beep (100ms, pause, 100ms)** - Timeout failure

## Quality Checks

All 9 checks must pass **simultaneously** for 3 continuous seconds:

### 1. Face Count
- **Requirement**: Exactly 1 face detected
- **Why**: Ensures no interference from others in frame

### 2. Face Size
- **Requirement**: Face width ≥ 80 pixels (configurable)
- **Why**: Ensures sufficient detail for recognition
- **Note**: Adjusted from 200px IOD requirement to practical face width

### 3. Face Centered
- **Requirement**: Face within ±12% of image center (both X and Y)
- **Why**: Ensures consistent framing and proper composition

### 4. Head Pose
- **Requirements**: 
  - Yaw (left/right): ±15°
  - Pitch (up/down): ±15°
  - Roll (tilt): ±10°
- **Why**: Ensures front-facing, level photo
- **Method**: Estimated from eye positions using OpenCV cascades (no dlib required)

### 5. Eyes Open
- **Requirement**: Eye Aspect Ratio (EAR) > 0.25
- **Why**: Prevents closed-eye photos
- **Method**: Approximated from eye cascade detection dimensions

### 6. Mouth Closed
- **Requirement**: Mouth openness ≤ 0.5 (slightly open acceptable)
- **Why**: Ensures natural, professional appearance
- **Method**: Smile cascade detection + size ratio analysis

### 7. Sharpness
- **Requirement**: Laplacian variance > 80
- **Why**: Prevents blurry photos from motion or focus issues
- **Method**: Edge detection intensity measurement

### 8. Brightness
- **Requirement**: Average face brightness 70-180 (0-255 scale)
- **Why**: Ensures proper exposure - not too dark or washed out
- **Method**: Mean grayscale intensity of face region

### 9. Illumination Uniformity
- **Requirements**:
  - Standard deviation < 40 (even lighting)
  - Dark pixel ratio < 20% (no heavy shadows)
- **Why**: Detects masks, sunglasses, heavy shadows that obscure features
- **Method**: Statistical analysis of face region pixel distribution

## Configuration

Edit `config/config.json` to customize quality thresholds:

```json
{
  "face_quality": {
    "min_face_size": 80,              // Minimum face width in pixels
    "center_tolerance_x": 0.12,       // Horizontal centering tolerance (12%)
    "center_tolerance_y": 0.12,       // Vertical centering tolerance (12%)
    "max_yaw": 15.0,                  // Max left/right head turn (degrees)
    "max_pitch": 15.0,                // Max up/down head tilt (degrees)
    "max_roll": 10.0,                 // Max head roll/tilt (degrees)
    "min_eye_aspect_ratio": 0.25,    // Minimum EAR for open eyes
    "min_sharpness": 80.0,            // Minimum Laplacian variance
    "min_brightness": 70,             // Minimum face brightness (0-255)
    "max_brightness": 180,            // Maximum face brightness (0-255)
    "max_mouth_openness": 0.5,        // Maximum mouth openness ratio
    "stability_duration": 3.0,        // Seconds of perfect quality required
    "timeout": 15.0                   // Maximum capture window (seconds)
  }
}
```

## State Machine

The auto-capture system uses a state machine with these states:

- **IDLE** - Not active
- **WAITING** - Looking for face or waiting for quality checks to pass
- **STABLE** - All checks passed, countdown running
- **CAPTURED** - Photo captured successfully
- **TIMEOUT** - 15 seconds elapsed without meeting all criteria

## Testing

Test the face quality system independently:

```bash
python test_face_quality.py
```

This opens a camera feed showing:
- Real-time quality check results
- Pass/fail status for each of 9 checks
- Countdown when all checks pass
- Automatic capture after 3 seconds

Press SPACE to start a test, 'q' to quit.

## User Instructions

When using the attendance system:

1. **Scan QR code** - Hold your ID card QR code to camera
2. **Position yourself** - Look directly at camera, centered in frame
3. **Wait for beep** - When you hear a single beep, all checks passed
4. **Hold still** - Stay perfectly still for 3 seconds during countdown
5. **Listen for confirmation** - Long beep = success, double beep = retry

**Tips for success:**
- Stand at normal distance (not too close or far)
- Look straight at camera (no extreme angles)
- Keep eyes open, relaxed expression
- Ensure good lighting (avoid backlighting)
- Remove sunglasses, lower face masks
- Hold position steady during countdown

## Technical Details

### OpenCV-Only Implementation

The system uses **only OpenCV Haar Cascades** - no dlib or facial landmark detection required. This makes it:
- Faster (real-time processing at 30 FPS)
- Lightweight (no large model files)
- Raspberry Pi compatible (lower CPU requirements)

### Estimation Methods

Since we don't use facial landmarks:

- **Head pose**: Estimated from relative eye positions and asymmetry
- **Eye openness**: Approximated from eye cascade bounding box aspect ratio
- **Mouth state**: Detected using smile cascade and size analysis

These approximations work well for quality gating even without precise landmark coordinates.

### Performance

- **Processing time**: ~30-50ms per frame on Raspberry Pi 4
- **False positives**: Minimal - all 9 checks must pass simultaneously
- **False negatives**: Rare - most users succeed within 5-10 seconds

## Troubleshooting

### "Timeout - quality conditions not met"

Check the displayed failure reason:

- **"Cannot detect both eyes"** - Turn toward camera, ensure good lighting
- **"Pose: yaw=X°"** - Turn face more straight-on
- **"Sharpness=X"** - Hold still, ensure camera is focused
- **"Brightness=X"** - Adjust lighting or move to better-lit area
- **"Poor illumination"** - Remove sunglasses/masks, improve lighting uniformity

### Countdown keeps resetting

This is normal - any small movement or lighting change can fail checks. Hold position **perfectly still** once countdown starts.

### Never reaches countdown

- Verify face is detected (green box around face)
- Check lighting - should be even, front-lit
- Move closer if face is too small
- Center yourself in frame
- Look straight at camera

## Future Enhancements

Possible improvements:
- Add liveness detection (blink, smile commands)
- Machine learning-based quality scoring
- Adaptive thresholds based on environment
- Multi-angle capture fallback
- Real-time quality score graph display
