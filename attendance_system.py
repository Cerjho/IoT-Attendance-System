#!/usr/bin/env python3
"""
IoT Attendance System - Complete Flow
QR Scan → Face Detection → Photo Capture → Database Upload

Flow:
1. Standby - Wait for QR code scan
2. QR Detected - Validate student ID
3. Face Detection - 2 second window to detect and capture face
4. Upload to Database - Save attendance record with photo
5. Return to Standby - Wait for next student
"""
import cv2
import sys
import os
import time
import logging
import warnings
import ctypes
from datetime import datetime
from pyzbar import pyzbar
import numpy as np

# Suppress ZBar decoder warnings by redirecting stderr temporarily
class SuppressStderr:
    def __enter__(self):
        self.original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr.close()
        sys.stderr = self.original_stderr

warnings.filterwarnings('ignore', category=DeprecationWarning)

sys.path.insert(0, os.path.dirname(__file__))

from src.utils import setup_logger, load_config
from src.camera import CameraHandler
from src.detection_only import SimpleFaceDetector
from src.database import AttendanceDatabase
from src.database.sync_queue import SyncQueueManager
from src.hardware import BuzzerController
from src.lighting import LightingAnalyzer, LightingCompensator
from src.network import ConnectivityMonitor
from src.cloud import CloudSyncManager
from src.notifications import SMSNotifier
from src.attendance.schedule_manager import ScheduleManager
import threading

logger = logging.getLogger(__name__)


class IoTAttendanceSystem:
    """
    Complete IoT Attendance System
    QR Code + Face Detection + Photo Capture + Database
    """
    
    def __init__(self, config_file: str = None):
        """Initialize the system"""
        self.config = load_config(config_file or 'config/config.json')
        
        # Create directories
        os.makedirs('data/photos', exist_ok=True)
        os.makedirs('data/logs', exist_ok=True)
        os.makedirs('data', exist_ok=True)
        
        # Initialize components
        self.camera = None
        self.face_detector = SimpleFaceDetector()
        self.database = AttendanceDatabase('data/attendance.db')
        
        # Initialize new components
        self.sync_queue = SyncQueueManager('data/attendance.db')
        self.connectivity = ConnectivityMonitor(self.config.get('offline_mode', {}))
        
        # Initialize buzzer
        buzzer_config = self.config.get('buzzer', {})
        buzzer_config['patterns'] = {
            'qr_detected': buzzer_config.get('qr_detected_pattern', [100, 50, 100]),
            'face_detected': buzzer_config.get('face_detected_pattern', [50]),
            'success': buzzer_config.get('success_pattern', [200, 100, 200, 100, 200]),
            'error': buzzer_config.get('error_pattern', [1000]),
            'duplicate': buzzer_config.get('duplicate_pattern', [100, 100, 100, 100, 100])
        }
        self.buzzer = BuzzerController(buzzer_config)
        
        # Initialize lighting components
        lighting_config = self.config.get('lighting', {})
        self.lighting_analyzer = LightingAnalyzer(lighting_config)
        self.lighting_compensator = LightingCompensator(lighting_config)
        self.lighting_enabled = lighting_config.get('enabled', True)
        
        # Initialize cloud sync
        cloud_config = self.config.get('cloud', {})
        # Get credentials from environment or config
        cloud_config['url'] = os.getenv('SUPABASE_URL', cloud_config.get('url'))
        cloud_config['api_key'] = os.getenv('SUPABASE_KEY', cloud_config.get('api_key'))
        cloud_config['device_id'] = os.getenv('DEVICE_ID', cloud_config.get('device_id', 'device_001'))
        self.cloud_sync = CloudSyncManager(cloud_config, self.sync_queue, self.connectivity)
        
        # Initialize SMS notifications
        sms_config = self.config.get('sms_notifications', {})
        self.sms_notifier = SMSNotifier(sms_config)
        
        # Initialize roster sync manager (Supabase as primary, SQLite as cache)
        self.roster_sync = RosterSyncManager(cloud_config, self.database.db_path)
        
        # Initialize schedule manager for school schedule
        self.schedule_manager = ScheduleManager(self.config)
        
        # Auto-sync roster on startup
        if self.roster_sync.enabled:
            logger.info("Starting roster sync on system startup...")
            sync_result = self.roster_sync.auto_sync_on_startup()
            if sync_result['success']:
                logger.info(f"✅ Roster synced: {sync_result['students_synced']} students cached for today")
                print(f"✅ Roster synced: {sync_result['students_synced']} students cached")
            else:
                logger.warning(f"⚠️  Roster sync failed: {sync_result['message']}")
                print(f"⚠️  Roster sync failed: {sync_result['message']}")
        
        # Start background sync thread if cloud enabled
        self.sync_thread = None
        if self.cloud_sync.enabled:
            self.sync_thread = threading.Thread(target=self._background_sync_loop, daemon=True)
            self.sync_thread.start()
            logger.info("Background sync thread started")
        
        # System state
        self.state = 'STANDBY'  # STANDBY, QR_DETECTED, CAPTURING, UPLOADING
        
        # Settings
        self.capture_window = 5.0  # Seconds to capture face after QR scan
        self.face_detect_timeout = 5.0  # Max time to wait for face detection
        # Photo settings (new)
        self.save_full_frame = bool(self.config.get('photo.save_full_frame', False))
        self.crop_padding = int(self.config.get('photo.crop_padding', 20))
        self.extra_top = int(self.config.get('photo.extra_top', 0))
        self.preview_draw_crop_box = bool(self.config.get('photo.preview_draw_crop_box', True))
        self.jpeg_quality = int(self.config.get('photo.jpeg_quality', 95))
        self.use_high_res_still = bool(self.config.get('photo.use_high_res_still', True))
        self.still_width = int(self.config.get('photo.still_resolution.width', 0) or 0)
        self.still_height = int(self.config.get('photo.still_resolution.height', 0) or 0)
        self.still_settle_ms = int(self.config.get('photo.still_settle_ms', 700))
        # Image processing settings
        self.denoise_enabled = bool(self.config.get('image_processing.denoise_enabled', False))
        self.denoise_h = int(self.config.get('image_processing.denoise_h', 7))
        self.denoise_hColor = int(self.config.get('image_processing.denoise_hColor', 7))
        self.denoise_templateWindowSize = int(self.config.get('image_processing.denoise_templateWindowSize', 7))
        self.denoise_searchWindowSize = int(self.config.get('image_processing.denoise_searchWindowSize', 21))
        self.prefer_isp_color = bool(self.config.get('image_processing.prefer_isp_color', True))
        self.awb_grayworld_enabled = bool(self.config.get('image_processing.awb_grayworld_enabled', False))
        self.neutral_balance_enabled = bool(self.config.get('image_processing.neutral_balance_enabled', False))
        self.neutral_balance_strength = float(self.config.get('image_processing.neutral_balance_strength', 0.3))
        self.clahe_enabled = bool(self.config.get('image_processing.clahe_enabled', False))
        self.clahe_clip_limit = float(self.config.get('image_processing.clahe_clip_limit', 2.0))
        self.clahe_tile_grid = int(self.config.get('image_processing.clahe_tile_grid', 8))
        self.sharpen_enabled = bool(self.config.get('image_processing.sharpen_enabled', False))
        self.sharpen_amount = float(self.config.get('image_processing.sharpen_amount', 0.6))
        self.sharpen_sigma = float(self.config.get('image_processing.sharpen_sigma', 1.0))
        
        # Session tracking
        self.session_count = 0
        
        logger.info("IoT Attendance System initialized")
    
    def initialize_camera(self) -> bool:
        """Initialize camera"""
        try:
            camera_index = self.config.get('camera.index', 0)
            width = self.config.get('camera.resolution.width', 640)
            height = self.config.get('camera.resolution.height', 480)
            
            # Prepare optional picamera controls from config
            picam_controls = self.config.get('camera.picamera', {})
            self.camera = CameraHandler(
                camera_index=camera_index,
                resolution=(width, height),
                controls=picam_controls,
                still_settle_ms=self.still_settle_ms
            )
            
            if not self.camera.start():
                logger.error("Failed to start camera")
                return False
            
            logger.info(f"✓ Camera started: {width}x{height}")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing camera: {str(e)}")
            return False
    
    def scan_qr_code(self, frame) -> str:
        """Scan QR code from frame, returns student_id or None"""
        try:
            # Suppress ZBar warnings during decode
            with SuppressStderr():
                decoded_objects = pyzbar.decode(frame)
            
            if decoded_objects:
                qr_data = decoded_objects[0].data.decode('utf-8')
                logger.info(f"QR code detected: {qr_data}")
                return qr_data
            
            return None
        except Exception as e:
            logger.error(f"Error scanning QR code: {str(e)}")
            return None
    
    def capture_face_photo(self, frame, student_id: str, face_box=None) -> str:
        """
        Capture and save face photo with lighting compensation
        Returns: photo file path
        """
        try:
            # Analyze lighting conditions
            if self.lighting_enabled:
                lighting_analysis = self.lighting_analyzer.analyze_frame(frame)
                logger.debug(f"Lighting quality: {lighting_analysis.get('quality_score', 0):.2f}")
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"attendance_{student_id}_{timestamp}.jpg"
            filepath = os.path.join('data/photos', filename)
            
            # Optionally capture a high-res still using Picamera2
            base_img = frame
            if self.use_high_res_still and getattr(self.camera, 'use_picamera2', False):
                target_size = None
                if self.still_width > 0 and self.still_height > 0:
                    target_size = (self.still_width, self.still_height)
                still_img = self.camera.capture_still_array(size=target_size)
                if still_img is not None:
                    base_img = still_img

            # Decide whether to save full frame regardless of detected box
            if self.save_full_frame or face_box is None or len(face_box) != 4:
                img_to_save = base_img
            else:
                x, y, w, h = face_box
                # Scale box if base_img has different size from the preview frame
                if base_img.shape[1] != frame.shape[1] or base_img.shape[0] != frame.shape[0]:
                    sx = base_img.shape[1] / float(frame.shape[1])
                    sy = base_img.shape[0] / float(frame.shape[0])
                    x = int(x * sx)
                    y = int(y * sy)
                    w = int(w * sx)
                    h = int(h * sy)
                padding = self.crop_padding
                x = max(0, x - padding)
                y = max(0, y - padding - self.extra_top)
                w = min(base_img.shape[1] - x, w + 2 * padding)
                h = min(base_img.shape[0] - y, h + 2 * padding + self.extra_top)
                img_to_save = base_img[y:y + h, x:x + w]
            
            # Apply lighting compensation if enabled
            if self.lighting_enabled:
                img_to_save = self.lighting_compensator.compensate(img_to_save, lighting_analysis)
            
            # Color / enhancement pipeline
            if self.prefer_isp_color:
                # Mild neutral balance only (avoid heavy processing to keep ISP look)
                if self.neutral_balance_enabled:
                    try:
                        img_to_save = self.apply_mild_neutral_balance(img_to_save, self.neutral_balance_strength)
                    except Exception as e:
                        logger.warning(f"Neutral balance failed: {e}")
            else:
                # Optional gray-world AWB
                if self.awb_grayworld_enabled:
                    try:
                        img_to_save = self.apply_grayworld_awb(img_to_save)
                    except Exception as e:
                        logger.warning(f"Gray-world AWB failed: {e}")
                # Optional denoising
                if self.denoise_enabled:
                    try:
                        img_to_save = cv2.fastNlMeansDenoisingColored(
                            img_to_save,
                            None,
                            self.denoise_h,
                            self.denoise_hColor,
                            self.denoise_templateWindowSize,
                            self.denoise_searchWindowSize
                        )
                    except Exception as e:
                        logger.warning(f"Denoising failed: {e}")
                # Optional CLAHE on L channel
                if self.clahe_enabled:
                    try:
                        lab = cv2.cvtColor(img_to_save, cv2.COLOR_BGR2LAB)
                        l, a, b = cv2.split(lab)
                        clahe = cv2.createCLAHE(clipLimit=self.clahe_clip_limit, tileGridSize=(self.clahe_tile_grid, self.clahe_tile_grid))
                        l2 = clahe.apply(l)
                        img_to_save = cv2.merge((l2, a, b))
                        img_to_save = cv2.cvtColor(img_to_save, cv2.COLOR_LAB2BGR)
                    except Exception as e:
                        logger.warning(f"CLAHE failed: {e}")
                # Optional sharpening via unsharp mask
                if self.sharpen_enabled and self.sharpen_amount > 0:
                    try:
                        blur = cv2.GaussianBlur(img_to_save, (0, 0), self.sharpen_sigma)
                        img_to_save = cv2.addWeighted(img_to_save, 1 + self.sharpen_amount, blur, -self.sharpen_amount, 0)
                    except Exception as e:
                        logger.warning(f"Sharpen failed: {e}")
            # Save with JPEG quality
            try:
                cv2.imwrite(filepath, img_to_save, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            except Exception:
                cv2.imwrite(filepath, img_to_save)
            
            logger.info(f"Photo saved: {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Error saving photo: {str(e)}")
            return None
    
    def upload_to_database(self, student_id: str, photo_path: str, qr_data: str, scan_type: str = 'time_in', status: str = 'present') -> bool:
        """Upload attendance record to database and sync to cloud"""
        try:
            # Ensure student exists in database
            student = self.database.get_student(student_id)
            if not student:
                # Add student with ID only
                self.database.add_student(student_id, name=None, email=None)
                logger.info(f"New student registered: {student_id}")
            
            # Record attendance locally
            record_id = self.database.record_attendance(student_id, photo_path, qr_data, scan_type, status)
            
            if record_id:
                logger.info(f"Attendance uploaded to database (Record ID: {record_id})")
                
                # Attempt cloud sync if enabled and sync_on_capture is true
                if self.cloud_sync.enabled and self.cloud_sync.sync_on_capture:
                    # Get the attendance record we just created
                    attendance_data = {
                        'id': record_id,
                        'student_id': student_id,
                        'timestamp': datetime.now().isoformat(),
                        'photo_path': photo_path,
                        'qr_data': qr_data,
                        'scan_type': scan_type,
                        'status': status
                    }
                    
                    # Try to sync immediately (will queue if offline)
                    self.cloud_sync.sync_attendance_record(attendance_data, photo_path)
                
                # Send SMS notification to parent if enabled
                if self.sms_notifier.enabled and self.config.get('sms_notifications', {}).get('send_on_capture', True):
                    # Get fresh student data (may have parent phone)
                    student_data = self.database.get_student(student_id)
                    if student_data and student_data.get('parent_phone'):
                        logger.info(f"Sending SMS notification to parent for {student_id}")
                        sms_sent = self.sms_notifier.send_attendance_notification(
                            student_id=student_id,
                            student_name=student_data.get('name'),
                            parent_phone=student_data.get('parent_phone'),
                            timestamp=datetime.now(),
                            scan_type=attendance_data.get('scan_type', 'time_in')
                        )
                        if sms_sent:
                            logger.info(f"SMS notification sent successfully to parent of {student_id}")
                        else:
                            logger.warning(f"Failed to send SMS notification to parent of {student_id}")
                    else:
                        logger.debug(f"No parent phone number for student {student_id}, skipping SMS")
                
                return True
            else:
                logger.error("Failed to upload attendance")
                self.buzzer.beep('error')
                return False
        
        except Exception as e:
            logger.error(f"Error uploading to database: {str(e)}")
            self.buzzer.beep('error')
            return False
    
    def run(self, display: bool = True, headless: bool = False):
        """
        Run the attendance system
        
        Main loop:
        1. STANDBY - Wait for QR code
        2. QR_DETECTED - Start face detection window
        3. CAPTURING - Detect face and capture photo
        4. UPLOADING - Save to database
        5. Return to STANDBY
        """
        if not self.initialize_camera():
            print("\n❌ CAMERA INITIALIZATION FAILED")
            print("Cannot run without camera")
            print("Try: python attendance_system.py --demo\n")
            return
        
        # Force disable display if headless
        if headless:
            display = False
        
        print("\n" + "="*70)
        print("IoT ATTENDANCE SYSTEM")
        print("="*70)
        print("\nSystem Ready!")
        print("\nWorkflow:")
        print("  1. 📱 Student scans QR code")
        print("  2. 👤 System detects face (2 second window)")
        print("  3. 📸 Photo captured")
        print("  4. 💾 Data uploaded to database")
        print("  5. ✓  Return to standby\n")
        
        if not display:
            print("Running in HEADLESS mode (no display window)")
        
        print("Press Ctrl+C to stop\n")
        print("="*70 + "\n")
        print("🟢 STANDBY - Waiting for QR code scan...\n")
        
        # State variables
        self.state = 'STANDBY'
        current_student_id = None
        capture_start_time = None
        face_detected = False
        best_face_frame = None
        best_face_box = None
        
        frame_count = 0
        
        try:
            while True:
                # Get frame
                frame = self.camera.get_frame()
                if frame is None:
                    logger.warning("Failed to get frame")
                    time.sleep(0.1)
                    continue
                
                frame_count += 1
                display_frame = frame.copy() if display else None
                
                # ===== STATE: STANDBY =====
                if self.state == 'STANDBY':
                    # Scan for QR code
                    student_id = self.scan_qr_code(frame)
                    
                    if student_id:
                        # Buzzer feedback for QR detected
                        self.buzzer.beep('qr_detected')
                        
                        # Check if student is in today's roster (from Supabase cache)
                        if self.roster_sync.enabled:
                            student = self.roster_sync.get_cached_student(student_id)
                            if not student:
                                print(f"   ❌ UNAUTHORIZED: Student {student_id} not in today's roster")
                                logger.warning(f"Student {student_id} not found in roster cache")
                                self.buzzer.beep('error')
                                
                                if display:
                                    cv2.putText(display_frame, "NOT IN TODAY'S ROSTER", (50, 200),
                                              cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                                    cv2.putText(display_frame, f"Student: {student_id}", (50, 260),
                                              cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                                    cv2.imshow('Attendance System', display_frame)
                                    cv2.waitKey(2000)  # Show for 2 seconds
                                else:
                                    time.sleep(2)
                                
                                continue
                            else:
                                logger.info(f"✓ Student {student_id} verified from roster: {student.get('name', 'Unknown')}")
                        else:
                            # Fallback: Check local database if roster sync disabled
                            student = self.database.get_student(student_id)
                            if not student:
                                # Auto-register new student when roster sync is disabled
                                self.database.add_student(student_id, name=None, email=None)
                                logger.info(f"Auto-registered new student: {student_id}")
                        
                        # Get current schedule info
                        schedule_info = self.schedule_manager.get_schedule_info()
                        expected_scan_type = schedule_info['expected_scan_type']
                        current_session = schedule_info['current_session']
                        
                        # Check if this scan is allowed (duplicate prevention)
                        last_scan = self.database.get_last_scan(student_id)
                        
                        if not self.schedule_manager.should_allow_scan(
                            student_id=student_id,
                            current_scan_type=expected_scan_type,
                            last_scan_time=last_scan.get('timestamp') if last_scan else None,
                            last_scan_type=last_scan.get('scan_type') if last_scan else None
                        ):
                            print(f"⚠️  Student {student_id} - ALREADY SCANNED (Cooldown: {self.schedule_manager.duplicate_cooldown_minutes} min)")
                            self.buzzer.beep('duplicate')
                            
                            if display:
                                cv2.putText(display_frame, "ALREADY SCANNED", (50, 200),
                                          cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                                cv2.putText(display_frame, f"Student: {student_id}", (50, 260),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                                cv2.putText(display_frame, f"Type: {expected_scan_type.upper()}", (50, 310),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                                cv2.imshow('Attendance System', display_frame)
                                cv2.waitKey(2000)  # Show for 2 seconds
                            else:
                                time.sleep(2)
                            
                            continue
                        
                        # Valid QR code - start capture process
                        scan_type_display = "LOGIN" if expected_scan_type == 'time_in' else "LOGOUT"
                        session_display = current_session.upper() if current_session != 'unknown' else "AFTER HOURS"
                        
                        print(f"\n{'='*70}")
                        print(f"📱 QR CODE DETECTED: {student_id}")
                        print(f"   Session: {session_display} | Type: {scan_type_display}")
                        print(f"{'='*70}")
                        print(f"👤 Starting face detection...")
                        
                        self.state = 'CAPTURING'
                        current_student_id = student_id
                        current_scan_type = expected_scan_type
                        current_session_name = current_session
                        capture_start_time = time.time()
                        face_detected = False
                        best_face_frame = None
                        best_face_box = None
                    
                    # Display standby screen
                    if display:
                        # Get current schedule info
                        schedule_info = self.schedule_manager.get_schedule_info()
                        session_name = schedule_info['current_session'].upper() if schedule_info['current_session'] != 'unknown' else "AFTER HOURS"
                        scan_type_name = "LOGIN" if schedule_info['expected_scan_type'] == 'time_in' else "LOGOUT"
                        
                        cv2.putText(display_frame, "STANDBY - SCAN QR CODE", (50, 60),
                                  cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                        cv2.putText(display_frame, "Show your QR code to camera", (50, 110),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        
                        # Show schedule info
                        cv2.putText(display_frame, f"Session: {session_name} | Scan: {scan_type_name}", 
                                  (50, 160),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                        
                        # Show stats
                        stats = self.database.get_statistics()
                        cv2.putText(display_frame, f"Today: {stats.get('today_attendance', 0)} records", 
                                  (50, display_frame.shape[0] - 30),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # ===== STATE: CAPTURING =====
                elif self.state == 'CAPTURING':
                    elapsed = time.time() - capture_start_time
                    remaining = self.capture_window - elapsed
                    
                    # Detect faces in current frame
                    faces = self.face_detector.detect_faces(frame)
                    
                    if len(faces) > 0:
                        # Face detected!
                        if not face_detected:
                            face_detected = True
                            self.buzzer.beep('face_detected')
                            print(f"   ✓ Face detected!")
                        
                        # Store best face (largest face)
                        largest_face = max(faces, key=lambda f: f[2] * f[3])
                        best_face_frame = frame.copy()
                        best_face_box = largest_face
                    
                    # Display capture window
                    if display:
                        # Draw face boxes
                        for (x, y, w, h) in faces:
                            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                        # Draw prospective crop region (preview) around largest face if cropping enabled
                        if (not self.save_full_frame and self.preview_draw_crop_box and best_face_box is not None):
                            bx, by, bw, bh = best_face_box
                            padding = self.crop_padding
                            px = max(0, bx - padding)
                            py = max(0, by - padding - self.extra_top)
                            pw = min(frame.shape[1] - px, bw + 2 * padding)
                            ph = min(frame.shape[0] - py, bh + 2 * padding + self.extra_top)
                            cv2.rectangle(display_frame, (px, py), (px+pw, py+ph), (255, 140, 0), 2)
                            cv2.putText(display_frame, "CROP PREVIEW", (px, max(0, py-10)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 140, 0), 1)
                        
                        if remaining > 0:
                            countdown = int(remaining) + 1
                            status = "FACE DETECTED!" if face_detected else "DETECTING..."
                            color = (0, 255, 0) if face_detected else (0, 255, 255)
                            
                            cv2.putText(display_frame, f"CAPTURING: {countdown}s", (50, 60),
                                      cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
                            cv2.putText(display_frame, status, (50, 120),
                                      cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
                            cv2.putText(display_frame, f"Student: {current_student_id}", (50, 170),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    
                    # Check if capture window expired
                    if remaining <= 0:
                        if face_detected and best_face_frame is not None:
                            # Capture successful
                            print(f"   📸 Capturing photo...")
                            
                            # Save photo
                            photo_path = self.capture_face_photo(
                                best_face_frame, 
                                current_student_id, 
                                best_face_box
                            )
                            
                            if photo_path:
                                print(f"   ✓ Photo saved: {photo_path}")
                                
                                # Determine attendance status based on schedule
                                attendance_status = self.schedule_manager.determine_attendance_status(
                                    datetime.now(), 
                                    self.schedule_manager.get_current_session(), 
                                    self.schedule_manager.get_expected_scan_type()[0]
                                )
                                status_display = "ON TIME" if attendance_status == 'present' else "LATE"
                                
                                print(f"   📋 Status: {status_display}")
                                
                                # Upload to database
                                print(f"   💾 Uploading to database...")
                                self.state = 'UPLOADING'
                                
                                if self.upload_to_database(current_student_id, photo_path, current_student_id, current_scan_type, attendance_status):
                                    self.session_count += 1
                                    self.buzzer.beep('success')
                                    
                                    scan_type_msg = "LOGIN" if current_scan_type == 'time_in' else "LOGOUT"
                                    print(f"   ✓ {scan_type_msg} recorded successfully!")
                                    print(f"   📊 Total today: {self.session_count}")
                                    
                                    # Show success message
                                    if display:
                                        success_frame = frame.copy()
                                        cv2.putText(success_frame, "SUCCESS!", (150, 180),
                                                  cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 0), 4)
                                        cv2.putText(success_frame, f"Student: {current_student_id}", (150, 240),
                                                  cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                                        cv2.putText(success_frame, f"Type: {scan_type_msg}", (150, 290),
                                                  cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                                        cv2.putText(success_frame, f"Status: {status_display}", (150, 340),
                                                  cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0) if attendance_status == 'present' else (0, 165, 255), 2)
                                        cv2.imshow('Attendance System', success_frame)
                                        cv2.waitKey(1500)  # Show for 1.5 seconds
                                    else:
                                        time.sleep(1.5)
                                else:
                                    print(f"   ❌ Failed to upload to database")
                        else:
                            # No face detected
                            self.buzzer.beep('error')
                            print(f"   ❌ No face detected in capture window")
                            
                            if display:
                                fail_frame = frame.copy()
                                cv2.putText(fail_frame, "NO FACE DETECTED", (100, 240),
                                          cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                                cv2.putText(fail_frame, "Please try again", (150, 300),
                                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                                cv2.imshow('Attendance System', fail_frame)
                                cv2.waitKey(2000)
                            else:
                                time.sleep(2)
                        
                        # Return to standby
                        print(f"{'='*70}\n")
                        print(f"🟢 STANDBY - Waiting for QR code scan...\n")
                        self.state = 'STANDBY'
                        current_student_id = None
                
                # Display frame
                if display and display_frame is not None:
                    cv2.imshow('Attendance System', display_frame)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print("\nShutdown requested by user...")
                        break
                
                # Periodic status in headless mode
                if not display and frame_count % 90 == 0:
                    stats = self.database.get_statistics()
                    print(f"[Status] Frame: {frame_count} | Today: {stats.get('today_attendance', 0)} students")
        
        except KeyboardInterrupt:
            print("\n\nShutdown requested (Ctrl+C)...")
        
        except Exception as e:
            logger.error(f"System error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.shutdown()

    def apply_grayworld_awb(self, img: np.ndarray) -> np.ndarray:
        # Gray-world white balance: equalize mean of B,G,R channels
        if img.ndim != 3 or img.shape[2] != 3:
            return img
        imgf = img.astype(np.float32)
        b, g, r = cv2.split(imgf)
        mb = float(np.mean(b)) + 1e-6
        mg = float(np.mean(g)) + 1e-6
        mr = float(np.mean(r)) + 1e-6
        gray = (mb + mg + mr) / 3.0
        kb, kg, kr = gray / mb, gray / mg, gray / mr
        b *= kb
        g *= kg
        r *= kr
        out = cv2.merge((b, g, r))
        return np.clip(out, 0, 255).astype(np.uint8)

    def _background_sync_loop(self):
        """Background thread for processing sync queue"""
        logger.info("Background sync loop started")
        
        while True:
            try:
                # Process sync queue every interval
                time.sleep(self.cloud_sync.sync_interval)
                
                # Check if online
                if self.connectivity.is_online():
                    result = self.cloud_sync.process_sync_queue(batch_size=10)
                    if result['processed'] > 0:
                        logger.info(f"Background sync: {result['succeeded']} succeeded, {result['failed']} failed")
                
            except Exception as e:
                logger.error(f"Error in background sync loop: {e}")
                time.sleep(30)  # Wait before retrying
    
    def apply_mild_neutral_balance(self, img: np.ndarray, strength: float = 0.3) -> np.ndarray:
        """Apply a mild gray-world style correction with adjustable strength (0-1)."""
        if img.ndim != 3 or img.shape[2] != 3:
            return img
        imgf = img.astype(np.float32)
        b, g, r = cv2.split(imgf)
        mb = float(np.mean(b)) + 1e-6
        mg = float(np.mean(g)) + 1e-6
        mr = float(np.mean(r)) + 1e-6
        gray = (mb + mg + mr) / 3.0
        gains = np.array([gray/mb, gray/mg, gray/mr], dtype=np.float32)
        # Blend gains toward 1 by (1 - strength)
        gains = 1.0 + (gains - 1.0) * max(0.0, min(1.0, strength))
        # Apply
        b *= gains[0]
        g *= gains[1]
        r *= gains[2]
        out = cv2.merge((b, g, r))
        return np.clip(out, 0, 255).astype(np.uint8)
    
    def run_demo(self):
        """Run demo mode without camera"""
        print("\n" + "="*70)
        print("IoT ATTENDANCE SYSTEM - DEMO MODE")
        print("="*70)
        
        print("\nSimulating attendance workflow...\n")
        
        # Demo students
        demo_students = [
            "2021001",
            "2021002", 
            "2021003",
            "2021004",
            "2021005"
        ]
        
        for i, student_id in enumerate(demo_students, 1):
            print(f"\n{'='*70}")
            print(f"[Student {i}/5]")
            print(f"{'='*70}")
            print(f"📱 QR Code Scanned: {student_id}")
            time.sleep(0.5)
            
            print(f"👤 Detecting face...")
            time.sleep(0.8)
            print(f"   ✓ Face detected!")
            
            print(f"📸 Capturing photo...")
            time.sleep(0.5)
            
            # Create demo record
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            photo_path = f"data/photos/demo_attendance_{student_id}_{timestamp}.jpg"
            
            print(f"   ✓ Photo saved: {photo_path}")
            
            print(f"💾 Uploading to database...")
            time.sleep(0.5)
            
            # Actually add to database in demo
            self.database.add_student(student_id)
            self.database.record_attendance(student_id, photo_path, student_id)
            
            print(f"   ✓ Attendance recorded successfully!")
            print(f"   📊 Total: {i} student(s)")
            
            time.sleep(0.5)
        
        print(f"\n{'='*70}")
        print("DEMO COMPLETE")
        print(f"{'='*70}\n")
        
        self.shutdown()
    
    def shutdown(self):
        """Shutdown system"""
        print("\n" + "="*70)
        print("SYSTEM SHUTDOWN")
        print("="*70)
        
        # Clean up buzzer
        if self.buzzer:
            self.buzzer.cleanup()
            logger.info("Buzzer cleaned up")
        
        # Release camera
        if self.camera:
            self.camera.release()
            logger.info("Camera released")
        
        # Close display
        if cv2:
            cv2.destroyAllWindows()
        
        # Get final statistics
        stats = self.database.get_statistics()
        
        print(f"\nSession Summary:")
        print(f"  Students scanned this session: {self.session_count}")
        print(f"  Total today: {stats.get('today_attendance', 0)}")
        print(f"  Total students in database: {stats.get('total_students', 0)}")
        print(f"  All-time attendance records: {stats.get('total_records', 0)}")
        
        # Export data
        export_file = self.database.export_to_json()
        if export_file:
            print(f"\n✓ Data exported to: {export_file}")
        
        print("\n" + "="*70)
        print("System stopped - Standby mode OFF")
        print("="*70 + "\n")


if __name__ == '__main__':
    # Setup logger
    setup_logger(name='iot_attendance_system')
    
    # Initialize system
    system = IoTAttendanceSystem(config_file='config/config.json')
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--demo':
            system.run_demo()
        elif sys.argv[1] == '--headless':
            system.run(display=False, headless=True)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Usage:")
            print("  python attendance_system.py           # Run with display")
            print("  python attendance_system.py --demo    # Demo mode")
            print("  python attendance_system.py --headless # Headless mode (no display)")
    else:
        try:
            system.run(display=True)
        except Exception as e:
            logger.error(f"System error: {str(e)}")
            import traceback
            traceback.print_exc()
