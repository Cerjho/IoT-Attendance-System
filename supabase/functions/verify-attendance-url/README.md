# Verify Attendance URL - Supabase Edge Function

## Purpose

Verifies HMAC-signed attendance URLs to prevent tampering with student UUIDs.

## Endpoint

```
https://YOUR-PROJECT.supabase.co/functions/v1/verify-attendance-url
```

## Request

**Method:** `GET`

**Query Parameters:**
- `student_id` (string, required) - Student UUID
- `expires` (string, required) - Unix timestamp (seconds)
- `sig` (string, required) - HMAC-SHA256 signature (hex)

**Example:**
```
GET /functions/v1/verify-attendance-url?student_id=0dedc5b0-ee62-431c-82d6-dde2633083e8&expires=1733183235&sig=b8e9c4a3f2d1...
```

## Response

**Success (200):**
```json
{
  "valid": true,
  "student_uuid": "0dedc5b0-ee62-431c-82d6-dde2633083e8",
  "expires_at": "2025-12-02T23:07:15.000Z"
}
```

**Invalid Signature (403):**
```json
{
  "valid": false,
  "error": "Invalid signature - link may have been tampered with"
}
```

**Expired (403):**
```json
{
  "valid": false,
  "error": "Link has expired"
}
```

**Invalid Parameters (400):**
```json
{
  "valid": false,
  "error": "Missing required parameters: student_id, expires, sig"
}
```

## Deployment

### 1. Install Supabase CLI

```bash
# macOS/Linux
curl -fsSL https://cli.supabase.com/install | sh

# Or with npm
npm install -g supabase
```

### 2. Login to Supabase

```bash
supabase login
```

### 3. Link to Your Project

```bash
cd /home/iot/attendance-system
supabase link --project-ref YOUR-PROJECT-REF
```

Get your project ref from: https://supabase.com/dashboard/project/_/settings/general

### 4. Set Signing Secret

```bash
# Generate a random secret (or use existing one)
SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Set in Supabase
supabase secrets set SIGNING_SECRET="$SECRET"

# Also save to your .env for local use
echo "SIGNING_SECRET=$SECRET" >> .env
```

### 5. Deploy Function

```bash
supabase functions deploy verify-attendance-url
```

### 6. Test Function

```bash
# Get your project URL and anon key from Supabase dashboard
SUPABASE_URL="https://your-project.supabase.co"
ANON_KEY="your-anon-key"

# Test with valid signature
curl "$SUPABASE_URL/functions/v1/verify-attendance-url?student_id=test&expires=9999999999&sig=abc123" \
  -H "Authorization: Bearer $ANON_KEY"
```

## Integration

### Update HTML (public/view-attendance.html)

Change the verification API URL:

```javascript
// Before (local Pi API)
const VERIFY_API = 'http://192.168.1.22:8080/api/verify-url';

// After (Supabase Edge Function)
const VERIFY_API = 'https://YOUR-PROJECT.supabase.co/functions/v1/verify-attendance-url';
```

### Update SMS Notifier (src/notifications/sms_notifier.py)

The SMS notifier already generates signatures - just ensure it uses the same `SIGNING_SECRET`:

```python
# In .env file
SIGNING_SECRET=your_secret_here_must_match_supabase
```

## Security

✅ **Signing secret is hidden** - Stored in Supabase secrets, not in HTML
✅ **HTTPS only** - Edge function runs on Supabase infrastructure
✅ **CORS enabled** - Allows calls from any origin (Vercel, GitHub Pages)
✅ **Expiration checked** - Links expire after 24 hours
✅ **Constant-time comparison** - Signature verified securely
✅ **No rate limiting needed** - Signature prevents brute force

## Monitoring

View function logs:

```bash
supabase functions logs verify-attendance-url
```

View in dashboard:
https://supabase.com/dashboard/project/_/functions/verify-attendance-url/logs

## Cost

**Free Tier:**
- 500K function invocations/month
- 2 GB outbound data transfer/month

More than enough for school attendance system!

## Troubleshooting

**403 Forbidden:**
- Check SIGNING_SECRET matches between Pi and Supabase
- Verify signature is hex-encoded HMAC-SHA256
- Check link hasn't expired

**500 Internal Server Error:**
- Check function logs: `supabase functions logs verify-attendance-url`
- Verify SIGNING_SECRET is set: `supabase secrets list`

**CORS Error:**
- Function already has CORS headers enabled
- Check browser console for actual error

## Local Development

Test locally before deploying:

```bash
# Start local Supabase
supabase start

# Serve function locally
supabase functions serve verify-attendance-url --env-file .env

# Test
curl "http://localhost:54321/functions/v1/verify-attendance-url?student_id=test&expires=9999999999&sig=abc123"
```
