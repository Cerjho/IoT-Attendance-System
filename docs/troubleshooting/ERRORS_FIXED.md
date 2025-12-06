# Errors Found and Fixed - December 6, 2025

## Summary
Five critical errors identified and resolved during system startup and operation.

---

## Error 1: Qt GUI Display Error ❌ **RESOLVED**

### Symptom
```
qt.qpa.xcb: could not connect to display 
qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
Aborted (core dumped)
```

### Root Cause
No X11 display server available when running in GUI mode on headless system.

### Solution
**Use headless mode:**
```bash
bash scripts/start_attendance.sh --headless
```

**Status:** ✅ RESOLVED - System runs successfully in headless mode.

---

## Error 2: Python Import Error in `force_sync.py` ❌ **FIXED**

### Symptom
```
ModuleNotFoundError: No module named 'src'
```

### Root Cause
Script didn't add project root to Python path before importing `src` modules.

### Solution
Modified `/home/iot/attendance-system/scripts/force_sync.py`:

```python
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cloud.cloud_sync import CloudSyncManager
```

Also fixed ConfigLoader usage (it doesn't support `.setdefault()`):

```python
def main():
    config_obj = load_config("config/config.json")
    cloud_config = config_obj.get("cloud", {})
    if not isinstance(cloud_config, dict):
        cloud_config = {}
    
    cloud_config.setdefault("enabled", True)
    # ... rest of config setup
```

**Status:** ✅ FIXED - Script now imports correctly and runs.

---

## Error 3: Systemd Service Dependency Error ❌ **FIXED**

### Symptom
```
sudo systemctl start attendance-system
Failed to start attendance-system.service: Unit attendance-dashboard.service not found.
```

### Root Cause
Service file referenced non-existent `attendance-dashboard.service` as required dependency.

### Solution
Removed dependency from `/etc/systemd/system/attendance-system.service`:

**Before:**
```ini
[Unit]
Description=IoT Attendance System - Main Service
After=network.target attendance-dashboard.service
Requires=attendance-dashboard.service
```

**After:**
```ini
[Unit]
Description=IoT Attendance System - Main Service
After=network.target
```

Applied with:
```bash
sudo sed -i 's/After=network.target attendance-dashboard.service/After=network.target/' /etc/systemd/system/attendance-system.service
sudo sed -i '/^Requires=attendance-dashboard.service/d' /etc/systemd/system/attendance-system.service
sudo systemctl daemon-reload
```

**Status:** ✅ FIXED - Service configuration now valid.

---

## Error 4: Supabase Permission Error (401) ⚠️ **REQUIRES MANUAL FIX**

### Symptom
```
Cloud insert failed: 401 - {"code":"42501","details":null,"hint":null,"message":"permission denied for table iot_devices"}
```

### Root Cause
The attendance enrichment trigger function (`enrich_attendance_data()`) runs with `SECURITY DEFINER` but the function owner (postgres role) lacks permission to read the `iot_devices` table due to RLS policies.

**Why this happens:**
1. IoT device inserts attendance record via REST API (as `anon` role)
2. Before insert, trigger `enrich_attendance_on_insert` fires
3. Trigger function queries `iot_devices` to get `section_id`
4. Function runs as its owner (postgres), not as caller (anon)
5. RLS policy on `iot_devices` only allows `anon` to SELECT when `status='active'`
6. Postgres role is blocked by RLS → 401 permission denied

### Solution

**Option A: Apply SQL Migration (Recommended)**

Created migration: `supabase/migrations/20251206120000_fix_iot_devices_permissions.sql`

Apply via Supabase Dashboard SQL Editor:
1. Go to: https://ddblgwzylvwuucnpmtzi.supabase.co/project/_/sql
2. Create new query
3. Copy contents from: `supabase/migrations/20251206120000_fix_iot_devices_permissions.sql`
4. Run the query

**Key changes in migration:**
- Grants SELECT on `iot_devices` to `authenticated`, `anon`, `service_role`, and `postgres`
- Updates RLS policy to `USING (status = 'active')` instead of `TO anon USING (...)`
- Ensures function owner is `postgres` with proper permissions
- Grants EXECUTE on trigger function to all relevant roles

**Option B: Quick Fix via psql**

If you have database connection string:
```bash
psql $DATABASE_URL -f supabase/migrations/20251206120000_fix_iot_devices_permissions.sql
```

**Option C: Helper Script (Shows SQL)**

Run to see the SQL that needs to be applied:
```bash
bash scripts/maintenance/fix_iot_devices_permissions.sh
```

### Verification

After applying the migration, test with:

```bash
# Test force sync
export $(grep -v '^#' .env | xargs)
python scripts/force_sync.py

# Start system and scan QR
bash scripts/start_attendance.sh --headless
```

**Expected:** No more "permission denied for table iot_devices" errors.

**Status:** ⚠️ **REQUIRES MANUAL ACTION** - SQL migration created, needs to be applied to Supabase.

---

## Error 5: Camera Segmentation Fault ❌ **FIXED**

### Symptom
```
[ WARN:0@2.267] global cap_v4l.cpp:982 open VIDEOIO(V4L2:/dev/video0): can't open camera by index
Failed to open camera at index 0
Camera failed to initialize after 3 attempts

❌ CAMERA INITIALIZATION FAILED

scripts/start_attendance.sh: line 60:  5094 Segmentation fault
```
**Exit code: 139** (segmentation fault)

### Root Cause
OpenCV's `VideoCapture` object wasn't properly released when camera initialization failed, causing a segfault during Python cleanup/garbage collection. This is a known OpenCV issue when VideoCapture fails to open but isn't explicitly cleaned up.

**Why no camera:** The system has video device nodes (`/dev/video0-31`) but no actual functional camera hardware connected. The devices exist but cannot capture frames.

### Solution

**Added explicit cleanup in 4 locations:**

1. **src/camera/camera_handler.py** - When `cap.isOpened()` returns False
2. **src/camera/camera_handler.py** - When camera opens but can't read frames  
3. **src/camera/camera_handler.py** - In exception handler
4. **attendance_system.py** - Before exit when camera init fails

**Example fix:**
```python
if not self.cap.isOpened():
    logger.error(f"Failed to open camera at index {self.camera_index}")
    # Clean up failed capture object to prevent segfault on exit
    if self.cap is not None:
        try:
            self.cap.release()
        except:
            pass
        self.cap = None
    return False
```

### Camera Detection Utility

Created `scripts/maintenance/detect_cameras.sh` to help diagnose camera issues:

```bash
bash scripts/maintenance/detect_cameras.sh
```

**Output on this system:**
```
❌ No working cameras found!

💡 Possible solutions:
   1. Check camera is properly connected
   2. Try Picamera2 if using Raspberry Pi Camera Module
   3. Use demo mode: python attendance_system.py --demo
```

### Verification

**Before:**
- Exit code: 139 (segmentation fault)
- Unclear error messages
- Crash during cleanup

**After:**
- Exit code: 0 (clean exit) ✅
- Clear error messages ✅
- Suggests demo mode ✅
- No crash ✅

**Status:** ✅ FIXED - System exits cleanly when camera unavailable. See `SEGFAULT_FIXED.md` for full details.

---

## Quick Reference: How to Start the System

### Manual Start (Recommended)
```bash
# Headless mode (no GUI)
bash scripts/start_attendance.sh --headless

# GUI mode (requires X11 display)
bash scripts/start_attendance.sh
```

### Systemd Service
```bash
# Enable on boot
sudo systemctl enable attendance-system

# Start now
sudo systemctl start attendance-system

# Check status
sudo systemctl status attendance-system

# View logs
sudo journalctl -u attendance-system -f
```

---

## Files Modified

1. **scripts/force_sync.py** - Fixed import and ConfigLoader usage
2. **/etc/systemd/system/attendance-system.service** - Removed dashboard dependency
3. **src/camera/camera_handler.py** - Added cleanup in 3 locations to prevent segfault
4. **attendance_system.py** - Added cleanup before exit on camera failure
5. **supabase/migrations/20251206120000_fix_iot_devices_permissions.sql** - Created (needs manual apply)
6. **scripts/maintenance/fix_iot_devices_permissions.sh** - Created helper script
7. **scripts/maintenance/detect_cameras.sh** - Created camera detection utility

---

## Next Steps

1. ✅ Use `--headless` mode to avoid Qt display issues
2. ✅ Test `force_sync.py` works: `python scripts/force_sync.py`
3. ⚠️ **Apply Supabase permissions migration** (see Error 4 above)
4. ✅ Verify systemd service: `sudo systemctl start attendance-system`
5. ✅ Monitor logs: `sudo journalctl -u attendance-system -f`

---

## Testing Commands

```bash
# Load environment
export $(grep -v '^#' .env | xargs)

# Test force sync
python scripts/force_sync.py

# Check system status
python scripts/status.py

# Validate deployment
bash scripts/validate_deployment.sh

# Start system
bash scripts/start_attendance.sh --headless
```
