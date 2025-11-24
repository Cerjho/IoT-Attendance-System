#!/usr/bin/env python3
"""
Database migration script to add parent_phone column
"""
import sqlite3
import os

db_path = 'data/attendance.db'

if not os.path.exists(db_path):
    print(f"Database not found: {db_path}")
    print("Run the attendance system first to create the database.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if parent_phone column exists
cursor.execute("PRAGMA table_info(students)")
columns = [row[1] for row in cursor.fetchall()]

if 'parent_phone' not in columns:
    print("Adding parent_phone column to students table...")
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN parent_phone TEXT")
        conn.commit()
        print("✓ Column added successfully!")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("✓ parent_phone column already exists")

# Show current structure
print("\nCurrent students table structure:")
cursor.execute("PRAGMA table_info(students)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

# Show student count
cursor.execute("SELECT COUNT(*) FROM students")
count = cursor.fetchone()[0]
print(f"\nTotal students: {count}")

conn.close()
