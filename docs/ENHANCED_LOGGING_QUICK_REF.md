# Enhanced Logging Quick Reference

## Quick View Commands

```bash
# Real-time log monitoring
journalctl -u attendance-system.service -f

# Last 100 entries
journalctl -u attendance-system.service -n 100

# Filter by operation type
journalctl -u attendance-system.service | grep '📱'  # SMS only
journalctl -u attendance-system.service | grep '☁️'  # Cloud only
journalctl -u attendance-system.service | grep '❌'  # Errors only
```

## Log Symbols

| Symbol | Meaning | Usage |
|--------|---------|-------|
| 📱 | SMS operation | Notification sending |
| ☁️ | Cloud operation | Sync to main server |
| ✅ | Success | Operation completed |
| ⚠️ | Warning | Retry or non-fatal error |
| ❌ | Error | Operation failed |
| 📥 | Queue add | Record queued for later |
| 📤 | Queue process | Processing queue |
| 📊 | Summary | Batch operation summary |

## Common Log Patterns

### SMS Send Success
```
📱 SMS Send Started: to=+639... msg_len=142
✅ SMS Sent Successfully: msg_id=abc123 attempt=1/3
```

### SMS Send Retry
```
📱 SMS Send Started: to=+639...
⚠️ SMS HTTP Error: status=500 attempt=1/3
📱 SMS Retry: attempt 2/3
✅ SMS Sent Successfully: attempt=2/3
```

### Cloud Sync Success
```
☁️ Cloud Sync Started: local_id=42 student=2021001
✅ Photo uploaded: https://...
✅ Attendance Persisted: cloud_id=789
✅ Cloud Sync Success: local_id=42
```

### Offline Queue
```
☁️ Cloud Sync Started: local_id=43
📥 Cloud Sync Queued (offline): local_id=43
```

### Queue Processing
```
📤 Processing sync queue: 5 pending records
✅ Queue sync success: queue_id=10 cloud_id=790
✅ Queue sync success: queue_id=11 cloud_id=791
📊 Sync queue complete: succeeded=5 failed=0
```

## Search Examples

### Find all SMS operations for a phone number
```bash
journalctl -u attendance-system.service | grep '📱.*+639123456789'
```

### Find all cloud syncs for a student
```bash
journalctl -u attendance-system.service | grep 'student=2021001'
```

### Count successful operations today
```bash
journalctl -u attendance-system.service --since today | grep -c '✅'
```

### Find failed SMS
```bash
journalctl -u attendance-system.service | grep '📱.*❌'
```

### Find queued records
```bash
journalctl -u attendance-system.service | grep '📥'
```

### Check sync rate
```bash
journalctl -u attendance-system.service --since "1 hour ago" | grep '📊'
```

## Troubleshooting

### SMS not sending?
```bash
# Check for SMS failures
journalctl -u attendance-system.service | grep '📱.*❌' | tail -20

# Common issues:
# - ⚠️ SMS Connection Error → API server down
# - ⚠️ SMS Timeout → Network slow
# - ⚠️ SMS HTTP Error: status=401 → Invalid credentials
```

### Cloud sync not working?
```bash
# Check for cloud failures
journalctl -u attendance-system.service | grep '☁️.*❌' | tail -20

# Common issues:
# - 📥 Queued (offline) → Network down
# - Student not found → Missing in Supabase
# - status=500 → Server error
```

### Check queue size
```bash
# Look for queue processing logs
journalctl -u attendance-system.service | grep '📤' | tail -5

# Shows: processed=X, succeeded=Y, failed=Z
```

## Performance Metrics

### Success Rate (last hour)
```bash
# Total operations
SUCCESS=$(journalctl -u attendance-system.service --since "1 hour ago" | grep -c '✅')
FAILED=$(journalctl -u attendance-system.service --since "1 hour ago" | grep -c '❌')
echo "Success: $SUCCESS, Failed: $FAILED"
```

### Average retry count
```bash
# Count retry attempts
journalctl -u attendance-system.service --since "1 hour ago" | grep '📱 SMS Retry'
```

### Queue backlog trend
```bash
# Check queue sizes over time
journalctl -u attendance-system.service --since today | grep '📤.*pending'
```

## Demo

Run example log formats:
```bash
python utils/demo_enhanced_logging.py
```

## Full Documentation

See `docs/technical/ENHANCED_LOGGING.md` for complete details.
