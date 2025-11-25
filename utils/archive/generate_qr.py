#!/usr/bin/env python3
"""
Generate QR codes for students
Creates QR code images that can be used for attendance
"""
import qrcode
import os
import sys

def generate_qr_codes(student_ids, output_dir='qr_codes'):
    """Generate QR codes for a list of student IDs"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("QR CODE GENERATOR")
    print('='*70)
    print(f"\nGenerating QR codes for {len(student_ids)} students...")
    print(f"Output directory: {output_dir}/\n")
    
    for student_id in student_ids:
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(student_id)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save image
        filename = f"{student_id}.png"
        filepath = os.path.join(output_dir, filename)
        img.save(filepath)
        
        print(f"  ✓ Generated: {filepath}")
    
    print(f"\n{'='*70}")
    print("QR CODES GENERATED SUCCESSFULLY")
    print('='*70)
    print(f"\nTotal: {len(student_ids)} QR codes")
    print(f"Location: {output_dir}/")
    print("\nUsage:")
    print("  1. Open the PNG files")
    print("  2. Display on screen or print")
    print("  3. Show to camera in attendance system")
    print('='*70 + '\n')


def generate_demo_students(count=10):
    """Generate demo student IDs"""
    return [f"STU{i:03d}" for i in range(1, count + 1)]


if __name__ == '__main__':
    # Check if student IDs provided as arguments
    if len(sys.argv) > 1:
        # Use provided IDs
        student_ids = sys.argv[1:]
        print(f"\nUsing provided student IDs: {', '.join(student_ids)}")
    else:
        # Generate demo IDs
        count = 10
        student_ids = generate_demo_students(count)
        print(f"\nNo student IDs provided. Generating {count} demo IDs...")
    
    # Generate QR codes
    generate_qr_codes(student_ids)
    
    print("\nYou can also specify custom student IDs:")
    print("  python generate_qr.py STU001 STU002 STU003")
    print("\nOr edit this file to add your student list.\n")
