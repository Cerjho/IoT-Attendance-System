#!/bin/bash
# Detect available cameras and their capabilities
# Helps identify the correct camera index for the attendance system

echo "======================================================================"
echo "CAMERA DETECTION UTILITY"
echo "======================================================================"
echo ""

# Check if v4l-utils is installed
if ! command -v v4l2-ctl &> /dev/null; then
    echo "⚠️  v4l2-ctl not found. Install with: sudo apt install v4l-utils"
    echo ""
fi

echo "📹 Video devices found:"
echo "----------------------------------------------------------------------"
ls -la /dev/video* 2>/dev/null || echo "No video devices found"
echo ""

echo "======================================================================"
echo "Testing camera indices with Python/OpenCV..."
echo "======================================================================"
echo ""

python3 << 'PYTHON_EOF'
import cv2
import sys

def test_camera(index):
    """Test if a camera index works and get info"""
    try:
        cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
        
        if cap.isOpened():
            # Get properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            
            # Try to read a frame
            ret, frame = cap.read()
            frame_status = "✅ WORKS" if ret and frame is not None else "❌ NO FRAMES"
            
            cap.release()
            
            return True, f"{width}x{height} @ {fps}fps", frame_status
        else:
            return False, None, None
    except Exception as e:
        return False, None, str(e)

print("Testing camera indices 0-5...\n")

working_cameras = []

for i in range(6):
    opened, info, frame_status = test_camera(i)
    
    if opened:
        print(f"📷 Camera {i}: {frame_status}")
        print(f"   Resolution: {info}")
        if frame_status == "✅ WORKS":
            working_cameras.append(i)
            print(f"   ✓ This camera can capture frames!\n")
        else:
            print(f"   ⚠️  Camera opened but cannot read frames\n")
    else:
        print(f"❌ Camera {i}: Not available\n")

print("======================================================================")
print("SUMMARY")
print("======================================================================")

if working_cameras:
    print(f"\n✅ Working cameras found at indices: {working_cameras}")
    print(f"\n💡 Recommended action:")
    print(f"   Edit config/config.json and set:")
    print(f"   \"camera\": {{")
    print(f"     \"index\": {working_cameras[0]},")
    print(f"     ...")
    print(f"   }}")
    print("")
else:
    print("\n❌ No working cameras found!")
    print("\n💡 Possible solutions:")
    print("   1. Check camera is properly connected")
    print("   2. Check camera permissions: ls -la /dev/video*")
    print("   3. Add user to video group: sudo usermod -a -G video $USER")
    print("   4. Try Picamera2 if using Raspberry Pi Camera Module")
    print("   5. Use demo mode: python attendance_system.py --demo")
    print("")

PYTHON_EOF

echo ""
echo "======================================================================"
echo "If you have v4l-utils installed, you can get detailed info with:"
echo "  v4l2-ctl --list-devices"
echo "  v4l2-ctl -d /dev/video0 --all"
echo "======================================================================"
