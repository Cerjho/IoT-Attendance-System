#!/usr/bin/env python3
"""
Assign Schedules to Sections

Utility script to assign school_schedules to sections in Supabase.
Supports:
- Assigning default schedule to all sections
- Assigning specific schedules to named sections
- Bulk assignment by pattern matching
"""

import os
import sys
import requests
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.logging_factory import get_logger
from src.utils.audit_logger import get_audit_logger
from dotenv import load_dotenv

logger = get_logger(__name__)
audit_logger = get_audit_logger()

# Load environment variables
load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}


def get_schedules() -> List[Dict]:
    """Fetch all schedules from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/school_schedules"
    params = {"select": "id,name,is_default,status"}
    
    response = requests.get(url, params=params, headers=HEADERS, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to fetch schedules: {response.status_code}")
        print(response.text)
        return []


def get_sections(section_code: Optional[str] = None) -> List[Dict]:
    """
    Fetch sections from Supabase.
    
    Args:
        section_code: Optional section code filter
    """
    url = f"{SUPABASE_URL}/rest/v1/sections"
    params = {"select": "id,section_code,section_name,schedule_id"}
    
    if section_code:
        params["section_code"] = f"eq.{section_code}"
    
    response = requests.get(url, params=params, headers=HEADERS, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to fetch sections: {response.status_code}")
        print(response.text)
        return []


def assign_schedule_to_section(section_id: str, schedule_id: str) -> bool:
    """
    Assign schedule to a section.
    
    Args:
        section_id: Section UUID
        schedule_id: Schedule UUID
    
    Returns:
        True if successful
    """
    url = f"{SUPABASE_URL}/rest/v1/sections"
    params = {"id": f"eq.{section_id}"}
    payload = {"schedule_id": schedule_id}
    
    response = requests.patch(url, params=params, json=payload, headers=HEADERS, timeout=10)
    
    return response.status_code == 200


def assign_default_schedule_to_all() -> int:
    """
    Assign default schedule to all sections without a schedule.
    
    Returns:
        Number of sections updated
    """
    # Get default schedule
    schedules = get_schedules()
    default_schedule = next((s for s in schedules if s.get('is_default')), None)
    
    if not default_schedule:
        print("❌ No default schedule found")
        return 0
    
    print(f"✓ Found default schedule: {default_schedule['name']} ({default_schedule['id']})")
    
    # Get sections without schedule
    sections = get_sections()
    sections_to_update = [s for s in sections if not s.get('schedule_id')]
    
    if not sections_to_update:
        print("✓ All sections already have schedules assigned")
        return 0
    
    print(f"→ Assigning to {len(sections_to_update)} sections...")
    
    updated = 0
    for section in sections_to_update:
        if assign_schedule_to_section(section['id'], default_schedule['id']):
            print(f"  ✓ {section['section_code']}: {section['section_name']}")
            updated += 1
        else:
            print(f"  ✗ {section['section_code']}: Failed")
    
    return updated


def assign_schedule_by_pattern(pattern: str, schedule_name: str) -> int:
    """
    Assign schedule to sections matching a pattern.
    
    Args:
        pattern: Pattern to match in section_code (e.g., 'STEM', '11-')
        schedule_name: Name of schedule to assign
    
    Returns:
        Number of sections updated
    """
    # Get schedule by name
    schedules = get_schedules()
    schedule = next((s for s in schedules if s['name'].lower() == schedule_name.lower()), None)
    
    if not schedule:
        print(f"❌ Schedule not found: {schedule_name}")
        return 0
    
    print(f"✓ Found schedule: {schedule['name']} ({schedule['id']})")
    
    # Get all sections
    sections = get_sections()
    matching_sections = [s for s in sections if pattern.lower() in s['section_code'].lower()]
    
    if not matching_sections:
        print(f"❌ No sections match pattern: {pattern}")
        return 0
    
    print(f"→ Assigning to {len(matching_sections)} sections matching '{pattern}'...")
    
    updated = 0
    for section in matching_sections:
        if assign_schedule_to_section(section['id'], schedule['id']):
            print(f"  ✓ {section['section_code']}: {section['section_name']}")
            updated += 1
        else:
            print(f"  ✗ {section['section_code']}: Failed")
    
    return updated


def assign_schedule_to_specific_sections(section_codes: List[str], schedule_name: str) -> int:
    """
    Assign schedule to specific sections.
    
    Args:
        section_codes: List of section codes
        schedule_name: Name of schedule to assign
    
    Returns:
        Number of sections updated
    """
    # Get schedule by name
    schedules = get_schedules()
    schedule = next((s for s in schedules if s['name'].lower() == schedule_name.lower()), None)
    
    if not schedule:
        print(f"❌ Schedule not found: {schedule_name}")
        return 0
    
    print(f"✓ Found schedule: {schedule['name']} ({schedule['id']})")
    
    updated = 0
    for section_code in section_codes:
        sections = get_sections(section_code)
        
        if not sections:
            print(f"  ✗ {section_code}: Not found")
            continue
        
        section = sections[0]
        if assign_schedule_to_section(section['id'], schedule['id']):
            print(f"  ✓ {section_code}: {section['section_name']}")
            updated += 1
        else:
            print(f"  ✗ {section_code}: Failed")
    
    return updated


def show_current_assignments():
    """Display current schedule assignments."""
    sections = get_sections()
    schedules = get_schedules()
    
    # Build schedule lookup
    schedule_map = {s['id']: s['name'] for s in schedules}
    
    print("\n╔══════════════════════════════════════════════════════════════════════╗")
    print("║                   Current Schedule Assignments                       ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    # Group by schedule
    by_schedule = {}
    no_schedule = []
    
    for section in sections:
        schedule_id = section.get('schedule_id')
        if schedule_id:
            schedule_name = schedule_map.get(schedule_id, 'Unknown')
            if schedule_name not in by_schedule:
                by_schedule[schedule_name] = []
            by_schedule[schedule_name].append(section)
        else:
            no_schedule.append(section)
    
    # Display assignments
    for schedule_name, sects in sorted(by_schedule.items()):
        print(f"📅 {schedule_name}:")
        for section in sorted(sects, key=lambda s: s['section_code']):
            print(f"   • {section['section_code']}: {section['section_name']}")
        print()
    
    if no_schedule:
        print("❌ No Schedule Assigned:")
        for section in sorted(no_schedule, key=lambda s: s['section_code']):
            print(f"   • {section['section_code']}: {section['section_name']}")
        print()
    
    # Summary
    print(f"Total: {len(sections)} sections, {len(no_schedule)} without schedule")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Assign schedules to sections in Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current assignments
  python scripts/assign_schedules.py --show

  # Assign default schedule to all sections without one
  python scripts/assign_schedules.py --default-all

  # Assign specific schedule to sections matching pattern
  python scripts/assign_schedules.py --pattern "STEM" --schedule "Morning Only"

  # Assign schedule to specific sections
  python scripts/assign_schedules.py --sections "11-STEM-A" "11-STEM-B" --schedule "Morning Only"
        """
    )
    
    parser.add_argument('--show', action='store_true', help='Show current assignments')
    parser.add_argument('--default-all', action='store_true', help='Assign default schedule to all')
    parser.add_argument('--pattern', type=str, help='Section code pattern to match')
    parser.add_argument('--sections', nargs='+', help='Specific section codes')
    parser.add_argument('--schedule', type=str, help='Schedule name to assign')
    
    args = parser.parse_args()
    
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                     Schedule Assignment Tool                         ║")
    print("╚══════════════════════════════════════════════════════════════════════╝\n")
    
    # Show current assignments
    if args.show or len(sys.argv) == 1:
        show_current_assignments()
        return
    
    # Assign default to all
    if args.default_all:
        updated = assign_default_schedule_to_all()
        print(f"\n✅ Updated {updated} sections with default schedule")
        return
    
    # Assign by pattern
    if args.pattern:
        if not args.schedule:
            print("❌ Error: --schedule required with --pattern")
            sys.exit(1)
        updated = assign_schedule_by_pattern(args.pattern, args.schedule)
        print(f"\n✅ Updated {updated} sections")
        return
    
    # Assign to specific sections
    if args.sections:
        if not args.schedule:
            print("❌ Error: --schedule required with --sections")
            sys.exit(1)
        updated = assign_schedule_to_specific_sections(args.sections, args.schedule)
        print(f"\n✅ Updated {updated} sections")
        return
    
    # No action specified
    parser.print_help()


if __name__ == '__main__':
    main()
