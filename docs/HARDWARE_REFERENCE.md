# Hardware Quick Reference

## GPIO Pin Assignments (BCM Mode)

```
Component       GPIO Pin    Resistor    Connection
─────────────────────────────────────────────────────────
Buzzer          23          1kΩ         GPIO → R → Buzzer(+) → Buzzer(-) → GND
RGB LED (Red)   17          1kΩ         GPIO → R → Anode
RGB LED (Green) 27          1kΩ         GPIO → R → Anode
RGB LED (Blue)  22          1kΩ         GPIO → R → Anode
Common Cathode  -           -           → GND
```

## Visual Feedback Colors

```
State               Color      RGB              Triggered When
─────────────────────────────────────────────────────────────────
QR Detected        Blue       (0, 0, 255)      Student scans QR
Face Detected      Orange     (255, 165, 0)    Face appears
Success            Green      (0, 255, 0)      Attendance saved
Error              Red        (255, 0, 0)      Failed/No face
Duplicate          Yellow     (255, 255, 0)    Already scanned
Late               Orange     (255, 165, 0)    Late arrival
Processing         Magenta    (255, 0, 255)    System processing
```

## Audio Feedback Patterns

```
Event              Pattern (ms)               Description
───────────────────────────────────────────────────────────
QR Detected        [100, 50, 100]            Double beep
Face Detected      [50]                      Quick beep
Success            [200, 100, 200, 100, 200] Success melody
Error              [1000]                    Long beep
Duplicate          [100, 100, 100, 100, 100] Rapid beeps
```

## Testing

```bash
# Test all hardware
python3 tests/test_hardware.py

# Run attendance system
python3 attendance_system.py
```

## Configuration Files

- **Hardware config**: `config/config.json` → buzzer & rgb_led sections
- **Controller code**: `src/hardware/buzzer_controller.py` & `rgb_led_controller.py`
- **Integration**: `attendance_system.py`
- **Test script**: `tests/test_hardware.py`

## Common Issues

**LED not working:**
- Check pin connections (R=17, G=27, B=22)
- Verify 1kΩ resistors
- Confirm common cathode type (not common anode)
- Test with: `python3 tests/test_hardware.py`

**Buzzer not working:**
- Check GPIO 23 connection
- Verify 1kΩ resistor
- Test with: `python3 tests/test_hardware.py`

## Customization

Edit `config/config.json`:

```json
"rgb_led": {
  "brightness": 100,          // 0-100%
  "fade_duration_ms": 500,    // Fade speed
  "hold_duration_ms": 2000,   // Display time
  "colors": {
    "success": [0, 255, 0]    // Change colors [R, G, B]
  }
}
```
