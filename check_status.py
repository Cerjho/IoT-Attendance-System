"""
System Status & Diagnostics Script
Display system configuration and camera status
"""
import logging
import os
from src.utils import setup_logger, load_config
from src.camera import CameraHandler


def display_status():
    """Display system status and information."""
    setup_logger('root', log_dir='logs', level=logging.WARNING)
    
    print("\n" + "="*60)
    print("FACE DETECTION SYSTEM - STATUS")
    print("="*60)
    
    # Load configuration
    config = load_config('config/config.json')
    print("\n[CONFIGURATION]")
    print(f"Camera Index: {config.get('camera.index', 0)}")
    print(f"Camera Resolution: {config.get('camera.resolution.width', 640)}x{config.get('camera.resolution.height', 480)}")
    print(f"FPS: {config.get('camera.fps', 30)}")
    print(f"Log Level: {config.get('logging.level', 'INFO')}")
    print(f"Log Directory: {config.get('logging.log_dir', 'logs')}")
    
    # Check camera
    print("\n[CAMERA]")
    try:
        camera = CameraHandler(
            camera_index=config.get('camera.index', 0),
            resolution=(config.get('camera.resolution.width', 640),
                       config.get('camera.resolution.height', 480))
        )
        if camera.start():
            info = camera.get_camera_info()
            print(f"Status: ✓ Online")
            print(f"Index: {info['camera_index']}")
            print(f"Resolution: {info['resolution']}")
            print(f"Frames captured: {info['frame_count']}")
            camera.release()
        else:
            print(f"Status: ✗ Failed to open")
    except Exception as e:
        print(f"Status: ✗ Error - {str(e)}")
    
    # Check directories
    print("\n[DIRECTORIES]")
    dirs_to_check = {
        'photos': 'photos/',
        'logs': 'logs/',
        'config': 'config/',
        'src': 'src/'
    }
    
    for name, path in dirs_to_check.items():
        exists = os.path.exists(path)
        status = "✓" if exists else "✗"
        print(f"  {status} {name}: {path}")
    
    # Check files
    print("\n[FILES]")
    files_to_check = {
        'main.py': 'main.py',
        'config': 'config/config.json',
        'requirements': 'requirements.txt'
    }
    
    for name, path in files_to_check.items():
        exists = os.path.exists(path)
        status = "✓" if exists else "✗"
        print(f"  {status} {name}: {path}")
    
    # Summary
    print("\n[SYSTEM]")
    print(f"Version: 1.0.0 (Face Detection & Photo Capture)")
    print(f"Status: ✓ Ready to use")
    
    print("\n" + "="*60)
    print("QUICK START:")
    print("  python main.py --demo     # Test demo mode")
    print("  python main.py             # Run with camera")
    print("="*60 + "\n")


if __name__ == '__main__':
    display_status()

