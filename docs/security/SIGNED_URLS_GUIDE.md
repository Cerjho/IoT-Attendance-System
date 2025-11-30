# Signed URLs - Quick Setup Guide

## What Is This?

Signed URLs provide **medium-level security** for attendance view links sent via SMS. Each link contains a cryptographic signature (HMAC-SHA256) that expires after a configurable time (default 48 hours).

## Security Benefits

- ✅ **Time-limited access**: Links expire automatically
- ✅ **Tamper-proof**: Any modification invalidates the signature
- ✅ **No enumeration**: Can't guess other student URLs
- ✅ **Audit trail**: All verification attempts logged
- ✅ **No stored passwords**: Stateless verification

## Setup (5 Minutes)

### 1. Generate Signing Secret

```bash
python -c "import secrets; print(f'URL_SIGNING_SECRET={secrets.token_hex(32)}')"
```

### 2. Add to `.env` File

```bash
echo "URL_SIGNING_SECRET=your-64-char-hex-from-step-1" >> .env
```

### 3. Verify Configuration

Check `config/config.json`:
```json
{
  "sms_notifications": {
    "use_signed_urls": true,
    "signed_url_expiry_hours": 48
  }
}
```

### 4. Restart Services

```bash
sudo systemctl restart attendance-system
sudo systemctl restart attendance-dashboard
```

### 5. Test It

```bash
python tests/test_signed_urls.py
```

Expected output:
```
5/5 tests passed
🎉 All tests PASSED! Implementation ready for production.
```

## How It Works

### Before (Insecure)
```
SMS: View attendance: https://example.com/view?student_id=2021001
```
- ❌ Anyone with student_id can access
- ❌ Link never expires
- ❌ Can enumerate all students

### After (Secure)
```
SMS: View attendance: https://example.com/view?student_id=2021001&expires=1764595410&sig=c19abefc...
```
- ✅ Signature validates authenticity
- ✅ Expires after 48 hours
- ✅ Tampering invalidates signature

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `use_signed_urls` | `true` | Enable signed URL generation |
| `signed_url_expiry_hours` | `48` | Hours until link expires |
| `URL_SIGNING_SECRET` | *required* | 64-char hex secret (in .env) |

### Adjust Expiry Time

Edit `config/config.json`:
```json
{
  "sms_notifications": {
    "signed_url_expiry_hours": 24  // 1 day instead of 2
  }
}
```

### Disable Signing (Testing)

```json
{
  "sms_notifications": {
    "use_signed_urls": false  // Falls back to plain URLs
  }
}
```

## URL Structure

### Signed URL Parameters

| Parameter | Example | Description |
|-----------|---------|-------------|
| `student_id` | `2021001` | Student number |
| `expires` | `1764595410` | Unix timestamp |
| `sig` | `c19abefc...` | HMAC-SHA256 signature |

### Signature Calculation

```python
message = "expires=1764595410&student_id=2021001"
signature = HMAC-SHA256(message, URL_SIGNING_SECRET)
```

## Verification Flow

```
1. Parent receives SMS with signed URL
2. Parent clicks link → opens view-attendance.html
3. JavaScript extracts student_id, expires, sig from URL
4. Calls API: GET /api/verify-url?student_id=...&expires=...&sig=...
5. Server:
   - Reconstructs expected signature
   - Compares with provided signature (constant-time)
   - Checks expiry timestamp
6. If valid: Show attendance data
   If invalid: Display error message
```

## Troubleshooting

### "URL_SIGNING_SECRET not configured"

**Problem**: Secret not loaded from .env

**Solution**:
```bash
# Check .env file exists
cat .env | grep URL_SIGNING_SECRET

# Restart services to reload .env
sudo systemctl restart attendance-dashboard
```

### "Invalid signature"

**Problem**: URL was modified or secret changed

**Solution**:
- Don't manually edit URLs
- Request new link via QR scan
- If secret rotated, all old links are invalid

### "Link expired"

**Problem**: URL older than expiry time

**Solution**:
- Request new link by scanning QR code
- Increase `signed_url_expiry_hours` if needed

### API Endpoint Unreachable

**Problem**: Dashboard service not running or wrong IP

**Solution**:
```bash
# Check dashboard status
sudo systemctl status attendance-dashboard

# Verify IP in view-attendance.html matches Pi device
grep VERIFY_API public/view-attendance.html
# Should show: const VERIFY_API = 'http://192.168.1.22:8080/api/verify-url';
```

## Security Considerations

### What This Protects Against

✅ **URL enumeration**: Can't guess valid student_id values  
✅ **URL tampering**: Signature invalidates if modified  
✅ **Permanent links**: URLs expire automatically  
✅ **Unauthorized sharing**: Time-limited access  

### What This Doesn't Protect Against

❌ **SMS interception**: Link visible in plaintext SMS  
❌ **Device theft**: Valid link usable from any device  
❌ **Parent impersonation**: No phone number verification  

### Improving Security Further

**Option A: Shorter Expiry** (15 minutes)
```json
{"signed_url_expiry_hours": 0.25}
```

**Option B: One-time Links** (requires tracking)
- Store used signatures in database
- Reject second use of same signature

**Option C: Phone Number Verification**
- Include hashed phone number in signature
- Verify phone matches before showing data

**Option D: Full Authentication** (See Magic Links guide)
- Implement Supabase Auth with OTP
- JWT-based sessions
- Proper RLS policies

## Monitoring

### View Verification Attempts

Check dashboard logs:
```bash
tail -f data/logs/system.log | grep "verify-url"
```

### Successful Verification
```
INFO: Valid signed URL verified for student 2021001
```

### Failed Attempts
```
WARNING: Invalid signature for student 2021001
WARNING: URL expired at 2025-11-30 20:23:30 for student 2021001
```

## API Reference

### `/api/verify-url` Endpoint

**Method**: `GET`

**Parameters**:
- `student_id` (required): Student number
- `expires` (required): Unix timestamp
- `sig` (required): HMAC signature

**Response** (200 OK):
```json
{
  "valid": true,
  "student_id": "2021001",
  "student_uuid": "3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4",
  "expires_at": "2025-12-02T21:19:40"
}
```

**Response** (403 Forbidden):
```json
{
  "valid": false,
  "error": "Link expired at 2025-11-30 20:23:30"
}
```

## Testing

### Manual Test

```bash
# Generate test URL
python -c "
from src.auth.url_signer import URLSigner
import os

secret = os.environ.get('URL_SIGNING_SECRET')
signer = URLSigner(secret)

url = signer.sign_url(
    'https://cerjho.github.io/IoT-Attendance-System/view-attendance.html',
    '2021001',
    48
)

print(url)
"
```

### Automated Tests

```bash
# Run all tests
python tests/test_signed_urls.py

# Run specific test
python -c "
from tests.test_signed_urls import test_tampering
result = test_tampering()
print('✅ PASS' if result else '❌ FAIL')
"
```

## Rotation Plan

### When to Rotate Secret

- **Immediate**: Secret exposed/leaked
- **Periodic**: Every 90 days (recommended)
- **After incident**: Any security breach

### How to Rotate

1. Generate new secret:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

2. Update `.env`:
```bash
sed -i 's/URL_SIGNING_SECRET=.*/URL_SIGNING_SECRET=new-secret/' .env
```

3. Restart services:
```bash
sudo systemctl restart attendance-system attendance-dashboard
```

4. **Note**: All existing links become invalid immediately

### Gradual Rotation (Advanced)

Support both old and new secrets during transition:

```python
# In url_signer.py, verify with fallback
def verify_url(self, url, fallback_secret=None):
    # Try primary secret first
    if self._verify_with_secret(url, self.secret_key):
        return True
    
    # Try fallback secret
    if fallback_secret and self._verify_with_secret(url, fallback_secret):
        logger.warning("Verified with fallback secret")
        return True
    
    return False
```

## Production Checklist

- [ ] URL_SIGNING_SECRET generated (64 chars)
- [ ] Secret added to .env (not committed to Git)
- [ ] Config: `use_signed_urls: true`
- [ ] Config: `signed_url_expiry_hours` set appropriately
- [ ] Dashboard service restarted
- [ ] Test suite passed (5/5 tests)
- [ ] SMS message sent with signed URL
- [ ] Attendance view loads successfully
- [ ] Expired URL rejected with clear message
- [ ] Tampered URL rejected
- [ ] Verification logs reviewed

## Support

For issues or questions:
- Check logs: `data/logs/system.log`
- Run tests: `python tests/test_signed_urls.py`
- Review code: `src/auth/url_signer.py`

## Related Documentation

- `docs/security/SECURITY_SETUP.md` - General security configuration
- `docs/security/SECURE_DEPLOYMENT_SUMMARY.md` - Deployment guide
- `.github/copilot-instructions.md` - Development patterns
