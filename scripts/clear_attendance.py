#!/usr/bin/env python3
"""
Clear all attendance records from the local SQLite database with a backup export.
"""
import os
import sys

# Ensure project root is on path so `src` package is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.database.db_handler import AttendanceDatabase

DB_PATH = 'data/attendance.db'

def main():
    db = AttendanceDatabase(DB_PATH)

    print('Exporting current database to JSON backup...')
    backup = db.export_to_json()
    if backup:
        print(f'Backup saved to: {backup}')
    else:
        print('Backup failed or not created.')

    # Confirm with user when running interactively
    if sys.stdin and sys.stdin.isatty():
        resp = input('Proceed to DELETE all attendance records? Type YES to confirm: ')
        if resp.strip() != 'YES':
            print('Aborted by user.')
            return

    import sqlite3
    print('Deleting attendance records...')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM attendance')
    before = cur.fetchone()[0]
    cur.execute('DELETE FROM attendance')
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM attendance')
    after = cur.fetchone()[0]
    conn.close()

    print(f'Records before: {before}, after: {after}')
    print('Done.')

if __name__ == '__main__':
    main()
