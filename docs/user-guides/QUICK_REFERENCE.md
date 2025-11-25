# Quick Reference: Updated Attendance Flow

## The New Flow (5 Phases)

```
CAPTURE → LOCAL PERSIST → CLOUD SYNC → CLEANUP → STANDBY
```

### Phase 1️⃣: CAPTURE
- QR code scanned
- Face detected (5-second window)
- Photo saved to disk (blocking)

### Phase 2️⃣: LOCAL PERSIST ✓
- Attendance record created in SQLite
- Status: `synced=0` (not yet synced)
- **Guaranteed locally** - even if cloud sync fails

### Phase 3️⃣: CLOUD SYNC
- **If ONLINE**: Try to sync immediately
  - Upload photo → Supabase Storage
  - Insert record → Supabase DB
  - Mark `synced=1`
  - **Delete local photo** ✓

- **If OFFLINE**: Queue for later
  - Add to sync_queue table
  - Keep local photo (needed for retry)
  - Return to standby (fast!)

### Phase 4️⃣: CLEANUP
- **Immediate** (if sync succeeded) → Delete photo now
- **Delayed** (if sync queued) → Keep photo, delete after background sync

### Phase 5️⃣: STANDBY
- Ready for next QR scan
- Background sync processes queue every 60s

---

## Key Methods

### In `src/cloud/cloud_sync.py`

```python
# Delete photo after successful sync
def _delete_local_photo(photo_path: str) -> bool:
    """Safely delete local photo"""
```

Called in:
- `sync_attendance_record()` - After immediate sync
- `process_sync_queue()` - After queued record syncs
- `force_sync_all()` - After manual force sync

### In `src/database/sync_queue.py`

```python
# Cleanup helper (can be called independently)
def cleanup_photo(photo_path: str) -> bool:
    """Delete photo after cloud sync confirmed"""
```

### In `attendance_system.py`

```python
# Enhanced with clear phase logging
def upload_to_database(student_id, photo_path, qr_data):
    # ✓ LOCAL: Record locally
    # ☁️  CLOUD: Attempt sync
    # ⟳ QUEUE: Queue if offline
    # ✓ SMS: Send notification
```

---

## Command Reference

### Check Sync Status
```bash
python scripts/sync_to_cloud.py
```

Output shows:
```
Cloud Sync: ✅ Enabled
Online: ✅ Yes
Unsynced Records: 0
Queue Size: 0
```

### Monitor Photos
```bash
# List local photos
ls -la photos/

# Count photos
ls photos/*.jpg | wc -l

# Check disk usage
du -sh photos/
```

### View Database State
```bash
# Count synced vs unsynced
sqlite3 data/attendance.db "SELECT synced, COUNT(*) FROM attendance GROUP BY synced;"

# Queue size
sqlite3 data/attendance.db "SELECT COUNT(*) FROM sync_queue;"

# Device status
sqlite3 data/attendance.db "SELECT * FROM device_status;"
```

### Monitor Logs
```bash
# Real-time flow tracking
tail -f logs/attendance_system_*.log | grep -E "(✓|⟳|❌|synced|queue)"

# Just sync operations
tail -f logs/attendance_system_*.log | grep -i sync

# Photo operations
tail -f logs/attendance_system_*.log | grep -i photo
```

---

## Configuration

In `config/config.json`:

```json
{
  "cloud": {
    "enabled": true,              // Enable cloud sync
    "sync_on_capture": true,      // Try immediate sync after capture
    "sync_interval": 60,          // Background sync every 60s
    "retry_attempts": 3,          // Max retries for queued records
    "retry_delay": 30             // Wait 30s between retries
  },
  "offline_mode": {
    "enabled": true,              // Enable offline queue
    "auto_sync_when_online": true // Resume queue when online
  }
}
```

---

## Scenarios

### Scenario A: Online ✅
```
1. QR Scan
2. Face Detected
3. Photo Saved (500ms)
4. Record Locally (550ms)
5. Sync Immediately
   ├─ Upload Photo (1s)
   ├─ Insert to Supabase (1s)
   ├─ Mark Synced (100ms)
   └─ DELETE Photo ✓
6. Return to Standby

Total: ~2.2 seconds
Result: Photo cleaned, data synced
```

### Scenario B: Offline ⟳
```
1. QR Scan
2. Face Detected
3. Photo Saved
4. Record Locally
5. Check Online: NO
   ├─ Add to queue
   └─ Keep Photo
6. Return to Standby (fast!)

Total: ~0.6 seconds
Result: Photo kept locally, queued

[Later when online...]
7. Background sync runs
   ├─ Uploads Photo
   ├─ Inserts to Supabase
   ├─ Marks Synced
   └─ DELETE Photo ✓
```

### Scenario C: Sync Fails ❌
```
1. QR Scan
2. Face Detected
3. Photo Saved
4. Record Locally
5. Try Sync: FAIL (timeout/error)
   ├─ Add to queue (retry_count=0)
   └─ Keep Photo
6. Return to Standby

[Next 60 seconds...]
7. Background sync tries again
   ├─ Photo upload succeeds
   ├─ But DB insert fails
   └─ Increment retry_count=1, keep photo

[Next 60 seconds...]
8. Background sync tries again (retry 2)
   └─ Success! Delete photo ✓

Or after 3 retries:
9. Give up, remove from queue, keep photo for manual recovery
```

---

## Data States

| Stage | photo_path | Local DB | sync | Cloud DB | photo_url |
|-------|-----------|----------|------|----------|-----------|
| After capture | ✓ | ✓ | 0 | - | - |
| Online sync | ✓→✗ | ✓ | 1 | ✓ | ✓ |
| Offline | ✓ | ✓ | 0 | - | - |
| Queue processing | ✓ | ✓ | 0 | - | - |
| Queue sync success | ✗ | ✓ | 1 | ✓ | ✓ |
| Queue sync fail | ✓ | ✓ | 0 | - | - |

---

## Disk Usage

Typical sizes:
- Photo: 100-500 KB (depends on resolution)
- Attendance record: ~500 bytes
- Queue entry: ~1-2 KB
- Database backup: ~50-300 KB

After cleanup:
- 10 students/day × 365 days = 3,650 records
- 3,650 × 200 KB (avg) = ~730 MB cleaned per year
- With cleanup: ~50-100 MB on disk at any time
- Without cleanup: ~730 MB

---

## Logging Examples

### Successful Online Sync
```
✓ LOCAL: Attendance recorded (Record ID: 42, Photo: photos/attendance_2021001_20251124_150530.jpg)
✓ CLOUD: Attendance synced successfully (local photo deleted)
✓ SMS: Notification sent to parent of 2021001
```

### Offline with Queue
```
✓ LOCAL: Attendance recorded (Record ID: 43, Photo: photos/attendance_2021002_20251124_150530.jpg)
⟳ QUEUE: Attendance queued for later sync (offline or failed, photo kept locally)
```

### Background Queue Processing
```
INFO: Processing 5 pending sync records
INFO: Synced queued record 1 (attendance ID 43)
INFO: Deleted local photo: photos/attendance_2021002_20251124_150530.jpg
INFO: Sync queue processed: 5 succeeded, 0 failed
```

---

## Troubleshooting

### Photos not being deleted
```bash
# Check logs
tail -f logs/attendance_system_*.log | grep -i "delete"

# Check sync status
sqlite3 data/attendance.db "SELECT synced, COUNT(*) FROM attendance GROUP BY synced;"

# If most are synced=0, run manual sync
python scripts/sync_to_cloud.py
```

### Photos stuck in queue
```bash
# Check queue size
sqlite3 data/attendance.db "SELECT COUNT(*) FROM sync_queue;"

# Check retry counts
sqlite3 data/attendance.db "SELECT id, retry_count, error_message FROM sync_queue;"

# Manually retry
python scripts/sync_to_cloud.py
```

### High disk usage
```bash
# Check photo count
ls photos/*.jpg | wc -l

# Check unsynced records
sqlite3 data/attendance.db "SELECT COUNT(*) FROM attendance WHERE synced=0;"

# Manual cleanup
python scripts/auto_cleanup.py
```

---

## Testing Checklist

- [ ] Online sync: Photos deleted after 2-3 seconds
- [ ] Offline mode: Photos kept, system returns to standby <1s
- [ ] Queue processing: Photos deleted after sync (check logs)
- [ ] Manual sync: `sync_to_cloud.py` shows cleanup status
- [ ] Logs: Shows ✓ CLOUD and deleted photo message
- [ ] Database: `synced=1` and `cloud_record_id` set after sync
- [ ] Disk: Photos directory empty after all synced

---

## Files to Review

1. **FLOW_DIAGRAM.md** - Detailed flow visualization with 5 phases
2. **IMPLEMENTATION_NOTES.md** - Technical implementation details
3. **src/cloud/cloud_sync.py** - Photo deletion logic
4. **src/database/sync_queue.py** - Queue management
5. **attendance_system.py** - Enhanced upload_to_database with phases

---

## Summary

✅ **Local-first**: Data always saved locally  
✅ **Smart sync**: Online = immediate, offline = queue  
✅ **Auto-cleanup**: Deletes photos after confirmed sync  
✅ **Resilient**: Keeps photos for retry, max 3 attempts  
✅ **Documented**: Comprehensive logging + clear phases  

**No configuration needed - works out of the box!**
