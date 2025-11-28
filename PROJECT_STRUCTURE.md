# Project Structure

## Directory Organization

```
attendance-system/
├── attendance_system.py        # Main application entry point
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── LICENSE                     # Project license
│
├── config/                     # Configuration files
│   └── config.json            # System configuration
│
├── src/                        # Source code modules
│   ├── attendance/            # Attendance management
│   ├── camera/                # Camera handling
│   ├── cloud/                 # Cloud sync (Supabase)
│   ├── database/              # Local database operations
│   ├── network/               # Network connectivity
│   ├── notifications/         # SMS notifications
│   ├── recognition/           # Face detection/recognition
│   ├── sync/                  # Roster synchronization
│   └── utils/                 # Utility functions
│
├── scripts/                   # System scripts
│   ├── start_attendance.sh   # Main startup script
│   ├── deployment/           # Deployment scripts
│   └── archive/              # Archived/old scripts
│
├── tests/                     # Test scripts
│   ├── test_simple_flow.py   # Complete flow test
│   └── test_sms_quick.sh     # SMS quick test
│
├── docs/                      # Documentation
│   ├── implementation/       # Implementation docs
│   ├── technical/            # Technical specs
│   └── user-guides/          # User guides
│
├── supabase/                  # Supabase configuration
│   └── migrations/           # Database migrations
│
├── data/                      # Runtime data
│   ├── attendance.db         # Local SQLite database
│   ├── photos/               # Captured photos
│   └── logs/                 # System logs
│
├── data/qr_codes/             # Generated QR codes
│
├── venv/                      # Python virtual environment
│
└── .env                       # Environment variables (not in git)
```

## Key Files

### Application
- `attendance_system.py` - Main system orchestrator
- `config/config.json` - System configuration
- `.env` - Environment variables (credentials)

### Scripts
- `scripts/start_attendance.sh` - Start system
- `tests/test_simple_flow.py` - Test complete flow

### Documentation
- `README.md` - Getting started guide
- `docs/implementation/` - Implementation details
- `PROJECT_STRUCTURE.md` - This file

## Module Organization

### src/attendance/
- `attendance_manager.py` - Attendance tracking logic
- `schedule_manager.py` - School schedule handling

### src/camera/
- `camera_handler.py` - Camera initialization and capture

### src/cloud/
- `cloud_sync.py` - Supabase synchronization
- `photo_uploader.py` - Photo upload to cloud storage

### src/database/
- `db_handler.py` - SQLite operations
- `sync_queue.py` - Offline sync queue

### src/notifications/
- `sms_notifier.py` - SMS notification service

### src/recognition/
- `face_detector.py` - Face detection using dlib/OpenCV
- `face_recognizer.py` - Face recognition engine

### src/sync/
- `roster_sync.py` - Daily roster synchronization

### src/utils/
- `config_loader.py` - Configuration management
- `logger_config.py` - Logging setup

## Data Flow

1. **QR Scan** → `attendance_system.py`
2. **Face Detection** → `src/recognition/face_detector.py`
3. **Photo Capture** → `src/camera/camera_handler.py`
4. **Database Save** → `src/database/db_handler.py`
5. **Cloud Sync** → `src/cloud/cloud_sync.py`
6. **SMS Send** → `src/notifications/sms_notifier.py`

## Configuration Files

- `.env` - Credentials (Supabase, SMS, etc.)
- `config/config.json` - System settings
- `supabase/migrations/` - Database schema

## Runtime Directories

- `data/attendance.db` - Local attendance records
- `data/photos/` - Captured student photos
- `logs/` - Application logs
- `data/qr_codes/` - Student QR codes
