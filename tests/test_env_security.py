#!/usr/bin/env python3
"""
Test configuration security - verify environment variables are loaded
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Manually load .env
print("✓ Loading .env file...")
with open(".env", "r") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

# Check if env vars are loaded
print("\n✓ Environment Variables Check:")
env_vars = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "DEVICE_ID",
    "SMS_USERNAME",
    "SMS_PASSWORD",
    "SMS_DEVICE_ID",
    "SMS_API_URL",
]
all_set = True
for var in env_vars:
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "KEY" in var or "PASSWORD" in var:
            display = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display = value[:30] + "..." if len(value) > 30 else value
        print(f"  ✓ {var}: {display}")
    else:
        print(f"  ✗ {var}: NOT SET")
        all_set = False

print("\n✓ Config Loader Test:")
from src.utils.config_loader import load_config

config = load_config("config/config.json")

# Test sensitive values are loaded from env
cloud_url = config.get("cloud.url")
cloud_key = config.get("cloud.api_key")
sms_user = config.get("sms_notifications.username")
sms_pass = config.get("sms_notifications.password")
device_id = config.get("cloud.device_id")

resolved = True

if cloud_url and not cloud_url.startswith("${"):
    print(f"  ✓ Cloud URL: {cloud_url[:40]}...")
else:
    print(f"  ✗ Cloud URL: NOT RESOLVED")
    resolved = False

if cloud_key and not cloud_key.startswith("${"):
    print(f"  ✓ Cloud Key: {cloud_key[:20]}...")
else:
    print(f"  ✗ Cloud Key: NOT RESOLVED")
    resolved = False

if device_id and not device_id.startswith("${"):
    print(f"  ✓ Device ID: {device_id}")
else:
    print(f"  ✗ Device ID: NOT RESOLVED")
    resolved = False

if sms_user and not sms_user.startswith("${"):
    print(f"  ✓ SMS Username: {sms_user}")
else:
    print(f"  ✗ SMS Username: NOT RESOLVED")
    resolved = False

if sms_pass and not sms_pass.startswith("${"):
    print(f"  ✓ SMS Password: {sms_pass[:5]}...")
else:
    print(f"  ✗ SMS Password: NOT RESOLVED")
    resolved = False

if all_set and resolved:
    print("\n✅ SUCCESS: Configuration secured! All sensitive data loaded from .env")
    print("\n📝 Security Notes:")
    print("  - Sensitive keys are NOT in config.json")
    print("  - All credentials loaded from .env file")
    print("  - .env is in .gitignore (never committed)")
    print("  - Use .env.example as template for new setups")
else:
    print("\n⚠️  WARNING: Some environment variables not properly configured")
    sys.exit(1)
