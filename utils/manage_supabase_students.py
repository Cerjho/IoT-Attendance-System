#!/usr/bin/env python3
"""
Student Management Script for Supabase
Helps add/update/list students in Supabase primary database
"""

import sys
import os
import argparse
import requests
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from src.utils import load_config


class SupabaseStudentManager:
    """Manage students in Supabase database"""
    
    def __init__(self, config):
        self.supabase_url = config.get('url')
        self.supabase_key = config.get('api_key')
        self.headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def add_student(self, student_id, name=None, email=None, parent_phone=None):
        """Add a new student to Supabase"""
        url = f"{self.supabase_url}/rest/v1/students"
        
        data = {
            'student_id': student_id,
            'name': name,
            'email': email,
            'parent_phone': parent_phone,
            'status': 'active'
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                print(f"✅ Student {student_id} added successfully")
                return True
            else:
                print(f"❌ Failed to add student: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
        
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def update_student(self, student_id, name=None, email=None, parent_phone=None):
        """Update existing student in Supabase"""
        url = f"{self.supabase_url}/rest/v1/students"
        
        data = {}
        if name: data['name'] = name
        if email: data['email'] = email
        if parent_phone: data['parent_phone'] = parent_phone
        
        try:
            response = requests.patch(
                f"{url}?student_id=eq.{student_id}",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                print(f"✅ Student {student_id} updated successfully")
                return True
            else:
                print(f"❌ Failed to update student: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def list_students(self, limit=50):
        """List students from Supabase"""
        url = f"{self.supabase_url}/rest/v1/students"
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={'limit': limit, 'order': 'student_id'}
            )
            
            if response.status_code == 200:
                students = response.json()
                return students
            else:
                print(f"❌ Failed to fetch students: {response.status_code}")
                return []
        
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def delete_student(self, student_id):
        """Delete student from Supabase"""
        url = f"{self.supabase_url}/rest/v1/students?student_id=eq.{student_id}"
        
        try:
            response = requests.delete(url, headers=self.headers)
            
            if response.status_code == 204:
                print(f"✅ Student {student_id} deleted successfully")
                return True
            else:
                print(f"❌ Failed to delete student: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def import_from_csv(self, csv_file):
        """Import students from CSV file"""
        import csv
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    student_id = row.get('student_id')
                    name = row.get('name')
                    email = row.get('email')
                    parent_phone = row.get('parent_phone')
                    
                    if student_id:
                        if self.add_student(student_id, name, email, parent_phone):
                            count += 1
                
                print(f"\n✅ Imported {count} students from {csv_file}")
                return True
        
        except Exception as e:
            print(f"❌ Error importing CSV: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Manage students in Supabase database')
    parser.add_argument('--add', metavar='STUDENT_ID', help='Add a new student')
    parser.add_argument('--name', help='Student name')
    parser.add_argument('--email', help='Student email')
    parser.add_argument('--phone', help='Parent phone number')
    parser.add_argument('--update', metavar='STUDENT_ID', help='Update existing student')
    parser.add_argument('--delete', metavar='STUDENT_ID', help='Delete a student')
    parser.add_argument('--list', action='store_true', help='List all students')
    parser.add_argument('--limit', type=int, default=50, help='Limit for list (default: 50)')
    parser.add_argument('--import-csv', metavar='FILE', help='Import students from CSV file')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config('config/config.json')
    cloud_config = config.get('cloud', {})
    
    if not cloud_config.get('enabled'):
        print("❌ Cloud sync is disabled in configuration")
        return
    
    # Initialize manager
    manager = SupabaseStudentManager(cloud_config)
    
    # Execute command
    if args.add:
        manager.add_student(args.add, args.name, args.email, args.phone)
    
    elif args.update:
        manager.update_student(args.update, args.name, args.email, args.phone)
    
    elif args.delete:
        confirm = input(f"Are you sure you want to delete student {args.delete}? (y/N): ")
        if confirm.lower() == 'y':
            manager.delete_student(args.delete)
    
    elif args.list:
        print(f"\n{'='*80}")
        print(f"Students in Supabase (limit: {args.limit})")
        print(f"{'='*80}\n")
        
        students = manager.list_students(args.limit)
        
        if students:
            for i, student in enumerate(students, 1):
                print(f"{i}. ID: {student.get('student_id')}")
                print(f"   Name: {student.get('name', 'N/A')}")
                print(f"   Email: {student.get('email', 'N/A')}")
                print(f"   Phone: {student.get('parent_phone', 'N/A')}")
                print(f"   Status: {student.get('status', 'N/A')}")
                print()
            
            print(f"Total: {len(students)} students")
        else:
            print("No students found")
        
        print(f"\n{'='*80}\n")
    
    elif args.import_csv:
        manager.import_from_csv(args.import_csv)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
