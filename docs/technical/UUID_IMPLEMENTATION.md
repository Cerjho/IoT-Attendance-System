# UUID Implementation - Attendance Links

## Summary

**Changed:** Attendance SMS links now use student **UUID** instead of **student_number**.

### Before:
```
https://...view-attendance.html?student_id=2021001&sig=...
                                          ^^^^^^^^ student_number (QR code)
```

### After:
```
https://...view-attendance.html?student_id=3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4&sig=...
                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ UUID
```

---

## Why This Change?

### Security Benefits:
1. **Harder to Enumerate**: UUIDs are random, student_numbers are sequential (2021001, 2021002, etc.)
2. **Aligns with Supabase Schema**: `students.id` is UUID primary key
3. **Better Privacy**: Parents see UUID (meaningless to others) vs student_number (school ID)

### Technical Benefits:
1. **Consistent with Database**: Supabase uses UUID as primary key
2. **Future-Proof**: Supports student ID changes (transfer, re-enrollment)
3. **Cleaner Architecture**: student_number for QR only, UUID for everything else

---

## Architecture

### Data Flow:

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   Supabase  │────▶│ Roster Sync  │────▶│ Local Cache    │
│  students   │     │              │     │ (SQLite)       │
│             │     │              │     │                │
│ id (UUID)   │     │ Download     │     │ student_id     │
│ student_num │     │ Daily        │     │ uuid ◄─ NEW!   │
│ name        │     │              │     │ name           │
│ parent_ph   │     │              │     │ parent_phone   │
└─────────────┘     └──────────────┘     └────────────────┘
                                                   │
                                                   ▼
                                          ┌────────────────┐
                                          │ SMS Notifier   │
                                          │                │
                                          │ Uses UUID for  │
                                          │ link generation│
                                          └────────────────┘
```

### Storage:

| Location | Field | Example | Purpose |
|----------|-------|---------|---------|
| **Supabase** | `id` | `3c2c6e8f-...` | Primary key |
| | `student_number` | `2021001` | For QR codes |
| **Local Cache** | `student_id` | `2021001` | QR lookup (indexed) |
| | `uuid` | `3c2c6e8f-...` | For SMS links |

---

## Migration Guide

### 1. Database Migration (REQUIRED)

```bash
# Add uuid column to students table
python3 scripts/migrate_add_uuid.py
```

**Output:**
```
🔧 Adding uuid column to students table...
✅ Migration complete! UUID column added to students table
```

### 2. Roster Sync (REQUIRED)

```bash
# Populate UUIDs from Supabase
python3 -c "
from src.sync.roster_sync import RosterSyncManager
from src.utils.config_loader import load_config
config = load_config()
roster = RosterSyncManager(config.get('cloud', {}))
result = roster.download_today_roster(force=True)
print(result)
"
```

**Expected Output:**
```json
{
  "success": true,
  "students_synced": 45,
  "message": "Roster synced successfully",
  "cached_count": 45
}
```

### 3. Verify UUIDs Cached

```bash
# Check if UUIDs are populated
sqlite3 data/attendance.db "SELECT student_id, substr(uuid, 1, 20) || '...' as uuid FROM students LIMIT 5;"
```

**Expected:**
```
2021001|3c2c6e8f-7d3e-4f7a...
2021002|5f2a3d1c-8b4e-4c9a...
2021003|7d4b5e2f-9c6a-4d8b...
```

---

## Code Changes

### 1. SMS Notifier Signature

**Before:**
```python
def send_attendance_notification(
    self,
    student_id: str,        # student_number
    student_name: Optional[str],
    parent_phone: str,
    ...
) -> bool:
```

**After:**
```python
def send_attendance_notification(
    self,
    student_id: str,            # student_number (QR code)
    student_name: Optional[str],
    parent_phone: str,
    ...
    student_uuid: Optional[str] = None,  # NEW: UUID for links
) -> bool:
```

### 2. Link Generation

**Before:**
```python
# Used student_number directly
attendance_link = self._generate_attendance_link(student_id)
```

**After:**
```python
# Use UUID if available, fallback to student_number
link_identifier = student_uuid if student_uuid else student_id
attendance_link = self._generate_attendance_link(link_identifier)
```

### 3. Main System Integration

**Before:**
```python
sms_sent = self.sms_notifier.send_attendance_notification(
    student_id=student_id,
    student_name=student_data.get("name"),
    parent_phone=student_data.get("parent_phone"),
    ...
)
```

**After:**
```python
# Get UUID from cached data
student_uuid = student_data.get("uuid")

sms_sent = self.sms_notifier.send_attendance_notification(
    student_id=student_id,
    student_name=student_data.get("name"),
    parent_phone=student_data.get("parent_phone"),
    ...
    student_uuid=student_uuid,  # Pass UUID for link
)
```

---

## Backward Compatibility

### ✅ Graceful Fallback

The system **automatically falls back** to student_number if UUID not available:

```python
# In _generate_attendance_link()
link_identifier = student_uuid if student_uuid else student_id
```

### When Fallback Occurs:

1. **No roster sync run yet** - UUIDs not populated
2. **Offline system** - Never synced with Supabase
3. **Manual SMS** - UUID not provided

### Migration Path:

| State | UUID Available? | Link Uses | Notes |
|-------|----------------|-----------|-------|
| **Before migration** | ❌ No | student_number | Old behavior |
| **After migration, before sync** | ❌ No | student_number | Fallback mode |
| **After roster sync** | ✅ Yes | UUID | Desired state |

---

## Testing

### Test 1: Generate UUID Link

```bash
# Generate link with UUID
python3 scripts/generate_sample_link.py "3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4"
```

**Expected:**
```
🔗 Full URL:
https://...view-attendance.html?student_id=3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4&sig=...
```

### Test 2: Verify Signature

```bash
# Signature should be different for UUID vs student_number
python3 scripts/generate_sample_link.py "2021001"  # Old way
python3 scripts/generate_sample_link.py "3c2c6e8f-..."  # New way
```

**Result:** Different signatures (proves enumeration protection)

### Test 3: Check SMS Integration

```python
from src.notifications.sms_notifier import SMSNotifier
from src.utils.config_loader import load_config

config = load_config()
sms = SMSNotifier(config.get('sms_notifications', {}))

# Test with UUID
link_with_uuid = sms._generate_attendance_link("3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4")
print("UUID Link:", link_with_uuid)

# Test fallback
link_fallback = sms._generate_attendance_link("2021001")
print("Fallback Link:", link_fallback)
```

---

## Security Impact

### ✅ Improved:

1. **Enumeration Resistance**: Can't guess next student (UUID random vs sequential)
2. **Privacy**: UUID meaningless to outsiders vs student_number (school ID)
3. **Signature Uniqueness**: Each UUID gets unique signature

### Example Attack Prevention:

**Before (student_number):**
```
Attacker knows: student_id=2021001
Attacker tries: student_id=2021002, 2021003, 2021004...
                (sequential, easy to enumerate)
```

**After (UUID):**
```
Attacker knows: student_id=3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4
Attacker tries: student_id=3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a5
                (signature invalid - different UUID)
                
Trying random UUIDs: 1 in 5.3 × 10^36 chance (impossible)
```

---

## Troubleshooting

### Issue: SMS links still use student_number

**Solution:**
```bash
# 1. Check if UUIDs populated
sqlite3 data/attendance.db "SELECT COUNT(*) FROM students WHERE uuid IS NOT NULL;"

# 2. If zero, run roster sync
python3 scripts/migrate_add_uuid.py  # If not done yet
# Then sync roster (see Migration Guide step 2)

# 3. Restart services
sudo systemctl restart attendance-{dashboard,system}
```

### Issue: Roster sync fails

**Check:**
```bash
# 1. Verify Supabase credentials
grep -E "(SUPABASE_URL|SUPABASE_KEY)" .env

# 2. Check network connectivity
curl -s "${SUPABASE_URL}/rest/v1/students?limit=1" \
  -H "apikey: ${SUPABASE_KEY}" | jq .

# 3. Check logs
sudo journalctl -u attendance-system | grep "roster sync"
```

### Issue: UUIDs empty after sync

**Cause:** Supabase `students` table might not have `id` field returned

**Fix:**
```python
# Check Supabase query includes 'id'
response = requests.get(
    f"{url}/rest/v1/students",
    params={"select": "id,student_number,first_name,last_name,parent_guardian_contact"}
)
```

---

## Deployment Checklist

- [x] Run database migration
- [x] Sync roster to populate UUIDs
- [x] Restart services
- [x] Test UUID link generation
- [x] Verify SMS uses UUID
- [x] Check fallback behavior (no UUID)
- [x] Monitor logs for errors
- [x] Update documentation

---

## Files Changed

| File | Change | Purpose |
|------|--------|---------|
| `src/database/db_handler.py` | Added `uuid` column | Store UUID locally |
| `src/sync/roster_sync.py` | Cache UUID from Supabase | Populate UUIDs |
| `src/notifications/sms_notifier.py` | Added `student_uuid` param | Use UUID for links |
| `attendance_system.py` | Pass UUID to SMS | Integration |
| `scripts/migrate_add_uuid.py` | Migration script | Add column |

---

## FAQ

**Q: Do old links still work?**  
A: Yes, if they haven't expired. New links use UUID.

**Q: What if roster sync never runs?**  
A: System falls back to student_number (old behavior).

**Q: Can I force UUID in config?**  
A: No, UUID must come from Supabase via roster sync.

**Q: What about offline systems?**  
A: Use student_number fallback. UUID caching requires initial online sync.

**Q: Does this break existing SMS templates?**  
A: No, templates use `{attendance_link}` placeholder which works with both.

---

**Status:** ✅ Implemented  
**Version:** 1.0  
**Date:** 30 November 2025
