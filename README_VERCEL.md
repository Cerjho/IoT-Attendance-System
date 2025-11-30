# Deploy to Vercel - Quick Guide

## 🚀 One-Click Deployment

### Step 1: Login to Vercel
1. Go to: **https://vercel.com**
2. Click **"Sign Up"** or **"Login"**
3. Choose **"Continue with GitHub"** (1 click!)
4. Authorize Vercel to access your GitHub

### Step 2: Import Repository
1. Click **"Add New..."** → **"Project"**
2. Find **"IoT-Attendance-System"** in the list
3. Click **"Import"**

### Step 3: Configure Project
Leave everything as default:
- **Framework Preset:** Other
- **Root Directory:** `./` (keep as is)
- **Build Command:** (leave empty)
- **Output Directory:** `public`

Click **"Deploy"**

### Step 4: Get Your URL
After 30 seconds, you'll get:
```
https://iot-attendance-system.vercel.app
```

Or customize the name:
```
https://mabini-attendance.vercel.app
```

## ✅ What Gets Deployed

- ✅ `public/view-attendance.html` - Parent attendance page
- ✅ `public/index.html` - Welcome page
- ✅ Automatic HTTPS
- ✅ Global CDN (fast worldwide)
- ✅ Auto-deploys on git push

## 🔧 After Deployment

### Update SMS Links
Edit `config/config.json`:
```json
{
  "sms_notifications": {
    "attendance_view_url": "https://YOUR-PROJECT.vercel.app/view-attendance.html?student_id={student_id}"
  }
}
```

### Update HTML API Endpoint
The HTML currently has verification disabled. To enable it, you'll need to:

**Option A: Use Local IP (works on same network)**
```javascript
const VERIFY_API = 'http://192.168.1.22:8080/api/verify-url';
```

**Option B: Setup Cloudflare Tunnel (recommended)**
Follow `scripts/setup_cloudflare_tunnel.sh` to expose your Pi API securely.

**Option C: Use Vercel Serverless Function** (see below)

## 🎯 Next Steps

### Enable Signature Verification (Optional)

If you want to verify signed URLs:

1. Setup Cloudflare Tunnel for your Pi API
2. Update `VERIFY_API` in `public/view-attendance.html`
3. Re-enable verification code (uncomment)
4. Push to GitHub → Auto-deploys to Vercel

### Custom Domain (Optional)

In Vercel dashboard:
1. Go to project settings
2. Click "Domains"
3. Add your domain (if you have one)

## 📊 Monitoring

- **Deployments:** https://vercel.com/dashboard
- **Analytics:** Built-in (see dashboard)
- **Logs:** Real-time in Vercel dashboard

## 🔒 Security

Current setup:
- ✅ HTTPS automatic
- ✅ UUIDs used (not student numbers)
- ⚠️ Signature verification disabled (until API exposed)

To enable full security:
1. Setup Cloudflare Tunnel or ngrok
2. Update API endpoint in HTML
3. Re-enable signature verification

## 🆘 Troubleshooting

**404 Error:**
- Check `vercel.json` routes are correct
- Ensure files are in `public/` folder

**Build Failed:**
- No build needed for static site
- Check `.vercelignore` is present

**Slow Loading:**
- Vercel uses global CDN (should be fast)
- Check network connection

## 📝 Useful Commands

```bash
# Install Vercel CLI (optional)
npm i -g vercel

# Deploy from command line
vercel --prod

# Check deployment status
vercel ls

# View logs
vercel logs
```

## 🎉 You're Done!

Your attendance page is now live at:
```
https://YOUR-PROJECT.vercel.app
```

Parents can access it from anywhere in the world! 🌍
