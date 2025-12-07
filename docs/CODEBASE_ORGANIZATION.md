# Codebase Organization

Last organized: December 7, 2025

## Directory Structure

### Root Level
```
attendance-system/
├── attendance_system.py      # Main application entry point
├── start_attendance.sh        # System startup script
├── requirements.txt           # Python dependencies
├── pytest.ini                 # Test configuration
├── README.md                  # Main documentation
├── LICENSE                    # MIT License
├── .env                       # Environment variables (not in git)
├── .env.example               # Environment template
└── .gitignore                 # Git ignore rules
```

### Source Code (`src/`)
Core application modules organized by domain:

- `attendance/` - Schedule management and validation
- `auth/` - Authentication (if needed)
- `camera/` - Camera handling (OpenCV + Picamera2)
- `cloud/` - Supabase integration and photo upload
- `database/` - SQLite local cache and sync queue
- `hardware/` - GPIO devices (buzzer, LED, power button)
- `lighting/` - Lighting analysis and compensation
- `network/` - Connectivity monitoring
- `notifications/` - SMS notifications with templates
- `sync/` - Roster and schedule synchronization
- `utils/` - Shared utilities (logging, config, metrics, etc.)

### Configuration (`config/`)
- `config.json` - Main system configuration
- `defaults.json` - Default fallback values

### Scripts (`scripts/`)
Production and maintenance scripts:

**Production:**
- `start_attendance.sh` - Start system
- `status.py` - Check system status
- `health_check.sh` - Health monitoring
- `quick_check.sh` - Quick system validation

**Deployment:**
- `deployment/deploy.sh` - Main deployment script
- `deployment/install_service.sh` - Systemd service setup
- `deployment/migrate_supabase.sh` - Database migrations

**Maintenance:**
- `maintenance/detect_cameras.sh` - Camera detection
- `maintenance/fix_iot_devices_permissions.sh` - Permission fixes
- `backup.py` - Database backup
- `cleanup_attendance_cache.py` - Cache cleanup
- `force_sync.py` - Manual cloud sync

**Testing:**
- `generate_test_qr_codes.py` - QR code generation
- `hw_check.py` - Hardware validation
- `production_check.sh` - Pre-deployment checks

### Tests (`tests/`)
Pytest-based test suite:
- Unit tests for all modules
- Integration tests (marked with `@pytest.mark.integration`)
- Hardware tests (marked with `@pytest.mark.hardware`)
- See `tests/README.md` for test organization

### Utilities (`utils/`)
Helper scripts and test utilities:
- `manage_supabase_students.py` - Student management CLI
- `test-scripts/` - Manual testing scripts for debugging

### Documentation (`docs/`)
Comprehensive documentation:

**Main Guides:**
- `README.md` - Documentation index
- `QUICKSTART.md` - Quick setup guide
- `DEPLOYMENT.md` - Production deployment
- `API_INTEGRATION_GUIDE.md` - API reference

**Technical:**
- `technical/SYSTEM_OVERVIEW.md` - Architecture overview
- `technical/AUTO_CAPTURE.md` - Face quality system
- `technical/SUPABASE_SCHEMA_COMPLIANCE.md` - Database schema

**Testing:**
- `testing/TEST_REPORT_*.md` - Test reports (archived)
- `testing/test_system.sh` - Comprehensive system test script

**User Guides:**
- `user-guides/TEACHER_GUIDE.md` - For teachers
- `user-guides/ADMIN_GUIDE.md` - For administrators

### Data (`data/`)
Runtime data (all in `.gitignore`):
- `attendance.db` - Local SQLite cache
- `photos/` - Captured student photos
- `logs/` - System logs
- `exports/` - Data exports
- `qr_codes/` - Generated QR codes

### Supabase (`supabase/`)
Database schema and migrations:
- `migrations/` - SQL migration files (timestamped)
- `schemas/` - Schema documentation
- `sql/` - SQL utility scripts
- `functions/` - Database functions (if any)

### Public (`public/`)
Static web content (GitHub Pages):
- `view-attendance.html` - Public attendance viewer
- `README.md` - Public site documentation

## File Naming Conventions

### Python Files
- `snake_case.py` - All Python modules
- `test_*.py` - Test files (pytest discovery)

### Shell Scripts
- `kebab-case.sh` - All shell scripts
- Executable: `chmod +x script.sh`

### Documentation
- `UPPERCASE.md` - Root-level docs (README, LICENSE, etc.)
- `TitleCase.md` - Technical documentation
- `kebab-case.md` - Supplementary docs

### SQL Files
- `YYYYMMDDHHMMSS_description.sql` - Migration files
- `lowercase_description.sql` - Utility SQL scripts

## Code Organization Principles

### 1. Single Responsibility
Each module has one clear purpose. Example:
- `camera_handler.py` - Camera operations only
- `cloud_sync.py` - Cloud synchronization only
- `schedule_manager.py` - Schedule logic only

### 2. Dependency Direction
```
attendance_system.py (main)
    ↓
src/ (domain modules)
    ↓
utils/ (shared utilities)
```

### 3. Configuration Over Code
System behavior controlled via `config/config.json`, not hardcoded values.

### 4. Offline-First Architecture
- Local SQLite cache for all data
- Sync queue for offline operations
- Cloud is authoritative but optional

### 5. Clean Imports
```python
# Standard library
import os
from datetime import datetime

# Third-party
import cv2
import requests

# Local modules
from src.database.db_handler import AttendanceDatabase
from src.utils.logger_config import setup_logging
```

## Maintenance Tasks

### Regular Cleanup
```bash
# Remove Python cache (done automatically)
find . -type d -name "__pycache__" -delete

# Clean old logs (weekly)
python scripts/cleanup_attendance_cache.py

# Backup database (daily - automated via cron)
python scripts/backup.py
```

### Before Commits
```bash
# Run tests
pytest -q

# Check code organization
ls -R | grep -E "^\\..*|temp_|tmp"

# Verify .gitignore
git status --ignored
```

### Production Updates
1. Run `scripts/production_check.sh`
2. Deploy with `scripts/deployment/deploy.sh`
3. Verify with `scripts/health_check.sh`

## Clean Codebase Checklist

✅ No `__pycache__/` directories in git
✅ No `*.pyc` or `*.pyo` files in git
✅ No temporary files (`.tmp`, `temp_*`, etc.)
✅ All test reports in `docs/testing/`
✅ Scripts organized by purpose (production/deployment/maintenance)
✅ Documentation up-to-date
✅ `.gitignore` comprehensive
✅ Root directory minimal and clean

## Quick Commands

```bash
# Check codebase organization
ls -lh *.md *.py *.sh

# Find temporary files
find . -name "*.tmp" -o -name "temp_*" -o -name ".lgd-*"

# Count lines of code
find src -name "*.py" | xargs wc -l | tail -1

# List all scripts
find scripts -name "*.sh" -o -name "*.py" | sort

# Verify test coverage
pytest --cov=src --cov-report=term-missing
```

---

**Note:** This organization follows the principles outlined in `.github/copilot-instructions.md`. Any changes to structure should maintain these conventions.
