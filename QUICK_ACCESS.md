# Quick Access Guide

## 🚀 Dashboard Access (HTTPS Only)

**Production URL:**
```
https://192.168.1.22
```

**What happens:**
1. Browser shows certificate warning (self-signed) ⚠️
2. Click "Advanced" → "Accept Risk and Continue"
3. Dashboard loads with API key prompt
4. Enter API key (stored in session)
5. View fleet management interface

**No more:**
- ❌ No HTTP on port 8888
- ❌ No mixed content warnings
- ❌ No protocol switching
- ❌ Single certificate acceptance

## ✅ Architecture

```
Browser (HTTPS) → Nginx (443) → {
    ├─ Static files: /home/iot/attendance-system/public/
    └─ API requests: localhost:8080 (dashboard service)
}
```

**Benefits:**
- ✅ Single HTTPS endpoint
- ✅ One certificate warning
- ✅ Production-ready security
- ✅ Clean URL structure

## 📝 API Key

Stored in: `/home/iot/attendance-system/.env`
```bash
DASHBOARD_API_KEY=hInJfwkBNOOsF0ZpUWm3pC_g21kJMujLDQeXFgH1HV8
```

## 🔧 Services

```bash
# Dashboard API
systemctl status attendance-dashboard.service

# Nginx (HTTPS proxy + static files)
systemctl status nginx
```

---

**Everything runs through HTTPS now! 🔒**
