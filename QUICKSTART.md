# IoT Face Detection & Photo Capture - Quick Start

## 🚀 5-Minute Setup

### 1. Initial Setup
```bash
cd /home/iot/attendance-system
chmod +x setup.sh
./setup.sh
source venv/bin/activate  # IMPORTANT: Always activate venv before running
```

**Note:** The virtual environment MUST have access to system site packages (specifically `picamera2` for Raspberry Pi camera support). The setup script now creates the venv with `--system-site-packages` flag.

### 2. Test Demo Mode (No Camera Needed)
```bash
source venv/bin/activate  # Must activate venv first!
python main.py --demo
```

**Output:**
- ✓ Simulates face detection events
- ✓ Simulates photo capture
- ✓ Generates detection log (JSON)
- ✓ Exports statistics

### 3. Check System Status
```bash
source venv/bin/activate  # Must activate venv first!
python check_status.py
```

**Should show:**
- ✓ Configuration loaded
- ✓ Camera: Online (or ready if not connected)
- ✓ All directories present
- ✓ All files present

## 📷 With Camera (When Connected)

### Connect Camera
- **USB**: Plug USB camera into Pi USB port
- **CSI**: Connect camera module to CSI ribbon connector

### List Available Cameras
```bash
ls /dev/video*
```

### Run with Camera
```bash
source venv/bin/activate  # Must activate venv first!
python main.py
```

**What happens:**
- Detects faces in the video stream
- Captures photos of detected faces
- Logs detection events
- Press 'q' to quit

## 📁 Output Files

### Captured Photos
```
photos/face_capture_YYYYMMDD_HHMMSS_NNN_M.jpg
```
- Automatically saved when faces are detected
- Organized by timestamp

### Detection Log
```
logs/detection_log_YYYYMMDD_HHMMSS.json
```
- JSON format with all detection events
- Face count and photo list
- Summary statistics

**View the log:**
```bash
cat logs/detection_log_*.json
```

## ⚙️ Configuration

### Camera Settings
Edit `config/config.json`:

```json
{
  "camera": {
    "index": 0,              // 0 = /dev/video0, 1 = /dev/video1, etc.
    "resolution": {
      "width": 640,          // 320-1920
      "height": 480          // 240-1080
    },
    "fps": 30
  }
}
```

### Change Camera Device
If you have multiple cameras:
```bash
# Find available cameras
ls -la /dev/video*

# Update config
nano config/config.json
# Change "index": 0 to "index": 1, etc.
```

### Lower Resolution for Faster Processing
```json
"resolution": {
  "width": 320,
  "height": 240
}
```

## 🔧 Troubleshooting

### "Failed to get frame" Error
**This is normal if:**
- No camera is connected
- Camera is already in use by another application
- Wrong camera index in config

**Solution:**
```bash
# Check available cameras
ls /dev/video*

# Update camera index in config.json if needed
# Restart the system
```

### Camera Works but No Detections
**Possible causes:**
- Poor lighting (need well-lit environment)
- Camera angle is wrong
- Face is too far/close from camera
- Resolution too low

**Solutions:**
- Ensure good lighting
- Position camera 1-2 meters from face
- Try higher resolution in config
- Test with `python check_status.py`

### System Hangs or Slow Performance
**Solutions:**
```json
{
  "camera": {
    "resolution": {
      "width": 320,
      "height": 240
    }
  }
}
```

Lower resolution = faster processing

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or reinstall from scratch
rm -rf venv
./setup.sh
```

## 📊 Common Commands

```bash
# Demo mode (no camera)
python main.py --demo

# Live mode (requires camera)
python main.py

# System status
python check_status.py

# View detection logs
ls -lh logs/

# View captured photos
ls -lh photos/

# View latest log
tail -f logs/detection_log_*.json

# Check log files
cat logs/attendance_system_*.log
```

## 💡 Tips & Tricks

### Test Camera Before Running
```bash
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print('✓ Camera online')
    cap.release()
else:
    print('✗ Camera offline')
"
```

### View System Logs
```bash
# Real-time log
tail -f logs/attendance_system_*.log

# Search for errors
grep ERROR logs/attendance_system_*.log
```

### Export Detection Data
```bash
# Copy detection log
cp logs/detection_log_*.json detection_backup.json

# View JSON
cat logs/detection_log_*.json | python -m json.tool
```

### Performance Monitoring
```bash
# Check CPU usage
top

# Check memory
free -h

# Check disk space
df -h
```

## 🎯 Next Steps

1. **Test without camera:**
   ```bash
   python main.py --demo
   ```

2. **Connect a camera** (USB or CSI)

3. **Run the system:**
   ```bash
   python main.py
   ```

4. **Check outputs:**
   ```bash
   ls photos/              # Captured images
   cat logs/detection_log_*.json   # Detection events
   ```

5. **Extend the system:**
   - Add facial recognition
   - Integrate with web dashboard
   - Add cloud storage
   - Custom processing on photos

## 📚 Documentation

- **README.md** - Complete system documentation
- **config/config.json** - All available settings
- **main.py** - Main application code
- **src/detection_only.py** - Core detection logic

## ✅ Success Indicators

**System is working if:**
- ✓ `python main.py --demo` completes successfully
- ✓ `python check_status.py` shows all green
- ✓ Detection logs are created in `logs/`
- ✓ No import errors

**Camera is working if:**
- ✓ `ls /dev/video*` shows at least one device
- ✓ `python check_status.py` shows "Camera: ✓ Online"
- ✓ `python main.py` starts without camera errors

---

**Version:** 1.0.0  
**Last Updated:** November 20, 2025  
**Status:** ✅ Production Ready
