#!/usr/bin/env python3
"""
Utility script to manage parent phone numbers for students
Allows adding/updating/viewing parent contact information
"""
import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import AttendanceDatabase
from src.utils import load_config


def add_parent_phone(db: AttendanceDatabase, student_id: str, parent_phone: str, name: str = None):
    """Add or update parent phone for a student"""
    # Check if student exists
    student = db.get_student(student_id)
    
    if student:
        # Update existing student
        success = db.add_student(student_id, student.get('name') or name, student.get('email'), parent_phone)
        if success:
            print(f"✓ Updated parent phone for student {student_id}: {parent_phone}")
            return True
        else:
            print(f"✗ Failed to update student {student_id}")
            return False
    else:
        # Create new student
        success = db.add_student(student_id, name, None, parent_phone)
        if success:
            print(f"✓ Created new student {student_id} with parent phone: {parent_phone}")
            return True
        else:
            print(f"✗ Failed to create student {student_id}")
            return False


def view_students(db: AttendanceDatabase, show_all: bool = False):
    """View all students and their parent phone numbers"""
    import sqlite3
    
    try:
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if show_all:
            cursor.execute('SELECT * FROM students ORDER BY student_id')
        else:
            cursor.execute('SELECT * FROM students WHERE parent_phone IS NOT NULL ORDER BY student_id')
        
        students = cursor.fetchall()
        conn.close()
        
        if not students:
            print("\nNo students found in database.")
            return
        
        print("\n" + "="*80)
        print(f"{'Student ID':<15} {'Name':<20} {'Parent Phone':<20} {'Email':<25}")
        print("="*80)
        
        for student in students:
            print(f"{student['student_id']:<15} "
                  f"{student['name'] or 'N/A':<20} "
                  f"{student['parent_phone'] or 'N/A':<20} "
                  f"{student['email'] or 'N/A':<25}")
        
        print("="*80)
        print(f"Total: {len(students)} student(s)")
        if not show_all:
            print("(Showing only students with parent phone numbers. Use --all to show all students)")
        print()
    
    except Exception as e:
        print(f"Error viewing students: {str(e)}")


def import_from_csv(db: AttendanceDatabase, csv_file: str):
    """Import parent phone numbers from CSV file"""
    import csv
    
    if not os.path.exists(csv_file):
        print(f"✗ File not found: {csv_file}")
        return False
    
    try:
        count_success = 0
        count_failed = 0
        
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            # Check required columns
            if 'student_id' not in reader.fieldnames or 'parent_phone' not in reader.fieldnames:
                print("✗ CSV file must have 'student_id' and 'parent_phone' columns")
                print(f"  Found columns: {', '.join(reader.fieldnames)}")
                return False
            
            for row in reader:
                student_id = row.get('student_id', '').strip()
                parent_phone = row.get('parent_phone', '').strip()
                name = row.get('name', '').strip() or None
                
                if not student_id or not parent_phone:
                    print(f"⚠ Skipping row with missing data: {row}")
                    count_failed += 1
                    continue
                
                if add_parent_phone(db, student_id, parent_phone, name):
                    count_success += 1
                else:
                    count_failed += 1
        
        print(f"\n{'='*80}")
        print(f"Import complete: {count_success} succeeded, {count_failed} failed")
        print(f"{'='*80}\n")
        return True
    
    except Exception as e:
        print(f"Error importing CSV: {str(e)}")
        return False


def export_to_csv(db: AttendanceDatabase, output_file: str = None):
    """Export students to CSV file"""
    import sqlite3
    import csv
    
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"students_export_{timestamp}.csv"
    
    try:
        conn = sqlite3.connect(db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM students ORDER BY student_id')
        students = cursor.fetchall()
        conn.close()
        
        if not students:
            print("No students to export.")
            return False
        
        with open(output_file, 'w', newline='') as f:
            fieldnames = ['student_id', 'name', 'parent_phone', 'email', 'created_at']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for student in students:
                writer.writerow(dict(student))
        
        print(f"✓ Exported {len(students)} students to: {output_file}")
        return True
    
    except Exception as e:
        print(f"Error exporting CSV: {str(e)}")
        return False


def test_sms(config_path: str = None, phone_number: str = None):
    """Test SMS notification system"""
    from src.notifications import SMSNotifier
    
    config = load_config(config_path or 'config/config.json')
    sms_config = config.get('sms_notifications', {})
    
    notifier = SMSNotifier(sms_config)
    
    print("\n" + "="*80)
    print("SMS Notification Test")
    print("="*80)
    
    # Test connection
    print("\n1. Testing SMS Gateway connection...")
    result = notifier.test_connection()
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}")
    
    if result['status'] != 'success':
        print("\n✗ Connection test failed. Please check your configuration.")
        return False
    
    # Send test SMS if phone number provided
    if phone_number:
        print(f"\n2. Sending test SMS to {phone_number}...")
        success = notifier.send_attendance_notification(
            student_id='TEST001',
            student_name='Test Student',
            parent_phone=phone_number,
            timestamp=datetime.now()
        )
        
        if success:
            print("   ✓ Test SMS sent successfully!")
        else:
            print("   ✗ Failed to send test SMS")
        
        print("\n" + "="*80 + "\n")
        return success
    else:
        print("\n✓ Connection test successful!")
        print("   Use --phone <number> to send a test SMS")
        print("\n" + "="*80 + "\n")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Manage parent phone numbers for attendance system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View students with parent phone numbers
  python manage_parents.py --view
  
  # View all students
  python manage_parents.py --view --all
  
  # Add/update parent phone for a student
  python manage_parents.py --add STU001 +1234567890 --name "John Doe"
  
  # Import from CSV file
  python manage_parents.py --import students.csv
  
  # Export to CSV file
  python manage_parents.py --export
  
  # Test SMS notification system
  python manage_parents.py --test-sms
  
  # Send test SMS
  python manage_parents.py --test-sms --phone +1234567890

CSV Format (for import):
  student_id,name,parent_phone
  STU001,John Doe,+1234567890
  STU002,Jane Smith,+1987654321
        """
    )
    
    parser.add_argument('--view', action='store_true', 
                       help='View students and their parent phone numbers')
    parser.add_argument('--all', action='store_true',
                       help='Show all students (including those without parent phones)')
    parser.add_argument('--add', nargs=2, metavar=('STUDENT_ID', 'PHONE'),
                       help='Add/update parent phone for a student')
    parser.add_argument('--name', type=str,
                       help='Student name (optional, used with --add)')
    parser.add_argument('--import', dest='import_csv', metavar='FILE',
                       help='Import parent phones from CSV file')
    parser.add_argument('--export', nargs='?', const=True, metavar='FILE',
                       help='Export students to CSV file')
    parser.add_argument('--test-sms', action='store_true',
                       help='Test SMS notification system')
    parser.add_argument('--phone', type=str,
                       help='Phone number for test SMS (use with --test-sms)')
    parser.add_argument('--db', type=str, default='data/attendance.db',
                       help='Database path (default: data/attendance.db)')
    parser.add_argument('--config', type=str, default='config/config.json',
                       help='Config file path (default: config/config.json)')
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # Handle test-sms separately (doesn't need database)
    if args.test_sms:
        test_sms(args.config, args.phone)
        return
    
    # Initialize database for other operations
    db = AttendanceDatabase(args.db)
    
    # Handle commands
    if args.view:
        view_students(db, args.all)
    
    elif args.add:
        student_id, parent_phone = args.add
        add_parent_phone(db, student_id, parent_phone, args.name)
    
    elif args.import_csv:
        import_from_csv(db, args.import_csv)
    
    elif args.export:
        if args.export is True:
            export_to_csv(db)
        else:
            export_to_csv(db, args.export)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
