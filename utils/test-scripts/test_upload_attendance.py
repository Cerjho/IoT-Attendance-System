#!/usr/bin/env python3
"""
Test script to upload attendance record with photo to Supabase
"""
import os
import sys
from datetime import datetime

import requests


# Load environment variables manually
def load_env():
    env_vars = {}
    env_file = ".env"
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


env_vars = load_env()
SUPABASE_URL = env_vars.get("SUPABASE_URL")
SUPABASE_KEY = (
    env_vars.get("SUPABASE_SERVICE_KEY")
    or env_vars.get("SUPABASE_KEY")
    or env_vars.get("SUPABASE_ANON_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)

# Configuration
PHOTO_PATH = None  # Will be set by command line or use existing photo
STUDENT_NUMBER = "221566"  # John Paolo Gonzales
BUCKET_NAME = "attendance-photos"

# Try to find an existing test photo
import glob

test_photos = (
    glob.glob("data/photos/*.jpg")
    + glob.glob("data/photos/*.jpeg")
    + glob.glob("data/photos/*.png")
)
if test_photos:
    PHOTO_PATH = test_photos[0]  # Use first available photo


def get_student_uuid(student_number):
    """Get student UUID from student_number"""
    url = (
        f"{SUPABASE_URL}/rest/v1/students?student_number=eq.{student_number}&select=id"
    )
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data and len(data) > 0:
            return data[0]["id"]
    return None


def upload_photo(photo_path, student_number):
    """Upload photo to Supabase Storage"""
    if not os.path.exists(photo_path):
        print(f"❌ Photo not found: {photo_path}")
        return None

    # Read photo file
    with open(photo_path, "rb") as f:
        file_data = f.read()

    # Generate cloud path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(photo_path)
    cloud_path = f"{student_number}/{timestamp}_{filename}"

    # Upload to storage
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{cloud_path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "image/jpeg",
    }

    print(f"📤 Uploading photo to: {cloud_path}")
    response = requests.post(upload_url, headers=headers, data=file_data, timeout=30)

    if response.status_code in [200, 201]:
        # Generate public URL
        public_url = (
            f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{cloud_path}"
        )
        print(f"✅ Photo uploaded successfully")
        print(f"   URL: {public_url}")
        return public_url
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None


def create_attendance_record(student_uuid, photo_url):
    """Create attendance record in Supabase"""
    now = datetime.now()

    attendance_data = {
        "student_id": student_uuid,
        "date": now.strftime("%Y-%m-%d"),
        "time_in": now.strftime("%H:%M:%S"),
        "status": "present",
        "device_id": "test_device",
        "remarks": f"Test record - Photo: {photo_url}",
    }

    # Try to add photo_url if column exists
    try:
        attendance_data["photo_url"] = photo_url
    except:
        pass

    url = f"{SUPABASE_URL}/rest/v1/attendance"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    print(f"\n📝 Creating attendance record...")
    response = requests.post(url, headers=headers, json=attendance_data, timeout=10)

    if response.status_code in [200, 201]:
        data = response.json()
        print(f"✅ Attendance record created successfully")
        if data and len(data) > 0:
            print(f"   Record ID: {data[0].get('id')}")
        return True
    else:
        print(f"❌ Failed to create attendance record: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def main():
    print("=" * 70)
    print("TEST ATTENDANCE UPLOAD TO SUPABASE")
    print("=" * 70)
    print(f"\nStudent: {STUDENT_NUMBER}")

    # Allow photo path as command line argument
    global PHOTO_PATH
    if len(sys.argv) > 1:
        PHOTO_PATH = sys.argv[1]

    if not PHOTO_PATH:
        print("❌ No photo found!")
        print("   Usage: python3 test_upload_attendance.py <photo_path>")
        print("   Or place a photo in data/photos/ directory")
        sys.exit(1)

    if not os.path.exists(PHOTO_PATH):
        print(f"❌ Photo not found: {PHOTO_PATH}")
        sys.exit(1)

    print(f"Photo: {PHOTO_PATH}")
    print()

    # Step 1: Get student UUID
    print("🔍 Step 1: Looking up student...")
    student_uuid = get_student_uuid(STUDENT_NUMBER)

    if not student_uuid:
        print(f"❌ Student not found: {STUDENT_NUMBER}")
        print("   Make sure the student exists in Supabase students table")
        sys.exit(1)

    print(f"✅ Found student UUID: {student_uuid}")

    # Step 2: Upload photo
    print(f"\n📸 Step 2: Uploading photo...")
    photo_url = upload_photo(PHOTO_PATH, STUDENT_NUMBER)

    if not photo_url:
        print("❌ Failed to upload photo")
        sys.exit(1)

    # Step 3: Create attendance record
    print(f"\n💾 Step 3: Creating attendance record...")
    success = create_attendance_record(student_uuid, photo_url)

    if success:
        print("\n" + "=" * 70)
        print("✅ TEST COMPLETE - Attendance record created with photo!")
        print("=" * 70)
        print(f"\n🔗 View attendance at:")
        print(
            f"   https://cerjho.github.io/IoT-Attendance-System/view-attendance.html?student_id={STUDENT_NUMBER}"
        )
    else:
        print("\n❌ Failed to complete test")
        sys.exit(1)


if __name__ == "__main__":
    main()
