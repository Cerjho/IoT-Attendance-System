# SMS Template Testing Guide

## Overview
Comprehensive SMS testing script to test all 7 templates and new enhancements.

## Test Script
**File:** `tests/test_all_sms_templates.py`

## Features Tested
✅ **7 SMS Templates:**
1. Check-in notification (~65 chars)
2. Check-out notification (~65 chars) 
3. Late arrival alert (~75 chars)
4. No check-out alert (~70 chars)
5. Absence alert (~75 chars)
6. Weekly summary (~55 chars)
7. Monthly summary (~70 chars)

✅ **Smart Features:**
- Quiet hours detection (22:00-06:00)
- Cooldown mechanism (5-minute duplicate prevention)
- Unsubscribe text on summaries

## How to Run

### 1. Update Phone Number
Edit the test script and update the phone number on line 405:
```python
phone = '09123456789'  # Your phone number here
```

### 2. Run the Script
```bash
cd /home/iot/attendance-system
pytest -q tests/test_all_sms_templates.py
```

### 3. Select Test Option
When prompted, choose:
- **Option 1:** Test ALL templates (sends 10+ messages)
- **Option 2:** Test individual template (sends 1 message)
- **Option 3:** Test features only (sends 2 messages for cooldown test)
- **Option 4:** Update phone number
- **Option 5:** Exit

## Test Options Explained

### Option 1: Test ALL Templates
Sends all 7 template messages plus cooldown test:
- Check-in: "John Paolo Gonzales checked IN at 2:30 PM on December 05, 2024"
- Check-out: "John Paolo Gonzales checked OUT at 5:00 PM on December 05, 2024"
- Late arrival: "John Paolo Gonzales arrived LATE (15 min) at 8:15 AM"
- No checkout: "ALERT: John Paolo Gonzales has not checked OUT. Please verify..."
- Absence: "NOTICE: John Paolo Gonzales was marked ABSENT today..."
- Weekly summary: "Week summary for John Paolo Gonzales: 4P 1L 0A"
- Monthly summary: "Month summary for John Paolo Gonzales: 18P 2L 0A (95%)"
- Cooldown test: Sends 2 identical messages 10 seconds apart

**Press Enter between tests** to pace the messages.

### Option 2: Test Individual Template
Choose specific template to test (1-7).

### Option 3: Test Features Only
Tests quiet hours detection, unsubscribe text, and cooldown mechanism.

## Expected Results

### ✅ Successful Test
- SMS sent successfully (green checkmarks)
- Message appears on phone within 5-30 seconds
- Cooldown blocks second duplicate message
- Quiet hours warning if testing between 22:00-06:00
- Summary messages include "Reply STOP to unsubscribe."

### ❌ Common Issues
1. **SMS notifier not initialized**
   - Check `.env` has SMS_USERNAME, SMS_PASSWORD, SMS_DEVICE_ID
   
2. **Failed to send SMS**
   - Check SMS gateway credentials
   - Verify device_id is correct
   - Check internet connection
   - Ensure SMS gateway app is running on Android phone

3. **Message not received**
   - Check phone number format (09XXXXXXXXX)
   - Check SMS gateway app logs
   - Verify SMS gateway has internet connection

## Message Character Counts

All templates optimized for SMS cost efficiency:

| Template | Characters | Cost Savings |
|----------|-----------|--------------|
| Check-in | ~65 | 63% shorter |
| Check-out | ~65 | 63% shorter |
| Late arrival | ~75 | Similar |
| No checkout | ~70 | New feature |
| Absence | ~75 | New feature |
| Weekly summary | ~55 | New feature |
| Monthly summary | ~70 | New feature |

**Cost Impact:** ~63% reduction in SMS costs for check-in/check-out messages.

## Testing Checklist

Before testing:
- [ ] Update phone number in script (line 405)
- [ ] Check `.env` has SMS credentials
- [ ] Verify SMS gateway app is running
- [ ] Confirm internet connection on both devices

During testing:
- [ ] Test all 7 templates
- [ ] Verify message formatting
- [ ] Check character counts
- [ ] Confirm unsubscribe text on summaries
- [ ] Test cooldown mechanism
- [ ] Check quiet hours detection

After testing:
- [ ] Verify all messages received
- [ ] Check message content accuracy
- [ ] Confirm timestamps correct
- [ ] Review SMS gateway logs
- [ ] Document any issues

## Tips

1. **Test in stages** - Use Option 2 to test one template at a time first
2. **Check formatting** - Verify student name, time, date appear correctly
3. **Monitor gateway** - Watch SMS gateway app for delivery status
4. **Time your tests** - Test cooldown by sending same message twice
5. **Test quiet hours** - Try testing between 22:00-06:00 to see warning

## Troubleshooting

### Message not sending
```bash
# Check SMS gateway credentials
grep SMS .env

# Test SMS gateway API
curl -X POST https://api.sms-gate.app/3rdparty/v1/message \
  -H "Authorization: Basic BASE64_ENCODED_CREDENTIALS" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumbers": ["09123456789"], "message": "Test", "deviceId": "DEVICE_ID"}'
```

### Environment variables not loading
```bash
# Check .env file exists and has correct format
cat .env | grep SMS

# Verify no extra spaces or quotes
# Format should be: SMS_USERNAME=value (no quotes, no spaces)
```

### Wrong phone number format
```python
# Phone formats accepted:
09123456789  → +639123456789
639123456789 → +639123456789
+639123456789 → +639123456789
```

## Next Steps

After successful testing:
1. ✅ Update attendance_system.py to use new templates
2. ✅ Deploy updated config.json with new templates
3. ✅ Monitor SMS delivery in production
4. ✅ Track SMS cost savings
5. ✅ Collect parent feedback on new messages

## Support

If issues persist:
1. Check SMS gateway app logs on Android phone
2. Verify SMS gateway API status
3. Test with different phone number
4. Review .env credentials
5. Check internet connectivity on both devices

---
**Last Updated:** December 5, 2024
**Version:** 1.0.0
