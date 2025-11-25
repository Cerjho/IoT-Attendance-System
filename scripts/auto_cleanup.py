#!/usr/bin/env python3
"""
Automated Cleanup of Local Attendance Data After Supabase Sync

This script safely clears local attendance records, photos, and exports after
verifying all data has been successfully synced to Supabase cloud.

Safety features:
  - Verifies sync status before clearing
  - Creates automatic JSON backup
  - Creates database backup
  - Clears attendance records
  - Removes local photos
  - Cleans up old exports
  - Comprehensive error handling and reporting
"""

import sys
import os
import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.database.db_handler import AttendanceDatabase
from dotenv import load_dotenv

load_dotenv()


class AutoCleanup:
    """Automated cleanup with safety checks and reporting"""

    def __init__(self, db_path='data/attendance.db'):
        self.db_path = db_path
        self.db = AttendanceDatabase(db_path)
        self.start_time = datetime.now()
        self.report = {
            'timestamp': self.start_time.isoformat(),
            'status': 'pending',
            'checks': {},
            'actions': {},
            'errors': [],
            'summary': {}
        }

    def print_header(self, title):
        """Print formatted section header"""
        print(f"\n{'='*70}")
        print(f"{title:^70}")
        print(f"{'='*70}\n")

    def log(self, message, level='INFO', icon='ℹ'):
        """Log message with formatting"""
        prefix = {
            'INFO': 'ℹ',
            'SUCCESS': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'STEP': '📍'
        }.get(level, icon)
        print(f"{prefix} {message}")

    def check_sync_status(self):
        """Step 1: Verify sync status before clearing"""
        self.log("Verifying sync status...", 'STEP')

        try:
            # Import here to avoid loading full system unnecessarily
            from attendance_system import IoTAttendanceSystem
            system = IoTAttendanceSystem()
            status = system.cloud_sync.get_sync_status()

            unsynced = status['unsynced_records']
            queue_size = status['queue_size']

            self.report['checks']['sync_status'] = {
                'cloud_enabled': status['enabled'],
                'online': status['online'],
                'unsynced_records': unsynced,
                'queue_size': queue_size,
                'device_id': status['device_id']
            }

            print(f"  - Cloud Sync: {'✅ Enabled' if status['enabled'] else '❌ Disabled'}")
            print(f"  - Online: {'✅ Yes' if status['online'] else '❌ No'}")
            print(f"  - Unsynced Records: {unsynced}")
            print(f"  - Queue Size: {queue_size}")

            # Check: cloud must be enabled
            if not status['enabled']:
                raise Exception("Cloud sync is disabled in config")

            # Check: must be online
            if not status['online']:
                raise Exception("No internet connection detected")

            # Check: all records must be synced
            if unsynced > 0:
                raise Exception(
                    f"Cannot proceed: {unsynced} records still unsynced. "
                    f"Run 'python scripts/sync_to_cloud.py' first."
                )

            # Check: queue should be empty
            if queue_size > 0:
                raise Exception(
                    f"Sync queue not empty ({queue_size} pending). "
                    f"Wait for background sync to complete."
                )

            self.log("Sync status verified successfully", 'SUCCESS')
            return True

        except Exception as e:
            self.log(f"Sync verification failed: {e}", 'ERROR')
            self.report['checks']['sync_status_error'] = str(e)
            self.report['errors'].append(f"Sync check: {str(e)}")
            return False

    def get_attendance_counts(self):
        """Get current attendance record counts from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM attendance WHERE synced=1")
            synced_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM attendance WHERE synced=0")
            unsynced_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM attendance")
            total_count = cur.fetchone()[0]

            conn.close()

            return {
                'total': total_count,
                'synced': synced_count,
                'unsynced': unsynced_count
            }
        except Exception as e:
            self.log(f"Error counting attendance records: {e}", 'WARNING')
            return {'total': 0, 'synced': 0, 'unsynced': 0}

    def backup_database(self):
        """Step 2: Create database backup"""
        self.log("Creating database backup...", 'STEP')

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.db_path}.backup_{timestamp}"

            shutil.copy2(self.db_path, backup_path)
            
            backup_size = os.path.getsize(backup_path) / 1024  # KB
            self.log(f"Database backed up to: {backup_path} ({backup_size:.1f} KB)", 'SUCCESS')
            
            self.report['actions']['database_backup'] = {
                'path': backup_path,
                'size_kb': backup_size,
                'timestamp': timestamp
            }
            return True

        except Exception as e:
            self.log(f"Database backup failed: {e}", 'ERROR')
            self.report['errors'].append(f"Database backup: {str(e)}")
            return False

    def export_json_backup(self):
        """Step 3: Export JSON backup of all records"""
        self.log("Exporting JSON backup...", 'STEP')

        try:
            backup_path = self.db.export_to_json()
            
            if backup_path and os.path.exists(backup_path):
                file_size = os.path.getsize(backup_path) / 1024  # KB
                self.log(f"JSON backup saved to: {backup_path} ({file_size:.1f} KB)", 'SUCCESS')
                
                self.report['actions']['json_backup'] = {
                    'path': backup_path,
                    'size_kb': file_size
                }
                return True
            else:
                raise Exception("Export returned no path")

        except Exception as e:
            self.log(f"JSON export failed: {e}", 'ERROR')
            self.report['errors'].append(f"JSON export: {str(e)}")
            return False

    def clear_attendance_records(self):
        """Step 4: Clear attendance records from database"""
        self.log("Clearing attendance records from database...", 'STEP')

        try:
            counts_before = self.get_attendance_counts()
            print(f"  Before: {counts_before['total']} total "
                  f"({counts_before['synced']} synced, {counts_before['unsynced']} unsynced)")

            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute('DELETE FROM attendance')
            conn.commit()
            conn.close()

            counts_after = self.get_attendance_counts()
            print(f"  After:  {counts_after['total']} total")

            deleted = counts_before['total'] - counts_after['total']
            self.log(f"Deleted {deleted} attendance records", 'SUCCESS')

            self.report['actions']['attendance_cleared'] = {
                'records_deleted': deleted,
                'before': counts_before['total'],
                'after': counts_after['total']
            }
            return True

        except Exception as e:
            self.log(f"Attendance clear failed: {e}", 'ERROR')
            self.report['errors'].append(f"Attendance clear: {str(e)}")
            return False

    def clear_photos(self):
        """Step 5: Remove local photo files"""
        self.log("Clearing local photos...", 'STEP')

        try:
            photos_dir = Path('photos')
            
            if not photos_dir.exists():
                self.log("Photos directory not found (skipping)", 'WARNING')
                self.report['actions']['photos_cleared'] = {
                    'photos_deleted': 0,
                    'reason': 'Directory not found'
                }
                return True

            # Count and remove photos
            photo_files = list(photos_dir.glob('attendance_*.jpg'))
            deleted_count = 0

            for photo_file in photo_files:
                try:
                    photo_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    self.log(f"Failed to delete {photo_file.name}: {e}", 'WARNING')

            total_size_freed = sum(
                f.stat().st_size for f in photo_files if f.exists()
            ) / (1024 * 1024)  # MB

            self.log(f"Deleted {deleted_count} photo files", 'SUCCESS')

            self.report['actions']['photos_cleared'] = {
                'photos_deleted': deleted_count,
                'total_files': len(photo_files)
            }
            return True

        except Exception as e:
            self.log(f"Photo cleanup failed: {e}", 'ERROR')
            self.report['errors'].append(f"Photo cleanup: {str(e)}")
            return False

    def clean_old_exports(self, keep_count=5):
        """Step 6: Clean old JSON export files, keeping most recent"""
        self.log(f"Cleaning old JSON exports (keeping {keep_count} most recent)...", 'STEP')

        try:
            data_dir = Path('data')
            
            if not data_dir.exists():
                self.log("Data directory not found (skipping)", 'WARNING')
                return True

            export_files = sorted(
                data_dir.glob('attendance_export_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            if len(export_files) <= keep_count:
                self.log(f"Only {len(export_files)} exports found, no cleanup needed", 'INFO')
                self.report['actions']['exports_cleaned'] = {
                    'exports_deleted': 0,
                    'exports_remaining': len(export_files)
                }
                return True

            # Delete older exports
            deleted_count = 0
            deleted_size = 0

            for export_file in export_files[keep_count:]:
                try:
                    file_size = export_file.stat().st_size / 1024  # KB
                    export_file.unlink()
                    deleted_count += 1
                    deleted_size += file_size
                except Exception as e:
                    self.log(f"Failed to delete {export_file.name}: {e}", 'WARNING')

            self.log(
                f"Deleted {deleted_count} old exports, freed {deleted_size/1024:.1f} MB",
                'SUCCESS'
            )

            self.report['actions']['exports_cleaned'] = {
                'exports_deleted': deleted_count,
                'exports_remaining': keep_count,
                'space_freed_mb': deleted_size / 1024
            }
            return True

        except Exception as e:
            self.log(f"Export cleanup failed: {e}", 'ERROR')
            self.report['errors'].append(f"Export cleanup: {str(e)}")
            return False

    def clean_sync_queue(self):
        """Step 7: Clean old sync queue entries"""
        self.log("Cleaning sync queue (removing max retry failures)...", 'STEP')

        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # Get current queue size
            cur.execute("SELECT COUNT(*) FROM sync_queue")
            before_count = cur.fetchone()[0]

            # Delete entries that exceeded max retries (3 by default)
            cur.execute("DELETE FROM sync_queue WHERE retry_count >= 3")
            conn.commit()

            # Get new queue size
            cur.execute("SELECT COUNT(*) FROM sync_queue")
            after_count = cur.fetchone()[0]

            deleted = before_count - after_count

            conn.close()

            self.log(f"Cleaned {deleted} failed queue entries", 'SUCCESS')

            self.report['actions']['queue_cleaned'] = {
                'entries_deleted': deleted,
                'entries_remaining': after_count
            }
            return True

        except Exception as e:
            self.log(f"Queue cleanup failed: {e}", 'WARNING')
            self.report['actions']['queue_cleaned'] = {
                'error': str(e),
                'status': 'skipped'
            }
            return True  # Don't fail on queue cleanup

        except Exception as e:
            self.log(f"Queue cleanup error: {e}", 'WARNING')
            return True

    def print_report(self):
        """Print summary report"""
        self.print_header("CLEANUP SUMMARY")

        print("✅ COMPLETED ACTIONS:\n")
        for action, details in self.report['actions'].items():
            print(f"  {action.replace('_', ' ').title()}:")
            if isinstance(details, dict):
                for key, value in details.items():
                    if key != 'path':
                        print(f"    • {key.replace('_', ' ')}: {value}")
            print()

        if self.report['errors']:
            print("⚠️  WARNINGS & ERRORS:\n")
            for error in self.report['errors']:
                print(f"  • {error}")
            print()

        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"⏱️  Completed in {elapsed:.1f} seconds")
        print()

    def save_report(self):
        """Save detailed report to JSON"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = f"data/cleanup_report_{timestamp}.json"

            self.report['status'] = 'completed' if not self.report['errors'] else 'completed_with_errors'
            self.report['elapsed_seconds'] = (
                datetime.now() - self.start_time
            ).total_seconds()

            with open(report_path, 'w') as f:
                json.dump(self.report, f, indent=2)

            self.log(f"Report saved to: {report_path}", 'INFO')

        except Exception as e:
            self.log(f"Failed to save report: {e}", 'WARNING')

    def run(self, skip_confirmation=False):
        """Execute full cleanup workflow"""
        self.print_header("AUTOMATED CLEANUP - LOCAL ATTENDANCE DATA")

        print("This script will:")
        print("  1. Verify all data is synced to Supabase")
        print("  2. Create database backup")
        print("  3. Export JSON backup")
        print("  4. Clear attendance records")
        print("  5. Remove local photos")
        print("  6. Clean old exports")
        print("  7. Clean sync queue")
        print()

        # Confirmation
        if not skip_confirmation and sys.stdin.isatty():
            response = input("⚠️  Proceed with cleanup? Type 'YES' to confirm: ").strip()
            if response != 'YES':
                self.log("Cleanup cancelled by user", 'WARNING')
                return False

        print()

        # Step 1: Verify sync
        if not self.check_sync_status():
            self.log("Cleanup aborted due to sync verification failure", 'ERROR')
            self.report['status'] = 'failed'
            self.save_report()
            return False

        # Step 2: Database backup
        if not self.backup_database():
            self.log("Cleanup aborted due to backup failure", 'ERROR')
            self.report['status'] = 'failed'
            self.save_report()
            return False

        # Step 3: JSON export
        if not self.export_json_backup():
            self.log("Warning: JSON export failed, but continuing...", 'WARNING')

        # Step 4: Clear attendance
        if not self.clear_attendance_records():
            self.log("Cleanup aborted due to clear failure", 'ERROR')
            self.report['status'] = 'failed'
            self.save_report()
            return False

        # Step 5: Clear photos
        self.clear_photos()

        # Step 6: Clean exports
        self.clean_old_exports()

        # Step 7: Clean queue
        self.clean_sync_queue()

        # Report
        self.print_report()
        self.save_report()

        self.log("All cleanup tasks completed successfully!", 'SUCCESS')
        return True


def main():
    """Main entry point"""
    try:
        cleanup = AutoCleanup()
        success = cleanup.run()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n❌ Cleanup interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
