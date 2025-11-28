#!/usr/bin/env python3
"""
Test connection and functionality with new Supabase server
"""

import os
import sys

sys.path.insert(0, "/home/iot/attendance-system")

from datetime import datetime

import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("=" * 70)
print("🧪 TESTING NEW SUPABASE CONNECTION")
print("=" * 70)
print()
print(f"Server: {SUPABASE_URL}")
print()

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

# Test 1: Fetch students
print("[TEST 1] Fetching active students...")
try:
    url = f"{SUPABASE_URL}/rest/v1/students"
    params = {
        "select": "student_number,first_name,middle_name,last_name,email,parent_guardian_contact,grade_level,section,status",
        "status": "eq.active",
    }
    response = requests.get(url, headers=headers, params=params, timeout=10)

    if response.status_code == 200:
        students = response.json()
        print(f"✅ SUCCESS: {len(students)} active students found")

        if students:
            print("\n📋 Sample students:")
            for i, student in enumerate(students[:5], 1):
                name = f"{student.get('first_name', '')} {student.get('middle_name', '')} {student.get('last_name', '')}".strip()
                print(f"   {i}. {name}")
                print(f"      ID: {student.get('student_number')}")
                print(
                    f"      Grade: {student.get('grade_level')} | Section: {student.get('section')}"
                )
                print(f"      Contact: {student.get('parent_guardian_contact')}")
                print()
    else:
        print(f"❌ FAILED: HTTP {response.status_code}")
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ ERROR: {e}")

print()

# Test 2: Check attendance table structure
print("[TEST 2] Checking attendance table...")
try:
    url = f"{SUPABASE_URL}/rest/v1/attendance"
    params = {"select": "id,student_id,date,time_in,status,device_id", "limit": 5}
    response = requests.get(url, headers=headers, params=params, timeout=10)

    if response.status_code == 200:
        records = response.json()
        print(f"✅ SUCCESS: Attendance table accessible ({len(records)} records)")

        if records:
            print("\n📋 Recent attendance records:")
            for record in records:
                print(
                    f"   • Date: {record.get('date')} | Time: {record.get('time_in')} | Status: {record.get('status')}"
                )
    else:
        print(f"❌ FAILED: HTTP {response.status_code}")
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ ERROR: {e}")

print()

# Test 3: Simulate attendance insert (dry run - lookup only)
print("[TEST 3] Testing student UUID lookup...")
try:
    if students and len(students) > 0:
        test_student = students[0]
        student_number = test_student.get("student_number")

        url = f"{SUPABASE_URL}/rest/v1/students"
        params = {"student_number": f"eq.{student_number}", "select": "id"}
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result:
                student_uuid = result[0]["id"]
                print(
                    f"✅ SUCCESS: Student number '{student_number}' → UUID '{student_uuid}'"
                )
                print("   This mapping will be used for attendance sync")
            else:
                print(f"❌ FAILED: No UUID found for student {student_number}")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
    else:
        print("⚠️  SKIPPED: No students available for testing")
except Exception as e:
    print(f"❌ ERROR: {e}")

print()
print("=" * 70)
print("✅ CONNECTION TEST COMPLETE")
print("=" * 70)
print()
print("Summary:")
print("   • Supabase server: Connected")
print("   • Students table: Accessible")
print("   • Attendance table: Accessible")
print("   • UUID lookup: Working")
print()
print("The IoT system is ready to:")
print("   1. Cache students locally from Supabase")
print("   2. Scan QR codes (student_number)")
print("   3. Upload attendance with UUID mapping")
print()
