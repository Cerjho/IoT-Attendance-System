#!/usr/bin/env python3
"""
Database Migration: Add UUID column to students table
Migrates existing students table to include uuid column for Supabase UUID caching
"""

import sqlite3
import sys
from pathlib import Path

def migrate_students_table(db_path: str = "data/attendance.db"):
    """
    Add uuid column to students table if it doesn't exist
    
    Args:
        db_path: Path to SQLite database
    """
    try:
        # Check if database exists
        if not Path(db_path).exists():
            print(f"❌ Database not found: {db_path}")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if uuid column already exists
        cursor.execute("PRAGMA table_info(students)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'uuid' in columns:
            print("✅ UUID column already exists in students table")
            conn.close()
            return True
        
        # Add uuid column
        print("🔧 Adding uuid column to students table...")
        cursor.execute("ALTER TABLE students ADD COLUMN uuid TEXT")
        
        conn.commit()
        conn.close()
        
        print("✅ Migration complete! UUID column added to students table")
        print("   Run roster sync to populate UUIDs: python -c \"from src.sync.roster_sync import RosterSyncManager; from src.utils.config_loader import load_config; r = RosterSyncManager(load_config()); r.download_today_roster(force=True)\"")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/attendance.db"
    success = migrate_students_table(db_path)
    sys.exit(0 if success else 1)
