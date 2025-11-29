# IoT Attendance System

Advanced face recognition attendance system for Raspberry Pi with automatic quality validation, offline capability, and cloud synchronization.

## Features

✨ **Automatic Face Capture** - 9 quality checks with 3-second stability requirement  
🚀 **Lightning-Fast Scanning** - < 100ms response time with offline capability  
☁️ **Cloud-First Architecture** - Supabase primary database with local SQLite cache  
🔒 **Privacy Compliant** - Daily roster sync with automatic cache wipe  
📱 **SMS Notifications** - Real-time parent/guardian notifications  
🎯 **QR Code Validation** - Student verification against daily roster  

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/Cerjho/IoT-Attendance-System.git
cd IoT-Attendance-System

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit `config/config.json` with your Supabase credentials:

```json
{
  "cloud": {
    "enabled": true,
    "url": "https://your-project.supabase.co",
    "api_key": "your_api_key_here"
  }
}
```

### 3. Setup Supabase

```bash
# Create students table in Supabase
# See docs/technical/SUPABASE_SETUP.md for SQL schema

# Add students
python utils/manage_supabase_students.py --import-csv data/students_template.csv
```

### 4. Run System

```bash
# Start attendance system
python attendance_system.py

# Or run in headless mode (no display)
bash start_attendance.sh --headless
```

## Project Structure

```
IoT-Attendance-System/
├── attendance_system.py          # Main application
├── start_attendance.sh            # Startup script
├── requirements.txt               # Python dependencies
├── config/
│   └── config.json               # System configuration
├── src/                          # Source code modules
│   ├── camera/                   # Camera handling
│   ├── cloud/                    # Cloud sync (Supabase)
│   ├── database/                 # Local SQLite cache
│   ├── face_quality.py           # Quality assessment
│   ├── hardware/                 # Buzzer, GPIO control
│   ├── lighting/                 # Lighting analysis
│   ├── network/                  # Connectivity monitoring
│   ├── notifications/            # SMS notifications
│   ├── sync/                     # Roster synchronization
│   └── utils/                    # Utilities and helpers
├── utils/                        # Utility scripts
│   ├── manage_supabase_students.py  # Student management
│   ├── check_status.py           # System status checker
│   ├── view_attendance.py        # View attendance records
│   ├── generate_qr.py            # QR code generator
│   └── test-scripts/             # Test utilities
├── scripts/                      # Automation scripts
│   ├── auto_cleanup.py           # Automatic cleanup
│   └── sync_to_cloud.py          # Manual cloud sync
├── data/                         # Data storage
│   ├── attendance.db             # Local SQLite cache
│   ├── photos/                   # Captured photos
│   ├── qr_codes/                 # Generated QR codes
│   └── logs/                     # System logs
├── docs/                         # Documentation
│   ├── user-guides/              # User documentation
│   ├── technical/                # Technical documentation
│   └── archived/                 # Archived/historical docs
└── supabase/                     # Supabase configuration
    └── migrations/               # Database migrations
```

## Documentation

### User Guides
- **[Quick Start](docs/user-guides/QUICKSTART.md)** - Get started in 5 minutes
- **[Roster Sync Guide](docs/user-guides/QUICKSTART_ROSTER.md)** - Setup daily roster sync
- **[SMS Setup](docs/user-guides/SMS_QUICKSTART.md)** - Configure SMS notifications
- **[Quick Reference](docs/user-guides/QUICK_REFERENCE.md)** - Common commands

### Technical Documentation
- **[System Overview](docs/technical/SYSTEM_OVERVIEW.md)** - Architecture and components
- **[Auto-Capture System](docs/technical/AUTO_CAPTURE.md)** - Face quality validation
- **[Roster Sync](docs/technical/ROSTER_SYNC.md)** - Daily roster synchronization
- **[Supabase Setup](docs/technical/SUPABASE_SETUP.md)** - Database configuration
- **[SMS Notifications](docs/technical/SMS_NOTIFICATION_GUIDE.md)** - SMS integration

## Key Workflows

### Daily Operation

**Morning (6 AM or on boot)**
```
System starts → Download today's roster from Supabase
→ Cache 30-100 students locally → Ready for offline scanning
```

**During Class**
```
Student scans QR → Validate against roster → Face quality checks
→ Auto-capture after 3s stability → Upload to Supabase → SMS notification
```

**Evening (6 PM)**
```
Auto-wipe student cache → Privacy compliance maintained
```

### Auto-Capture Process

1. **QR Code Scan** - Student ID validation against roster
2. **Quality Monitoring** - 9 simultaneous checks:
   - Face count (exactly 1)
   - Face size (≥ 80px width)
   - Face centered (±12%)
   - Head pose (yaw/pitch/roll limits)
   - Eyes open (EAR > 0.25)
   - Mouth closed
   - Sharpness (Laplacian > 80)
   - Brightness (70-180 range)
   - Illumination uniformity
3. **Stability Timer** - 3-second countdown when all checks pass
4. **Capture & Upload** - High-quality photo saved and uploaded

## Hardware Requirements

- **Raspberry Pi 4B** (recommended) or 3B+
- **Camera** - Raspberry Pi Camera Module v1/v2 or USB webcam
- **Buzzer** (optional) - GPIO-connected for audio feedback
- **Internet** - For initial roster sync and attendance upload

## Performance

- **Startup**: 5-10 seconds
- **Roster Sync**: 2-5 seconds (once daily)
- **QR Validation**: < 100ms (offline)
- **Auto-Capture**: 3-8 seconds (with quality validation)
- **Upload**: 200-500ms (when online)

## Development

### Testing

```bash
# Test roster sync
python utils/test-scripts/test_roster_sync.py

# Test face quality
python utils/test-scripts/test_face_quality.py

# Check system status
python utils/check_status.py
```

### Adding Students

```bash
# Add single student
python utils/manage_supabase_students.py --add STU001 --name "John Doe"

# Import from CSV
python utils/manage_supabase_students.py --import-csv data/students.csv

# List students
python utils/manage_supabase_students.py --list
```

### Viewing Attendance

```bash
# View today's attendance
python utils/view_attendance.py

# Export to JSON
python utils/view_attendance.py --export
```

## Troubleshooting

### Camera not working
```bash
# Check camera detection
libcamera-hello --list-cameras

# Test capture
libcamera-still -o test.jpg
```

### Roster sync fails
```bash
# Check Supabase connection
curl -X GET "https://your-project.supabase.co/rest/v1/students?limit=1" \
  -H "apikey: your_api_key"

# Force manual sync
python utils/test-scripts/test_roster_sync.py
```

### Student rejected
- Verify student exists in Supabase
- Check if roster was synced today
- Force re-sync roster

### Manual Force Sync
If records are queued offline, you can force a sync when online:
```bash
source .venv/bin/activate
python scripts/force_sync.py
```
This loads `config/config.json`, checks connectivity, uploads any pending photos to Storage, and inserts attendance via Supabase REST. See `scripts/force_sync.py` for details.

## Contributing

Contributions are welcome! Please read the contribution guidelines before submitting PRs.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues
- **Logs**: Check `data/logs/attendance_system.log`

## Acknowledgments

- Face detection: OpenCV Haar Cascades
- Cloud backend: Supabase
- SMS gateway: SMS-Gate
- Camera interface: Picamera2

---

**Last Updated**: November 25, 2025  
**Version**: 2.0.0
