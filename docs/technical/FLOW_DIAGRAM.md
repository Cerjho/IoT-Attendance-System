# IoT Attendance System - Updated Persistence Flow

## Overview

The system now implements a **local-first, cloud-sync, auto-cleanup** flow that ensures zero data loss while optimizing storage and network efficiency.

```
CAPTURE → LOCAL PERSIST → CLOUD SYNC → CLEANUP
```

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│          ATTENDANCE CAPTURE & PERSISTENCE FLOW (UPDATED)             │
└─────────────────────────────────────────────────────────────────────┘

PHASE 1: STANDBY & CAPTURE
═══════════════════════════

    ┌─────────────────┐
    │ QR Code Scanned │ (instant)
    │ Student ID read │
    └────────┬────────┘
             │
             ↓
    ┌──────────────────────┐
    │ Face Detection Window │ (5 seconds)
    │ (capture best frame) │
    └────────┬─────────────┘
             │
             ↓
    ┌──────────────────────────┐
    │ Capture Photo to Disk     │
    │ photos/*.jpg (BLOCKING)  │
    │ Quality: 95% JPEG        │
    │ Size: ~100-500KB         │
    └────────┬─────────────────┘
             │
             ✓ PHOTO PERSISTED TO DISK


PHASE 2: LOCAL PERSISTENCE (Guaranteed)
════════════════════════════════════════

    ┌──────────────────────────────┐
    │ Record Attendance Locally     │
    │ (SQLite Database)            │
    │ data/attendance.db           │
    │                              │
    │ Fields:                      │
    │ ├─ id (auto-increment)       │
    │ ├─ student_id               │
    │ ├─ timestamp                │
    │ ├─ photo_path               │
    │ ├─ qr_data                  │
    │ ├─ status: 'present'        │
    │ ├─ synced: 0 (NOT synced)   │
    │ └─ [empty sync fields]      │
    └────────┬─────────────────────┘
             │
             ✓ LOCAL RECORD CREATED


PHASE 3: CLOUD SYNC ATTEMPT
════════════════════════════

    ┌─────────────────────┐
    │ Check Connectivity  │
    │ is_online()?        │
    └────┬──────────┬─────┘
         │          │
         │ONLINE    │OFFLINE
         │          │
    ┌────▼──────┐   │
    │ Attempt   │   │
    │ Cloud Sync│   │
    └─┬──┬──────┘   │
      │  │          │
      │  └──────────┴─────────────────┐
      │                               │
      │ SUCCESS                    OFFLINE/FAIL
      │                               │
    ┌─▼──────────────────┐  ┌────────▼──────────┐
    │ Upload Photo to    │  │ Add to sync_queue │
    │ Supabase Storage   │  │                   │
    │                    │  │ Queue Entry:      │
    │ (REST API POST)    │  │ ├─ record_id      │
    │ Timeout: 30s       │  │ ├─ photo_path     │
    │ Returns: photo_url │  │ ├─ retry_count:0  │
    └────┬───────────────┘  │ └─ data (full)    │
         │                  │                   │
         │ photo_url        └────────┬──────────┘
         │                           │
    ┌────▼──────────────────┐        │
    │ Insert Attendance to  │        │
    │ Supabase DB           │        │
    │                       │        │
    │ (REST API POST)       │        │
    │ Fields: student_id,   │        │
    │         timestamp,    │        │
    │         photo_url,    │        │
    │         qr_data,      │        │
    │         device_id     │        │
    │ Timeout: 10s          │        │
    │ Returns: cloud_id     │        │
    └────┬──────────────────┘        │
         │                           │
    ┌────▼──────────────────────┐    │
    │ Mark As Synced (Local DB) │    │
    │                           │    │
    │ UPDATE attendance:        │    │
    │ ├─ synced = 1             │    │
    │ ├─ sync_timestamp = now() │    │
    │ └─ cloud_record_id = uuid │    │
    └────┬──────────────────────┘    │
         │                           │
         │                           │
         │ SYNCED ✓             QUEUED ⟳
         │                           │
         ▼                           ▼


PHASE 4: PHOTO CLEANUP (IMMEDIATE or DELAYED)
══════════════════════════════════════════════

    ┌──────────────────────────────────┐
    │ ONLINE & SYNCED (Immediate)      │
    │                                  │
    │ Delete local photo:              │
    │ os.remove(photo_path)            │
    │                                  │
    │ ✓ Photos freed from disk         │
    │ ✓ Cloud storage is permanent     │
    └──────────────────────────────────┘

    ┌──────────────────────────────────┐
    │ OFFLINE & QUEUED (Delayed)       │
    │                                  │
    │ Keep local photo:                │
    │ ├─ Wait for connection           │
    │ ├─ Background sync processes it  │
    │ ├─ Cloud sync succeeds           │
    │ └─ Then delete photo             │
    │                                  │
    │ ⟳ Photos kept until sync OK      │
    └──────────────────────────────────┘


PHASE 5: BACKGROUND SYNC (Queued Records)
═══════════════════════════════════════════

    Every 60 seconds (sync_interval):
    
    ┌─────────────────┐
    │ Check Online?   │
    └────┬────────┬───┘
         │        │
         │OFFLINE │ONLINE
         │        │
      SKIP   ┌────▼──────────────┐
            │ Get pending        │
            │ records (max 10)   │
            │ from sync_queue    │
            └────┬───────────────┘
                 │
            ┌────▼──────────────────────┐
            │ For each record:          │
            │                           │
            │ ├─ Check retry_count < 3  │
            │ │                         │
            │ ├─ If >= 3: Remove & skip │
            │ │                         │
            │ ├─ Else: Try sync         │
            │ │ ├─ Upload photo (disk)  │
            │ │ ├─ Insert to Supabase   │
            │ │ └─ Mark synced          │
            │ │                         │
            │ ├─ If success:            │
            │ │ ├─ Delete photo         │
            │ │ └─ Remove from queue    │
            │ │                         │
            │ └─ If fail:               │
            │   └─ Increment retry      │
            │      (keep photo)         │
            │                           │
            └────┬──────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
      Success         Failure
         │                │
    ┌────▼────┐      ┌────▼─────────┐
    │Delete    │      │Retry later   │
    │photo     │      │(max 3x)      │
    │Queue OK  │      │Queue kept    │
    └──────────┘      │Photo kept    │
                      └──────────────┘


SUMMARY TABLE
═════════════

Phase | Component | Action | Status | Photo | Cloud DB | Local DB
──────┼───────────┼────────┼────────┼───────┼──────────┼──────────
  1   | Camera    | Capture| ✓      | ✓     | ✗        | ✗
  2   | Database  | Record | ✓      | ✓     | ✗        | ✓ (synced=0)
  3a  | Cloud     | Sync   | ✓      | ✓     | ✓        | ✓ (synced=1)
  3b  | Queue     | Queue  | ⟳      | ✓     | ✗        | ✓ (synced=0)
  4a  | Cleanup   | Delete | ✓      | ✗     | ✓        | ✓ (synced=1)
  4b  | Queue     | Kept   | ⟳      | ✓     | ✗        | ✓ (synced=0)
  5   | Queue     | Retry  | ⟳      | ✓     | ✗        | ✓ (synced=0)
  5   | Queue     | Sync   | ✓      | ✓     | ✓        | ✓ (synced=1)
  5   | Cleanup   | Delete | ✓      | ✗     | ✓        | ✓ (synced=1)
```

---

## Key Features

### ✅ Local-First Persistence
- Photo saved to disk immediately after face capture
- Attendance record created in local database before any cloud operations
- **Guarantees local data survival** even if cloud sync fails or is disabled
- User sees instant confirmation (success beep + message)

### ☁️ Smart Cloud Sync
- **Online**: Immediate sync after local recording
  - Upload photo to Supabase Storage
  - Insert record to Supabase DB
  - Mark as synced
  - Delete local photo
  - Takes ~1-5 seconds depending on network

- **Offline**: Automatic queuing
  - Record saved locally
  - Queued for later sync
  - Local photo kept for retry
  - No user-visible delay

### 🔄 Automatic Cleanup
- Photos deleted **immediately** after successful cloud sync
- Photos retained for **queued records** until cloud sync succeeds
- Failed sync attempts **preserve photos** for retry (max 3 retries)
- Background thread processes queue every 60 seconds
- **Zero data loss**: Always tries 3 times before giving up

### 📱 Offline Mode Resilience
- Works fully offline: QR scan + face detection + photo capture + local recording
- SMS notifications queued (optional, depends on SMS API)
- Automatic sync when connection returns
- No user intervention needed

---

## Data Flow Examples

### Scenario 1: Online with Immediate Sync
```
0ms     │ QR Scan
        │ ↓
100ms   │ Face Detected
        │ ↓
500ms   │ Photo Saved: photos/attendance_2021001_20251124_150530.jpg
        │ ↓
550ms   │ LOCAL DB INSERT: attendance record (synced=0, id=42)
        │ ↓
600ms   │ Cloud Online Check: YES
        │ ↓
1000ms  │ Photo Uploaded to Supabase Storage
        │ ↓
2000ms  │ Attendance Inserted to Supabase DB
        │ ↓
2100ms  │ Mark Synced (synced=1, cloud_record_id=uuid)
        │ ↓
2150ms  │ DELETE photos/attendance_2021001_20251124_150530.jpg ✓
        │ ↓
2200ms  │ Return to STANDBY
        │
Total Time: ~2.2 seconds
Result: Photo deleted, data synced to cloud
```

### Scenario 2: Offline with Auto-Sync Later
```
0ms     │ QR Scan
        │ ↓
100ms   │ Face Detected
        │ ↓
500ms   │ Photo Saved: photos/attendance_2021002_20251124_150530.jpg
        │ ↓
550ms   │ LOCAL DB INSERT: attendance record (synced=0, id=43)
        │ ↓
600ms   │ Cloud Online Check: NO (offline)
        │ ↓
610ms   │ Add to sync_queue (record_id=43, photo_path=..., retry_count=0)
        │ ↓
620ms   │ Return to STANDBY (photo kept locally)
        │
Total Time: ~0.6 seconds (much faster!)
Result: Data saved locally, queued for later

[User reconnects to internet in next 30 minutes...]

T+5min  │ Background sync runs (every 60 seconds, periodic check)
        │ ↓
        │ Online Check: YES ✓
        │ ↓
        │ Get pending records: 1 found (id=43)
        │ ↓
        │ Upload photos/attendance_2021002_20251124_150530.jpg
        │ ↓
        │ Insert to Supabase DB
        │ ↓
        │ Mark Synced (sync_timestamp, cloud_record_id)
        │ ↓
        │ DELETE photos/attendance_2021002_20251124_150530.jpg ✓
        │ ↓
        │ Remove from sync_queue
        │
Result: Eventually synced, photo cleaned up
```

### Scenario 3: Network Failure with Retry
```
0ms     │ QR Scan
500ms   │ Photo Saved
550ms   │ LOCAL DB: attendance record (synced=0, id=44)
600ms   │ Cloud Check: Online
610ms   │ Try Photo Upload: TIMEOUT ❌
620ms   │ Add to sync_queue (record_id=44, retry_count=0)
630ms   │ Return to STANDBY (photo kept)
        │
T+60s   │ Background sync: Try retry 1
        │ Photo Upload: SUCCESS ✓
        │ Cloud Insert: SUCCESS ✓
        │ Mark Synced
        │ DELETE photo ✓
        │
Result: After 60s, auto-synced and cleaned up
```

---

## Flow Guarantees

| Requirement | Guaranteed | How |
|-------------|-----------|-----|
| No data loss | ✅ | Local DB always created first |
| No duplicate uploads | ✅ | synced flag prevents re-upload |
| Photos cleaned after sync | ✅ | Automatic on sync success |
| Photos kept if pending | ✅ | Only deleted after cloud confirms |
| Works offline | ✅ | Queue mechanism with retries |
| Auto-cleanup on recovery | ✅ | Background sync processes queue |
| Manual sync available | ✅ | `python scripts/sync_to_cloud.py` |

---

## Configuration

Key settings in `config/config.json`:

```json
{
  "cloud": {
    "enabled": true,                    // Enable cloud sync
    "sync_on_capture": true,            // Try immediate sync after capture
    "sync_interval": 60,                // Background sync every 60s
    "retry_attempts": 3,                // Max retries for queued records
    "retry_delay": 30                   // Wait 30s between retries
  },
  "offline_mode": {
    "enabled": true,                    // Enable offline queue
    "auto_sync_when_online": true,      // Resume queue when online
    "check_connection_interval": 30     // Check connectivity every 30s
  }
}
```

---

## Monitoring & Debugging

### Check Sync Status
```bash
python scripts/sync_to_cloud.py
```

Output shows:
- Cloud Sync: Enabled/Disabled
- Online: Yes/No
- Unsynced Records: count
- Queue Size: count

### Check Local Photos
```bash
ls -lah photos/
du -sh photos/
```

### Check Queued Records
```bash
sqlite3 data/attendance.db
> SELECT * FROM sync_queue;
> SELECT COUNT(*) FROM attendance WHERE synced=0;
```

### View Logs
```bash
tail -f logs/attendance_system_*.log | grep -E "(synced|queue|photo|cleanup)"
```

### Monitor Background Sync
```bash
watch -n 5 'sqlite3 data/attendance.db "SELECT synced, COUNT(*) FROM attendance GROUP BY synced; SELECT COUNT(*) FROM sync_queue;"'
```

---

## Performance Impact

| Operation | Duration | Blocking |
|-----------|----------|----------|
| Photo capture | 700ms | YES (high-res still mode) |
| Photo save to disk | 50-200ms | YES |
| Local DB insert | 20-50ms | YES |
| **Online sync total** | 1-5s | YES |
| **Offline queue add** | 10-20ms | NO (returns immediately) |
| Background queue processing | variable | NO (separate thread) |
| Photo deletion | <10ms | YES |

**User-facing delay:**
- **Online**: ~2-5 seconds (unavoidable - network)
- **Offline**: ~0.6 seconds (fast - local only)

---

## Recovery & Manual Operations

### Manual Force Sync
```bash
python scripts/sync_to_cloud.py
```
Syncs all unsynced records immediately.

### Cleanup Local Data (After Sync)
```bash
./scripts/cleanup_locally.sh
# Or
python scripts/auto_cleanup.py
```

### Check What Will Be Deleted
```bash
# Count synced records
sqlite3 data/attendance.db "SELECT COUNT(*) FROM attendance WHERE synced=1;"

# List photo files
ls photos/attendance_*.jpg | wc -l

# List old exports
ls data/attendance_export_*.json | wc -l
```

### Restore From Backup
```bash
# Restore database
cp data/attendance.db.backup_TIMESTAMP data/attendance.db

# Restore from JSON export
python -c "from src.database.db_handler import AttendanceDatabase; AttendanceDatabase('data/attendance.db').import_from_json('data/attendance_export_*.json')"
```

---

## Summary

The updated flow implements a **resilient, offline-capable, storage-efficient system** that:

1. ✓ **Always saves locally first** (guarantees no data loss)
2. ✓ **Attempts cloud sync immediately** (if online)
3. ✓ **Queues for retry** (if offline or fails)
4. ✓ **Deletes photos after sync** (saves storage)
5. ✓ **Keeps photos until confirmed** (resilient retry)
6. ✓ **Auto-syncs when online** (transparent to user)
7. ✓ **Supports manual sync** (on-demand catch-up)

No configuration needed - works out of the box with smart defaults!
