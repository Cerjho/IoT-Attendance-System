# Utility Scripts

## Active Utilities

### manage_supabase_students.py
Supabase student management utility.

**Purpose:** Add, update, or remove students from Supabase database.

**Usage:**
```bash
cd /home/iot/attendance-system
source venv/bin/activate
python3 utils/manage_supabase_students.py
```

**Features:**
- Add new students
- Update student information
- Remove students
- View student list
- Update parent contact numbers

## Archive

Old/deprecated utility scripts are stored in `archive/` directory:
- `check_status.py` - Legacy status checker
- `view_attendance.py` - Legacy attendance viewer
- `generate_qr.py` - Old QR generator
- `manage_parents.py` - Legacy parent manager
- `migrate_database.py` - Old migration script

These have been replaced by newer implementations in the main codebase.
