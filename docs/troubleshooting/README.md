# Troubleshooting Guide

This directory contains detailed documentation for errors and issues encountered during development and deployment.

## Documents

- **[ERRORS_FIXED.md](ERRORS_FIXED.md)** - Comprehensive list of all errors found and fixed (Dec 6, 2025)
  - Qt GUI display error
  - Python import errors
  - Systemd service dependency issues
  - Supabase permission errors (401)
  - Camera segmentation fault

- **[SEGFAULT_FIXED.md](SEGFAULT_FIXED.md)** - Detailed analysis of the camera segmentation fault issue
  - Root cause analysis
  - Fix implementation
  - Verification steps
  - Camera detection utility

## Quick Fixes

### Camera Not Working
```bash
# Check if camera is detected
bash scripts/maintenance/detect_cameras.sh

# If camera is in use by systemd service
sudo systemctl stop attendance-system
```

### Cloud Sync Failing (401 Permission Error)
The Supabase trigger permissions have been fixed. If you still see 401 errors:
1. Apply the SQL migration: `supabase/migrations/20251206120000_fix_iot_devices_permissions.sql`
2. Run force sync: `python scripts/force_sync.py`

### Import Errors
Ensure you're using the virtual environment:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Related Documentation

- [Production Guide](../PRODUCTION_GUIDE.md)
- [Deployment Guide](../DEPLOYMENT.md)
- [Scripts README](../../scripts/README.md)
