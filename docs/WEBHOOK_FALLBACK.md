# Webhook Fallback for SMS Notifications

## Overview

The webhook fallback system provides a reliable backup when the local Android SMS Gateway has no signal or fails to send messages. This ensures parents always receive attendance notifications even when the IoT device has connectivity issues.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ Student Scans QR                                            │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Try Local SMS Gateway (Primary)                             │
│ - Uses Android SMS Gateway API                              │
│ - 3 retry attempts with exponential backoff                 │
└────────────────────┬────────────────────────────────────────┘
                     ▼
              ┌──────┴──────┐
              │  Success?   │
              └──────┬──────┘
           Yes ◄─────┴─────► No
            │                 │
            ▼                 ▼
     ┌──────────┐    ┌──────────────────┐
     │   Done   │    │ Webhook Fallback │
     └──────────┘    │ (Cloud Endpoint) │
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ Commercial SMS   │
                     │ (Semaphore/      │
                     │  Twilio)         │
                     └────────┬─────────┘
                              ▼
                     ┌──────────────────┐
                     │ SMS Delivered ✓  │
                     └──────────────────┘
```

## Configuration

### 1. Update `config/config.json`

```json
{
  "sms_notifications": {
    "enabled": true,
    "username": "${SMS_USERNAME}",
    "password": "${SMS_PASSWORD}",
    "device_id": "${SMS_DEVICE_ID}",
    "api_url": "${SMS_API_URL}",
    
    "webhook": {
      "enabled": true,
      "url": "https://your-server.vercel.app/api/sms/retry",
      "auth_header": "Bearer YOUR_API_KEY",
      "timeout": 10,
      "on_failure_only": true
    }
  }
}
```

**Configuration Options:**

- `enabled`: Enable/disable webhook fallback (default: `false`)
- `url`: Cloud endpoint URL that will handle SMS retry
- `auth_header`: Authorization header for webhook (optional)
- `timeout`: Request timeout in seconds (default: 10)
- `on_failure_only`: Only send to webhook when SMS fails (default: `true`)

### 2. Cloud Webhook Endpoint

You need to deploy a cloud endpoint that receives webhook requests and sends SMS via a commercial provider.

#### Option A: Vercel + Semaphore (Philippines)

Create `api/sms/retry.js` in your Vercel project:

```javascript
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { phone, message, device_id } = req.body;
  
  // Log retry attempt
  console.log(`SMS Retry: device=${device_id}, phone=${phone}`);
  
  // Send via Semaphore
  const response = await fetch('https://api.semaphore.co/api/v4/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      apikey: process.env.SEMAPHORE_API_KEY,
      number: phone,
      message: message,
      sendername: 'MabiniHS'
    })
  });

  const result = await response.json();
  
  if (response.ok) {
    console.log(`✅ SMS retry success: ${phone}`);
    return res.status(200).json({ 
      success: true, 
      message_id: result.message_id 
    });
  } else {
    console.error(`❌ SMS retry failed: ${result.message}`);
    return res.status(500).json({ 
      success: false, 
      error: result.message 
    });
  }
}
```

**Deploy:**
```bash
vercel deploy
```

**Environment Variables:**
```bash
vercel env add SEMAPHORE_API_KEY
```

#### Option B: Flask + Twilio

```python
from flask import Flask, request, jsonify
from twilio.rest import Client
import os

app = Flask(__name__)

@app.route('/api/sms/retry', methods=['POST'])
def retry_sms():
    data = request.json
    
    client = Client(
        os.environ['TWILIO_ACCOUNT_SID'],
        os.environ['TWILIO_AUTH_TOKEN']
    )
    
    try:
        message = client.messages.create(
            to=data['phone'],
            from_=os.environ['TWILIO_PHONE'],
            body=data['message']
        )
        
        return jsonify({
            'success': True,
            'message_id': message.sid
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

## Testing

### Test Normal Flow (Webhook Should NOT Trigger)

```bash
python test_webhook_fallback.py
```

Expected output:
```
Test 1: Normal SMS flow (webhook disabled)
Result: ✅ Success

Test 2: SMS with webhook enabled (on_failure_only=true)
Expected: SMS succeeds → webhook NOT called
Result: ✅ Success
```

### Test Failure Scenario (Webhook Should Trigger)

The test script simulates SMS failure and verifies webhook activation.

## SMS Providers

### Philippines (Recommended)

**Semaphore** (https://semaphore.co)
- Cost: ~₱1.00 per SMS
- Very reliable
- Local support
- Easy API

**Get API Key:**
1. Sign up at semaphore.co
2. Dashboard → API → Generate Key
3. Add to environment: `SEMAPHORE_API_KEY`

### International

**Twilio** (https://twilio.com)
- Cost: ~$0.0075 per SMS
- Global coverage
- Robust API

**Vonage** (https://vonage.com)
- Cost: ~$0.005 per SMS
- Good Philippines support

## Cost Comparison

| Method | Cost per SMS | Reliability | Notes |
|--------|--------------|-------------|-------|
| Android SMS Gateway | ₱0 (Free) | High (when signal available) | Primary method |
| Webhook → Semaphore | ~₱1.00 | Very High | Fallback only |
| Webhook → Twilio | ~₱0.42 | Very High | International |

**Average Cost Impact:**
- If 5% of SMS need fallback: ₱0.05 per student per day
- For 100 students: ₱5/day = ₱100/month additional cost

## Security

### Webhook Authentication

Always use authentication on your webhook endpoint:

```json
{
  "webhook": {
    "auth_header": "Bearer your-secret-token-here"
  }
}
```

Generate a secure token:
```bash
openssl rand -hex 32
```

### Endpoint Security Best Practices

1. **Use HTTPS only** - No HTTP endpoints
2. **Validate requests** - Check auth header
3. **Rate limiting** - Prevent abuse
4. **Log all attempts** - Monitor for suspicious activity
5. **IP whitelist** (optional) - Restrict to your IoT device IP

## Monitoring

### Logs

Check webhook activity in system logs:

```bash
grep "webhook" data/logs/attendance_*.log
```

### Success Indicators

```
✅ Webhook sent successfully: to=+639755269146, status=200
```

### Failure Indicators

```
⚠️ Webhook failed: status=500, response=...
❌ Both SMS and webhook failed
```

## Troubleshooting

### Webhook Not Triggering

1. **Check configuration:**
   ```bash
   grep -A 5 "webhook" config/config.json
   ```

2. **Verify enabled:**
   ```json
   "webhook": {
     "enabled": true,  ← Must be true
     "on_failure_only": true
   }
   ```

3. **Test endpoint:**
   ```bash
   curl -X POST https://your-server.com/api/sms/retry \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"phone":"+639123456789","message":"Test"}'
   ```

### Webhook Timeout

Increase timeout in config:
```json
"webhook": {
  "timeout": 30  ← Increase from default 10s
}
```

### Both SMS and Webhook Fail

Check logs for specific errors:
```bash
tail -f data/logs/attendance_*.log | grep -i "sms\|webhook"
```

## Production Deployment

### Recommended Setup

1. **Primary:** Android SMS Gateway (free, fast)
2. **Fallback:** Webhook → Semaphore (reliable, low cost)
3. **Monitoring:** Daily check of fallback usage

### Environment Variables

Add to `.env`:
```bash
# Webhook endpoint
WEBHOOK_URL=https://your-server.vercel.app/api/sms/retry
WEBHOOK_AUTH_TOKEN=your-secret-token
```

Update config to use env vars:
```json
"webhook": {
  "enabled": true,
  "url": "${WEBHOOK_URL}",
  "auth_header": "Bearer ${WEBHOOK_AUTH_TOKEN}"
}
```

## FAQ

**Q: Will webhook slow down the system?**
A: No. Webhook only activates after SMS fails (3 attempts), so normal flow is unaffected.

**Q: What if webhook also fails?**
A: The system continues normally. Parents won't get SMS but attendance is still recorded locally and synced to cloud.

**Q: Can I disable webhook?**
A: Yes. Set `"enabled": false` in webhook config. System works fine without it.

**Q: Does this work offline?**
A: Webhook requires internet. If device is offline, neither SMS nor webhook will work, but attendance is queued locally for later sync.

## Support

For issues or questions:
1. Check logs: `data/logs/attendance_*.log`
2. Test webhook: `python test_webhook_fallback.py`
3. Review this documentation
