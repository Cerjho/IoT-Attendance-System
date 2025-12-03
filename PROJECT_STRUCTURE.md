# IoT Attendance System - Project Structure

## Root Directory
```
attendance-system/
├── attendance_system.py          # Main entry point
├── start_attendance.sh            # Quick start script (delegates to scripts/)
├── requirements.txt               # Python dependencies
├── pytest.ini                     # Pytest configuration
├── README.md                      # Project overview
├── PROJECT_STRUCTURE.md           # This file
├── QUICK_ACCESS.md                # Quick command reference
└── .env                           # Environment variables (not in git)
```

## Source Code (`src/`)
```
src/
├── __init__.py
├── face_quality.py                # Face quality checker (9 checks + stability)
├── attendance/                    # Attendance logic
│   ├── __init__.py
│   └── schedule_manager.py        # LOGIN/LOGOUT windows, late status
├── auth/                          # Authentication
│   ├── __init__.py
│   └── url_signer.py              # URL signing for secure links
├── camera/                        # Camera handling
│   ├── __init__.py
│   └── camera_handler.py          # OV5647 camera interface
├── cloud/                         # Cloud synchronization
│   ├── __init__.py
│   ├── cloud_sync.py              # Supabase REST API sync
│   └── photo_uploader.py          # Storage bucket uploads
├── database/                      # Local database
│   ├── __init__.py
│   ├── db_handler.py              # SQLite operations
│   ├── device_registry.py         # Device management
│   └── sync_queue.py              # Offline queue + archive
├── hardware/                      # GPIO hardware
│   ├── __init__.py
│   ├── buzzer_controller.py       # Audio feedback
│   ├── rgb_led_controller.py      # Visual indicators
│   └── power_button.py            # Shutdown button
├── lighting/                      # Lighting analysis
│   ├── __init__.py
│   ├── lighting_analyzer.py       # Illumination detection
│   └── lighting_compensator.py    # Auto-compensation
├── network/                       # Network connectivity
│   ├── __init__.py
│   └── connectivity.py            # Online/offline detection
├── notifications/                 # Notifications
│   ├── __init__.py
│   └── sms_notifier.py            # SMS-Gate integration
├── sync/                          # Data synchronization
│   ├── __init__.py
│   └── roster_sync.py             # Daily roster updates
└── utils/                         # Utilities
    ├── __init__.py
    ├── admin_dashboard.py         # Admin HTTP dashboard
    ├── circuit_breaker.py         # Circuit breaker pattern
    ├── config_loader.py           # Configuration loading
    ├── db_transactions.py         # Transaction safety
    ├── disk_monitor.py            # Disk space monitoring
    ├── file_locks.py              # File locking
    ├── logger_config.py           # Logging setup
    ├── multi_device_manager.py    # Multi-device coordination
    ├── network_timeouts.py        # Network timeout configs
    ├── queue_validator.py         # Queue data validation
    ├── realtime_monitor.py        # Real-time monitoring engine
    └── structured_logging.py      # Structured log output
```

## Scripts (`scripts/`)
```
scripts/
├── backup.py                      # Backup utility
├── cleanup_attendance_cache.py    # Cache cleanup
├── deploy_production.sh           # Production deployment
├── force_sync.py                  # Force cloud sync
├── generate_ssl_cert.sh           # SSL certificate generation
├── health_check.sh                # Health monitoring
├── health_monitor.sh              # Continuous monitoring
├── hw_check.py                    # Hardware validation
├── migrate_add_uuid.py            # Database migration
├── monitor.py                     # System monitor
├── nginx_dashboard.conf           # Nginx configuration
├── production_check.sh            # Production validation
├── production_health_check.sh     # Production health
├── production_optimization.sh     # Production optimization
├── quick_check.sh                 # Quick system check
├── realtime_dashboard.py          # Real-time monitoring dashboard
├── setup.sh                       # Initial setup
├── start_attendance.sh            # Main startup script
├── start_dashboard_only.py        # Dashboard-only mode
├── start_dashboard.sh             # Admin dashboard startup
├── start_monitor.sh               # Monitoring dashboard startup
├── status.py                      # System status
├── validate_deployment.sh         # Deployment validation
├── README.md                      # Scripts documentation
├── README_DASHBOARD.md            # Dashboard operations
├── deployment/                    # Deployment scripts
└── tests/                         # Script tests
    ├── test_endpoints.sh          # API endpoint tests
    ├── test_ip_whitelist.sh       # IP whitelist tests
    └── test_security.sh           # Security tests
```

## Tests (`tests/`)
```
tests/
├── conftest.py                    # Pytest fixtures
├── test_admin_dashboard.py        # Dashboard tests
├── test_alerts.py                 # Alert system tests
├── test_all_sms_templates.py      # SMS template tests
├── test_attendance_page.py        # Attendance page tests
├── test_circuit_breaker.py        # Circuit breaker tests
├── test_cloud_sync_extended.py    # Extended cloud sync tests
├── test_cloud_sync_unit.py        # Cloud sync unit tests
├── test_db_transactions.py        # Transaction tests
├── test_disk_monitor.py           # Disk monitor tests
├── test_env_security.py           # Environment security tests
├── test_face_quality.py           # Face quality tests
├── test_file_locks.py             # File locking tests
├── test_hardware_camera.py        # Camera hardware tests
├── test_queue_sync_integration.py # Queue sync integration
├── test_real_complete_flow.py     # Complete flow test
├── test_simple_flow.py            # Simple flow test
├── test_sms_quick.sh              # Quick SMS test
└── test_system_integration.py     # System integration tests
```

## Documentation (`docs/`)
```
docs/
├── README.md                      # Documentation index
├── ADMIN_CONFIG_MANAGEMENT.md     # Config management
├── API_INTEGRATION_GUIDE.md       # API integration
├── CONFIG_MANAGEMENT_QUICKREF.md  # Config quick ref
├── DASHBOARD_DEPLOYMENT.md        # Dashboard deployment
├── DASHBOARD_TEST_GUIDE.md        # Dashboard testing
├── DEPLOYMENT.md                  # General deployment
├── HARDWARE_REFERENCE.md          # Hardware specs
├── MONITORING_QUICKREF.md         # Monitoring quick ref
├── MULTI_DEVICE_MANAGEMENT.md     # Multi-device setup
├── MULTI_DEVICE_QUICKSTART.md     # Multi-device quickstart
├── PRODUCTION_DASHBOARD.md        # Production dashboard
├── PRODUCTION_GUIDE.md            # Production guide
├── QUICK_REFERENCE.md             # General quick ref
├── QUICKSTART.md                  # Getting started
├── REALTIME_MONITORING.md         # Real-time monitoring guide
├── view-attendance.html           # Attendance viewer
├── security/                      # Security documentation
│   ├── IP_WHITELIST_CONFIG.md
│   ├── SECURE_DEPLOYMENT_SUMMARY.md
│   └── SECURITY_SETUP.md
├── summaries/                     # Implementation summaries
│   ├── CRASH_FIXES_APPLIED.md
│   ├── DEPLOYMENT_CRASH_RISKS.md
│   ├── DEPLOYMENT_READY.md
│   └── REALTIME_MONITORING_SUMMARY.md
├── technical/                     # Technical documentation
│   ├── AUTO_CAPTURE.md
│   └── SYSTEM_OVERVIEW.md
└── user-guides/                   # User guides
    └── ...
```

## Data (`data/`)
```
data/
├── attendance.db                  # SQLite database
├── exports/                       # Exported data
│   └── attendance_export_*.json
├── logs/                          # Application logs
│   └── attendance_YYYYMMDD.log
├── photos/                        # Captured photos
│   └── STUDENTID_TIMESTAMP.jpg
└── qr_codes/                      # Generated QR codes
    └── *.png
```

## Configuration (`config/`)
```
config/
├── config.json                    # Main configuration
└── defaults.json                  # Default configuration
```

## Supabase (`supabase/`)
```
supabase/
├── functions/                     # Supabase functions
├── migrations/                    # Database migrations
└── sql/                          # SQL scripts
```

## Public (`public/`)
```
public/
├── README.md                      # Public files documentation
├── multi-device-dashboard.html    # Multi-device dashboard
└── view-attendance.html           # Public attendance viewer
```

## Utilities (`utils/`)
```
utils/
├── check_status.py                # Status checker
└── test-scripts/                  # Test utilities
    ├── test_face_quality.py
    ├── test_realtime_monitor.py
    └── test_roster_sync.py
```

## Backups (`backups/`)
```
backups/
└── backup_YYYYMMDD_HHMMSS/       # Timestamped backups
    ├── attendance.db
    └── photos/
```

## Key Files

### Entry Points
- `attendance_system.py` - Main application
- `scripts/start_attendance.sh` - Production startup
- `scripts/start_dashboard.sh` - Admin dashboard
- `scripts/start_monitor.sh` - Real-time monitoring

### Configuration
- `config/config.json` - Main configuration
- `.env` - Environment variables (secrets)
- `requirements.txt` - Python dependencies
- `pytest.ini` - Test configuration

### Documentation
- `README.md` - Project overview
- `docs/QUICKSTART.md` - Getting started
- `docs/REALTIME_MONITORING.md` - Monitoring guide
- `.github/copilot-instructions.md` - AI assistant guidelines

## Directory Purpose

| Directory | Purpose | Git Tracked |
|-----------|---------|-------------|
| `src/` | Source code | Yes |
| `scripts/` | Operational scripts | Yes |
| `tests/` | Test suite | Yes |
| `docs/` | Documentation | Yes |
| `config/` | Configuration files | Yes |
| `data/` | Runtime data | Structure only |
| `backups/` | System backups | No |
| `public/` | Public HTML files | Yes |
| `supabase/` | Database schema | Yes |
| `utils/` | Utility scripts | Yes |

## Notes

- All Python cache files (`__pycache__`, `*.pyc`) are gitignored
- Data directories preserve structure via `.gitkeep` files
- Actual data files (`*.db`, photos, logs) are not tracked
- Backups are excluded from version control
- Environment secrets (`.env`) are never committed

## Organization Principles

1. **Domain-driven structure** - Code organized by business domain (camera, cloud, database)
2. **Clear separation** - Source code, scripts, tests, and docs in separate directories
3. **Documentation proximity** - Related docs near relevant code
4. **Data isolation** - Runtime data separate from code
5. **Backup safety** - Backups excluded from version control
6. **Cache exclusion** - All temporary files gitignored
7. **Structure preservation** - Empty directories maintained via .gitkeep
