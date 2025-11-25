# Automated Local Data Cleanup Guide

## Overview

The automated cleanup system safely removes local attendance records, photos, and old exports **after** verifying all data has been successfully synced to Supabase cloud. This prevents data loss while freeing disk space on your IoT device.

## Quick Start

### Option 1: Using the Bash Wrapper (Recommended)

```bash
cd /home/iot/attendance-system
./scripts/cleanup_locally.sh
```

### Option 2: Using Python Directly

```bash
cd /home/iot/attendance-system
source venv/bin/activate
python3 scripts/auto_cleanup.py
```

## What Gets Cleaned Up

| Item | Location | Action | Why |
|------|----------|--------|-----|
| **Attendance Records** | `data/attendance.db` | Deleted from database | Free database space |
| **Local Photos** | `photos/` | Removed from device | Cloud has permanent copies |
| **Old Exports** | `data/attendance_export_*.json` | Keep 5 newest, delete rest | Archive old backups |
| **Sync Queue Failures** | `data/attendance.db` | Remove entries with 3+ retries | Clean up permanently failed syncs |

### What's NOT Deleted

- ✅ Student records in database (kept for reference)
- ✅ Most recent database backup (`attendance.db.backup_*`)
- ✅ Recent JSON exports (keeps 5 most recent)
- ✅ Cloud data in Supabase (safe forever)

## Safety Checks (Before Cleanup Runs)

The script automatically verifies:

1. **Cloud sync is enabled** in `config/config.json`
2. **Device has internet connection**
3. **All attendance records are synced** (no unsynced records)
4. **Sync queue is empty** (all retry attempts finished)
5. **User confirms the action** (requires typing 'YES')

If any check fails, cleanup is aborted and you're shown the issue.

## Step-by-Step Process

```
1. VERIFY SYNC STATUS
   └─ Check cloud enabled + online + all records synced

2. CREATE DATABASE BACKUP
   └─ Copies attendance.db to attendance.db.backup_TIMESTAMP

3. EXPORT JSON BACKUP
   └─ Creates data/attendance_export_TIMESTAMP.json

4. CLEAR ATTENDANCE RECORDS
   └─ Deletes all rows from attendance table
   └─ Generates before/after count report

5. REMOVE LOCAL PHOTOS
   └─ Deletes all photos/attendance_*.jpg files
   └─ Cloud storage has permanent copies

6. CLEAN OLD EXPORTS
   └─ Keeps 5 most recent JSON exports
   └─ Deletes older ones to save space

7. CLEAN SYNC QUEUE
   └─ Removes permanently failed sync entries
   └─ Clears retry queue
```

## Example Output

```
======================================================================
                 AUTOMATED CLEANUP - LOCAL ATTENDANCE DATA
======================================================================

This script will:
  1. Verify all data is synced to Supabase
  2. Create database backup
  3. Export JSON backup
  4. Clear attendance records
  5. Remove local photos
  6. Clean old exports
  7. Clean sync queue

⚠️  Proceed with cleanup? Type 'YES' to confirm: YES

📍 Verifying sync status...
  - Cloud Sync: ✅ Enabled
  - Online: ✅ Yes
  - Unsynced Records: 0
  - Queue Size: 0
✅ Sync status verified successfully

📍 Creating database backup...
✅ Database backed up to: data/attendance.db.backup_20251124_111530 (245.3 KB)

📍 Exporting JSON backup...
✅ JSON backup saved to: data/attendance_export_20251124_111530.json (156.8 KB)

📍 Clearing attendance records from database...
  Before: 287 total (287 synced, 0 unsynced)
  After:  0 total
✅ Deleted 287 attendance records

📍 Clearing local photos...
✅ Deleted 8 photo files

📍 Cleaning old JSON exports (keeping 5 most recent)...
✅ Deleted 23 old exports, freed 3.4 MB

📍 Cleaning sync queue (removing max retry failures)...
✅ Cleaned 0 failed queue entries

======================================================================
                           CLEANUP SUMMARY
======================================================================

✅ COMPLETED ACTIONS:

  Attendance Cleared:
    • records_deleted: 287
    • before: 287
    • after: 0

  Photos Cleared:
    • photos_deleted: 8
    • total_files: 8

  Exports Cleaned:
    • exports_deleted: 23
    • exports_remaining: 5
    • space_freed_mb: 3.4

  Queue Cleaned:
    • entries_deleted: 0
    • entries_remaining: 0

⏱️  Completed in 2.3 seconds

Report saved to: data/cleanup_report_20251124_111530.json

✅ All cleanup tasks completed successfully!
```

## Cleanup Reports

After cleanup completes, a detailed JSON report is saved to:

```
data/cleanup_report_YYYYMMDD_HHMMSS.json
```

View the latest report:

```bash
cat data/cleanup_report_*.json | tail -1 | python3 -m json.tool
```

Reports include:
- Timestamp of cleanup
- All verification checks
- Actions taken and items deleted
- Any warnings or errors
- Time elapsed

## Scheduling Automatic Cleanup

To run cleanup automatically (e.g., daily), add to crontab:

```bash
# Run cleanup every night at 2 AM
0 2 * * * /home/iot/attendance-system/scripts/cleanup_locally.sh >> /var/log/attendance_cleanup.log 2>&1
```

**Note**: This requires the cleanup to skip the user confirmation prompt. Modify the script or use:

```bash
# Run with automatic confirmation (no user prompt)
echo "YES" | python3 scripts/auto_cleanup.py
```

## Troubleshooting

### ❌ "Cloud sync is disabled"
**Solution**: Enable cloud sync in `config/config.json`:
```json
{
  "cloud": {
    "enabled": true
  }
}
```

### ❌ "No internet connection detected"
**Solution**: Check your network:
```bash
ping -c 1 8.8.8.8
curl -I https://ufckpgswkziojwoqosxw.supabase.co
```

### ❌ "{N} records still unsynced"
**Solution**: Run manual sync before cleanup:
```bash
python3 scripts/sync_to_cloud.py
```

Wait for all records to show as synced, then retry cleanup.

### ❌ "Sync queue not empty"
**Solution**: Wait 1-2 minutes for background sync to complete:
```bash
# Watch sync progress
watch -n 1 'python3 -c "from attendance_system import IoTAttendanceSystem; s = IoTAttendanceSystem(); st = s.cloud_sync.get_sync_status(); print(f\"Queue: {st[\"queue_size\"]}, Unsynced: {st[\"unsynced_records\"]}\")"'
```

### ✅ Cleanup succeeded but photos still exist
**Normal behavior**: Delete manually if needed:
```bash
rm -f photos/attendance_*.jpg
```

### ✅ Want to recover deleted records
The backups are in:
```bash
ls -la data/attendance.db.backup_*        # Database backup
ls -la data/attendance_export_*.json      # JSON exports
```

Restore from backup:
```bash
cp data/attendance.db.backup_TIMESTAMP data/attendance.db
```

## Best Practices

1. **Run sync before cleanup**: Always verify all records are synced
   ```bash
   python3 scripts/sync_to_cloud.py  # Ensure unsynced_records = 0
   ```

2. **Keep backups**: Backups are automatically created but keep older ones:
   ```bash
   ls -la data/attendance.db.backup_*
   ```

3. **Monitor disk space**: Check space freed
   ```bash
   df -h
   du -sh data/ photos/
   ```

4. **Review cleanup reports**: Check the JSON report after each cleanup
   ```bash
   cat data/cleanup_report_*.json | python3 -m json.tool
   ```

5. **Schedule regularly**: Run cleanup weekly to maintain performance
   ```bash
   # Every Sunday at 2 AM
   0 2 * * 0 /home/iot/attendance-system/scripts/cleanup_locally.sh
   ```

## Disk Space Estimate

After cleanup, you can expect to free:

```
Photos: ~10-50 MB (depends on number of students)
Exports: ~2-10 MB (old JSON files)
Database: ~5-20 MB (cleared attendance records)
───────────────────────────────
Total: ~20-80 MB per cleanup cycle
```

Monthly savings: ~80-320 MB for daily cleanup

## System Recovery

If something goes wrong, restore from backups:

```bash
# Restore database from latest backup
cp data/attendance.db.backup_$(ls -t data/attendance.db.backup_* | head -1 | sed 's/.*backup_//') data/attendance.db

# Verify restoration
python3 -c "from src.database.db_handler import AttendanceDatabase; db = AttendanceDatabase('data/attendance.db'); print(f'Attendance records: {len(db.get_all_attendance())}')"
```

## Additional Commands

```bash
# Show current disk usage
du -sh data/ photos/ | sort -h

# Count current attendance records
python3 -c "import sqlite3; c = sqlite3.connect('data/attendance.db'); cur = c.cursor(); cur.execute('SELECT COUNT(*) FROM attendance'); print(f'Records: {cur.fetchone()[0]}')"

# Monitor cleanup in progress
tail -f logs/attendance_system_*.log | grep -i cleanup

# View all backups
ls -lrt data/attendance.db.backup_* data/attendance_export_*.json
```

## Questions?

For issues or questions about the cleanup process:

1. Check the cleanup report: `data/cleanup_report_*.json`
2. Review logs: `tail -f logs/attendance_system_*.log`
3. Check sync status: `python3 scripts/sync_to_cloud.py`
4. Verify config: `cat config/config.json | python3 -m json.tool`
