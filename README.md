# IoT Attendance System

**Advanced QR-based attendance system with automatic face capture, quality validation, and cloud synchronization for Raspberry Pi.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Supabase](https://img.shields.io/badge/Database-Supabase-green.svg)](https://supabase.com)

---

## 🎯 Overview

A production-ready attendance system that combines QR code validation with automatic face capture. Built for educational institutions requiring reliable, privacy-compliant attendance tracking with offline capability.

**Key Capabilities:**
- **QR Code Validation** - Instant student verification against daily roster
- **Automatic Face Capture** - 9 quality checks with 3-second stability requirement
- **Offline-First Architecture** - Local SQLite cache with automatic cloud sync
- **Schedule Enforcement** - LOGIN/LOGOUT windows with late status detection
- **SMS Notifications** - Real-time parent/guardian alerts
- **Privacy Compliant** - Daily roster sync with automatic evening cache wipe
- **Production Hardened** - Circuit breakers, disk monitoring, transaction safety, structured logging

---

## ✨ Features

### Core Functionality
- ⚡ **Fast QR Scanning** - Sub-100ms response time
- 📸 **Quality-Gated Photos** - 9 validation checks (size, centering, pose, eyes, brightness, sharpness, lighting, stability)
- 🔄 **Offline Queue** - Automatic sync when connectivity restored
- 📅 **Schedule Validation** - Prevent wrong-session scans (morning/afternoon enforcement)
- 🎯 **Scan Type Detection** - Automatic LOGIN/LOGOUT/BREAK determination based on schedule
- 📱 **SMS Integration** - Template-based notifications with delivery tracking

### Robustness (Phase 1-2)
- 💾 **Disk Monitoring** - Space checks before saves, automatic cleanup of old data
- 🔌 **Circuit Breakers** - Protect against cascading failures on Supabase calls
- 📷 **Camera Recovery** - Auto-retry on init, periodic health checks, graceful degradation
- 🔒 **Transaction Safety** - Atomic attendance+queue saves, rollback on failures

### Enhanced Reliability (Phase 3)
- ⏱️ **Network Timeouts** - Service-specific timeouts (Supabase: 10s, Storage: 30s, SMS: 15s)
- ✅ **Queue Validation** - Data sanitization before queueing, auto-fix common issues
- 🔐 **File Locking** - Prevent database/photo races in concurrent operations
- 📊 **Structured Logging** - Correlation IDs, JSON logs, multi-output (file, syslog, audit)

### Administration
- 🎛️ **Server-Side Config** - Manage SMS templates and schedules in Supabase
- 📈 **Metrics Tracking** - Scan counts, queue size, sync success rates
- 🚨 **Alert System** - Critical error notifications with rate limiting
- 🔍 **Audit Trail** - Security-sensitive operations logged separately

---

## 🚀 Quick Start

### Prerequisites

- **Hardware:** Raspberry Pi 4 (2GB+ RAM recommended)
- **OS:** Raspberry Pi OS (Debian 11/12)
- **Python:** 3.11 or higher
- **Camera:** Compatible USB webcam or Pi Camera Module
- **Storage:** 16GB+ SD card (for logs and photos)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/Cerjho/IoT-Attendance-System.git
cd IoT-Attendance-System

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install system dependencies (for camera/GPIO)
sudo apt update
sudo apt install -y python3-opencv libatlas-base-dev libzbar0 libsystemd-dev
```

### Configuration

1. **Create environment file:**
```bash
cp .env.example .env
```

2. **Edit `.env` with your credentials:**
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key_here
DEVICE_ID=pi-lab-01

# SMS Configuration (optional)
SMS_USERNAME=your_sms_username
SMS_PASSWORD=your_sms_password
SMS_DEVICE_ID=your_device_id
SMS_API_URL=https://sms-api-url.com
```

3. **Configure system settings in `config/config.json`:**
```json
{
  "cloud": {
    "enabled": true
  },
  "notifications": {
    "sms_enabled": true
  },
  "device_id": "pi-lab-01"
}
```

### Database Setup

Apply Supabase migrations to create required tables:

```bash
# Using Supabase CLI
cd supabase
supabase db push

# Or manually apply migrations from supabase/migrations/ in order
```

**Required tables:**
- `students` - Student roster with phone numbers
- `attendance` - Attendance records (auto-enriched with section/subject via trigger)
- `iot_devices` - Device registry with location/schedule mapping
- `school_schedules` - Schedule definitions (LOGIN/LOGOUT windows)
- `teaching_loads` - Subject assignments for enrichment
- `sms_templates` - Notification templates

See `supabase/migrations/` for complete schema.

### Initial Data

Add students to your Supabase instance:

```bash
# Via utility script
python utils/manage_supabase_students.py --import-csv students.csv

# Or insert directly in Supabase dashboard
```

### Running

#### Option 1: Direct Execution (GUI Mode)
```bash
python attendance_system.py
```

#### Option 2: Headless Mode (Production)
```bash
bash scripts/start_attendance.sh --headless
```

#### Option 3: Systemd Service (Recommended)
```bash
# Install service
sudo cp scripts/attendance-system.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable attendance-system
sudo systemctl start attendance-system

# Check status
sudo systemctl status attendance-system
```

---

## 📁 Project Structure

```
IoT-Attendance-System/
├── attendance_system.py          # Main application entry point
├── start_attendance.sh            # Startup script (delegates to scripts/)
├── requirements.txt               # Python dependencies
├── pytest.ini                     # Test configuration
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
│
├── config/                        # Configuration files
│   ├── config.json               # Main system configuration
│   └── defaults.json             # Default values and fallbacks
│
├── src/                          # Source code modules
│   ├── attendance/               # Schedule management and validation
│   │   ├── schedule_manager.py  # LOGIN/LOGOUT window logic
│   │   └── schedule_validator.py # Schedule rule enforcement
│   ├── auth/                     # Authentication helpers
│   ├── camera/                   # Camera interface and capture
│   │   └── camera_handler.py    # Camera management with recovery
│   ├── cloud/                    # Cloud integration (Supabase)
│   │   ├── cloud_sync.py        # Attendance/photo upload orchestration
│   │   └── photo_uploader.py    # Storage bucket operations
│   ├── database/                 # Local SQLite cache
│   │   ├── db_handler.py        # Database operations
│   │   └── sync_queue.py        # Offline queue management
│   ├── face_quality.py           # Face quality validation (9 checks)
│   ├── hardware/                 # GPIO and hardware control
│   │   ├── buzzer_controller.py # Audio feedback
│   │   ├── rgb_led_controller.py # Visual status indicators
│   │   └── power_button.py      # Graceful shutdown button
│   ├── lighting/                 # Lighting analysis
│   │   ├── analyzer.py          # Illumination assessment
│   │   └── compensator.py       # Auto brightness/contrast
│   ├── network/                  # Network connectivity
│   │   └── connectivity.py      # Online/offline detection
│   ├── notifications/            # SMS notifications
│   │   ├── sms_notifier.py      # SMS sending logic
│   │   └── template_cache.py    # Template management
│   ├── sync/                     # Data synchronization
│   │   ├── roster_sync.py       # Daily student roster pull
│   │   └── schedule_sync.py     # Schedule updates from cloud
│   └── utils/                    # Shared utilities
│       ├── config_loader.py     # Configuration management
│       ├── logging_factory.py   # Centralized logging setup
│       ├── audit_logger.py      # Security/business event logging
│       ├── circuit_breaker.py   # Circuit breaker pattern
│       ├── disk_monitor.py      # Storage management
│       ├── db_transactions.py   # Transaction safety helpers
│       ├── network_timeouts.py  # Service timeout configs
│       ├── queue_validator.py   # Queue data validation
│       ├── file_locks.py        # File locking utilities
│       ├── shutdown_handler.py  # Graceful shutdown
│       ├── alerts.py            # Alert notifications
│       └── metrics.py           # Performance metrics
│
├── scripts/                      # Automation and maintenance
│   ├── start_attendance.sh      # Main startup script (with env loading)
│   ├── monitor.py               # System monitoring dashboard
│   ├── backup.py                # Database backup automation
│   ├── cleanup_attendance_cache.py # Daily cache cleanup
│   ├── deploy_migration.py      # Migration deployment helper
│   ├── hw_check.py              # Hardware validation
│   ├── assign_schedules.py      # Schedule assignment utility
│   └── deployment/              # Production deployment scripts
│
├── tests/                        # Test suite
│   ├── test_simple_flow.py      # Basic flow tests
│   ├── test_system_integration.py # Integration tests
│   ├── test_face_quality.py     # Quality validation tests
│   ├── test_cloud_sync_*.py     # Cloud sync test suite
│   └── test_logging_system.py   # Logging tests
│
├── utils/                        # Utility scripts
│   ├── manage_supabase_students.py # Student CRUD operations
│   ├── check_status.py          # System status checker
│   ├── view_attendance.py       # Attendance viewer
│   ├── generate_qr.py           # QR code generator
│   └── test-scripts/            # Testing utilities
│
├── data/                         # Runtime data (gitignored)
│   ├── attendance.db            # Local SQLite cache
│   ├── photos/                  # Captured attendance photos
│   ├── logs/                    # System, audit, and business logs
│   ├── qr_codes/                # Generated QR codes
│   ├── backups/                 # Database backups
│   └── exports/                 # Exported reports
│
├── docs/                         # Documentation
│   ├── QUICK_REFERENCE.md       # Production quick reference
│   ├── PRODUCTION_GUIDE.md      # Production deployment guide
│   ├── DEPLOYMENT.md            # Deployment instructions
│   ├── ADMIN_GUIDE.md           # Administrator guide
│   ├── LOGGING_QUICK_REFERENCE.md # Logging configuration
│   ├── technical/               # Technical documentation
│   │   ├── SYSTEM_OVERVIEW.md   # Architecture overview
│   │   ├── AUTO_CAPTURE.md      # Face capture details
│   │   └── CLOUD_INTEGRATION.md # Supabase integration
│   ├── user-guides/             # End-user guides
│   ├── testing/                 # Testing guides
│   └── troubleshooting/         # Common issues and fixes
│
├── supabase/                     # Supabase configuration
│   ├── migrations/              # Database migrations (timestamped)
│   ├── sql/                     # SQL helpers and views
│   └── schemas/                 # Schema documentation
│
├── public/                       # Public web assets
│   └── view-attendance.html     # Client-side attendance viewer
│
└── backups/                      # Full system backups (gitignored)
```

---

## 🔧 Configuration

### Main Configuration (`config/config.json`)

```json
{
  "device_id": "pi-lab-01",
  
  "camera": {
    "index": "0",
    "resolution": {"width": "640", "height": "480"},
    "fps": 30
  },
  
  "cloud": {
    "enabled": true,
    "retry_attempts": 3,
    "retry_delay": 30,
    "cleanup_photos_after_sync": false
  },
  
  "notifications": {
    "sms_enabled": true,
    "cooldown_seconds": 300
  },
  
  "face_quality": {
    "min_face_size": 60,
    "center_tolerance": 25.0,
    "stability_duration": 2.0,
    "timeout": 15.0
  },
  
  "schedule": {
    "enabled": true,
    "sync_enabled": true,
    "sync_interval": 3600
  },
  
  "logging": {
    "level": "INFO",
    "outputs": {
      "file": {"enabled": true, "level": "DEBUG"},
      "json_file": {"enabled": true, "level": "DEBUG"},
      "console": {"enabled": false},
      "syslog": {"enabled": true, "level": "INFO"}
    },
    "audit": {"level": "INFO"},
    "business_metrics": {"level": "INFO"}
  },
  
  "disk_monitor": {
    "min_free_space_mb": 500,
    "auto_cleanup_enabled": true,
    "photo_retention_days": 7,
    "log_retention_days": 30
  },
  
  "circuit_breaker": {
    "failure_threshold": 5,
    "recovery_timeout": 60,
    "half_open_max_calls": 3
  }
}
```

### Environment Variables (`.env`)

```env
# Supabase Configuration (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key

# Device Identification (Required)
DEVICE_ID=pi-lab-01

# SMS Configuration (Optional)
SMS_USERNAME=your_username
SMS_PASSWORD=your_password
SMS_DEVICE_ID=device_id
SMS_API_URL=https://api.example.com/sms
```

---

## 📊 System Operation

### Attendance Flow

1. **QR Code Scan** → Student number decoded and validated against daily roster
2. **Schedule Check** → Determine expected scan type (LOGIN/LOGOUT) and validate timing
3. **Face Capture** → Start auto-capture session with 9 quality checks
4. **Stability Wait** → All checks must pass continuously for 2 seconds
5. **Photo Save** → Capture saved to `data/photos/` with timestamp
6. **Database Write** → Local SQLite insert (atomic with queue entry)
7. **Cloud Sync** → If online, upload photo to Storage and attendance to database
8. **SMS Notification** → Send parent/guardian alert (with cooldown)
9. **Hardware Feedback** → Buzzer beep and LED indicator

### Face Quality Checks

Nine validation checks ensure photo quality:

1. **Face Size** - Minimum 60px width
2. **Centering** - Within 25% of frame center (both axes)
3. **Head Pose** - Yaw ≤35°, Pitch ≤35°, Roll ≤80°
4. **Eyes Open** - EAR ≥0.25 (Eye Aspect Ratio)
5. **Mouth Closed** - Opening ≤50% of face height
6. **Sharpness** - Laplacian variance ≥80
7. **Brightness** - Grayscale avg 70-180
8. **Illumination** - Std dev <40, dark pixels <20%
9. **Stability** - All checks pass for 2.0s continuously

Session timeout: 15 seconds

### Schedule System

**LOGIN Window:** 05:00 - 09:00
- Status: `present` if before 07:30, `late` after
- Cooldown: 10 minutes

**LOGOUT Window:** 15:00 - 18:00
- Status: `present` (on-time dismissal)
- Cooldown: 10 minutes

**Outside Windows:** Scans rejected unless device configured for all-day access

### Offline Mode

When network is unavailable:
1. Attendance saved to local SQLite (`synced=0`)
2. Record added to `sync_queue` with photo path
3. System continues normal operation
4. Auto-sync when connectivity restored
5. Exponential backoff on failures (30s → 60s → 120s, max 300s)

### Cloud Sync Details

**Student Lookup:**
```http
GET /rest/v1/students?student_number=eq.{number}&select=id
```

**Attendance Insert:**
```http
POST /rest/v1/attendance
Content-Type: application/json

{
  "student_id": "uuid",
  "date": "2025-12-11",
  "time_in": "07:15:30",
  "status": "present",
  "device_id": "pi-lab-01",
  "photo_url": "https://.../storage/.../photo.jpg",
  "remarks": "QR: 233653"
}
```

**Backend Enrichment:** Database trigger automatically adds `section_id`, `subject_id`, `teaching_load_id` based on device location from `iot_devices` table.

**Photo Upload:**
```http
POST /storage/v1/object/attendance-photos/{student}/{timestamp}.jpg
Content-Type: image/jpeg
```

---

## 🛠️ Administration

### Service Management

```bash
# Start service
sudo systemctl start attendance-system

# Stop service
sudo systemctl stop attendance-system

# Restart service
sudo systemctl restart attendance-system

# View status
sudo systemctl status attendance-system

# View logs (live)
sudo journalctl -u attendance-system -f

# View logs (recent)
sudo journalctl -u attendance-system --since "1 hour ago"
```

### Monitoring

```bash
# System health dashboard
python scripts/monitor.py

# Check system status
python utils/check_status.py

# View attendance records
python utils/view_attendance.py --today

# Test roster sync
python utils/test-scripts/test_roster_sync.py

# Test face quality
python utils/test-scripts/test_face_quality.py
```

### Maintenance

```bash
# Manual backup
python scripts/backup.py

# Cleanup old data
python scripts/cleanup_attendance_cache.py

# Force cloud sync
python -c "
from src.cloud.cloud_sync import CloudSyncManager
from src.database.sync_queue import SyncQueueManager
from src.network.connectivity import ConnectivityMonitor
from src.utils.config_loader import load_config

config = load_config('config/config.json')
sync_queue = SyncQueueManager()
connectivity = ConnectivityMonitor(config)
cloud = CloudSyncManager(config, sync_queue, connectivity)
result = cloud.force_sync_all()
print(result)
"

# Hardware check
python scripts/hw_check.py
```

### Log Management

Logs are written to multiple outputs:

- **System logs:** `data/logs/attendance_system_YYYYMMDD.log` (DEBUG level)
- **JSON logs:** `data/logs/attendance_system_YYYYMMDD.json` (structured)
- **Audit logs:** `data/logs/audit_YYYYMMDD.log` (security events)
- **Business logs:** `data/logs/business_metrics_YYYYMMDD.json` (KPIs)
- **Syslog:** via systemd journal (INFO level, identifier: `attendance-system`)

**View logs:**
```bash
# Today's system log
tail -f data/logs/attendance_system_$(date +%Y%m%d).log

# Syslog (systemd journal)
sudo journalctl -u attendance-system --since today

# Audit trail
tail -f data/logs/audit_$(date +%Y%m%d).log
```

**Configure log levels** in `config/config.json`:
```json
{
  "logging": {
    "level": "INFO",
    "outputs": {
      "file": {"level": "DEBUG"},
      "syslog": {"level": "INFO"}
    }
  }
}
```

---

## 🧪 Testing

```bash
# Run all tests
pytest -q

# Run unit tests only (fast)
pytest -q -m "not hardware and not integration"

# Run integration tests
pytest -q -m integration

# Run hardware tests (requires device)
pytest -q -m hardware

# Run specific test file
pytest -q tests/test_simple_flow.py

# Run with coverage
pytest --cov=src --cov-report=html
```

**Test markers:**
- `@pytest.mark.hardware` - Requires GPIO/camera hardware
- `@pytest.mark.integration` - Cross-component flows

---

## 🔍 Troubleshooting

### Common Issues

**1. Camera not detected**
```bash
# Check camera device
ls -la /dev/video*

# Test camera with OpenCV
python -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL')"

# Check config camera index
grep -A3 '"camera"' config/config.json
```

**2. Cloud sync failing**
```bash
# Verify credentials
grep SUPABASE .env

# Test connection
curl -s "${SUPABASE_URL}/rest/v1/" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}"

# Check circuit breaker status
grep -i "circuit.*open" data/logs/attendance_system_$(date +%Y%m%d).log
```

**3. Students not in roster**
```bash
# Check roster sync
sqlite3 data/attendance.db "SELECT COUNT(*) FROM students;"

# Force roster sync
python -c "
from src.sync.roster_sync import RosterSync
from src.utils.config_loader import load_config
config = load_config('config/config.json')
roster = RosterSync(config)
roster.sync_roster()
"
```

**4. SMS not sending**
```bash
# Check SMS config
grep SMS_ .env

# Check template cache
sqlite3 data/attendance.db "SELECT * FROM template_cache;"

# Check delivery log
sqlite3 data/attendance.db "SELECT * FROM sms_delivery_log ORDER BY sent_at DESC LIMIT 10;"
```

**5. Disk space issues**
```bash
# Check available space
df -h /home/iot/attendance-system

# Check photo directory size
du -sh data/photos/

# Run manual cleanup
python scripts/cleanup_attendance_cache.py
```

### Debug Mode

Enable debug logging temporarily:

```json
// config/config.json
{
  "logging": {
    "level": "DEBUG",
    "outputs": {
      "console": {"enabled": true, "level": "DEBUG"}
    }
  }
}
```

Restart service to apply:
```bash
sudo systemctl restart attendance-system
```

---

## 📚 Documentation

- **[Production Guide](docs/PRODUCTION_GUIDE.md)** - Deployment and operations
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Common tasks and commands
- **[System Overview](docs/technical/SYSTEM_OVERVIEW.md)** - Architecture details
- **[Auto Capture](docs/technical/AUTO_CAPTURE.md)** - Face quality system
- **[Cloud Integration](docs/technical/CLOUD_INTEGRATION.md)** - Supabase setup
- **[Logging Guide](docs/LOGGING_QUICK_REFERENCE.md)** - Log configuration
- **[Admin Guide](docs/ADMIN_GUIDE.md)** - Administration tasks
- **[Troubleshooting](docs/troubleshooting/)** - Issue resolution

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow code organization principles (see `.github/copilot-instructions.md`)
4. Add tests for new features
5. Ensure all tests pass (`pytest -q`)
6. Update documentation as needed
7. Commit changes (`git commit -m 'Add amazing feature'`)
8. Push to branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

**Code Style:**
- Functions/methods: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Add type hints for new code
- Document with docstrings
- Use appropriate log levels

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenCV** - Computer vision library
- **Supabase** - Backend as a Service
- **pyzbar** - QR code decoding
- **RPi.GPIO** - Raspberry Pi GPIO control

---

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation in `docs/`
- Review troubleshooting guides
- Check system logs for error details

---

**Built with ❤️ for educational institutions requiring reliable attendance tracking**
