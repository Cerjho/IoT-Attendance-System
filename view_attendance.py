#!/usr/bin/env python3
"""
View Attendance Database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.database import AttendanceDatabase
from datetime import datetime

def main():
    db = AttendanceDatabase('data/attendance.db')
    
    print("\n" + "="*70)
    print("ATTENDANCE DATABASE VIEWER")
    print("="*70)
    
    # Statistics
    stats = db.get_statistics()
    print("\n📊 Statistics:")
    print(f"  Total Students: {stats.get('total_students', 0)}")
    print(f"  Total Attendance Records: {stats.get('total_records', 0)}")
    print(f"  Today's Attendance: {stats.get('today_attendance', 0)}")
    
    # Today's attendance
    print("\n" + "="*70)
    print("TODAY'S ATTENDANCE")
    print("="*70)
    
    today_records = db.get_today_attendance()
    
    if today_records:
        print(f"\n{len(today_records)} student(s) scanned today:\n")
        for i, record in enumerate(today_records, 1):
            timestamp = datetime.fromisoformat(record['timestamp'])
            print(f"{i}. Student ID: {record['student_id']}")
            print(f"   Time: {timestamp.strftime('%H:%M:%S')}")
            print(f"   Photo: {record['photo_path']}")
            if record.get('name'):
                print(f"   Name: {record['name']}")
            print()
    else:
        print("\nNo attendance records for today")
    
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
