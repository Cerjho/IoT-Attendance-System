#!/usr/bin/env python3
"""
Generate QR Codes for Test Students

Creates QR codes for all sample students so you can test scanning.
QR codes are saved to data/qr_codes/
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import qrcode
from PIL import Image, ImageDraw, ImageFont

# Test student numbers
STUDENTS = [
    {'number': '2021001', 'name': 'Juan Dela Cruz', 'schedule': 'Morning'},
    {'number': '2021002', 'name': 'Maria Santos', 'schedule': 'Morning'},
    {'number': '2021003', 'name': 'Pedro Reyes', 'schedule': 'Morning'},
    {'number': '2021004', 'name': 'Ana Lopez', 'schedule': 'Afternoon'},
    {'number': '2021005', 'name': 'Carlos Ramos', 'schedule': 'Afternoon'},
    {'number': '2021006', 'name': 'Lisa Fernandez', 'schedule': 'Both Sessions'},
    {'number': '2021007', 'name': 'Mark Gonzales', 'schedule': 'Both Sessions'},
    {'number': 'STU001', 'name': 'Test Student One', 'schedule': 'Flexible'},
    {'number': 'STU002', 'name': 'Test Student Two', 'schedule': 'Flexible'},
    {'number': '221566', 'name': 'Sample Student', 'schedule': 'Flexible'},
    {'number': '171770', 'name': 'Demo Student', 'schedule': 'Flexible'},
]

def create_qr_with_label(student_number, student_name, schedule, output_dir):
    """Create QR code with student info label."""
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(student_number)
    qr.make(fit=True)
    
    # Create QR image
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_width, qr_height = qr_img.size
    
    # Create canvas with extra space for text
    label_height = 120
    total_height = qr_height + label_height
    canvas = Image.new('RGB', (qr_width, total_height), 'white')
    
    # Paste QR code
    canvas.paste(qr_img, (0, 0))
    
    # Add text labels
    draw = ImageDraw.Draw(canvas)
    
    try:
        # Try to use a nice font
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        # Fallback to default font
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Student number (large, bold)
    text = student_number
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    x = (qr_width - text_width) // 2
    y = qr_height + 10
    draw.text((x, y), text, fill='black', font=font_large)
    
    # Student name
    text = student_name
    bbox = draw.textbbox((0, 0), text, font=font_medium)
    text_width = bbox[2] - bbox[0]
    x = (qr_width - text_width) // 2
    y = qr_height + 45
    draw.text((x, y), text, fill='black', font=font_medium)
    
    # Schedule
    text = f"Schedule: {schedule}"
    bbox = draw.textbbox((0, 0), text, font=font_small)
    text_width = bbox[2] - bbox[0]
    x = (qr_width - text_width) // 2
    y = qr_height + 75
    draw.text((x, y), text, fill='gray', font=font_small)
    
    # Save
    output_path = output_dir / f"qr_{student_number}.png"
    canvas.save(output_path, 'PNG')
    
    return output_path


def main():
    """Generate all QR codes."""
    
    print("=" * 70)
    print("QR Code Generator for Test Students")
    print("=" * 70)
    print()
    
    # Create output directory
    output_dir = Path('data/qr_codes')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directory: {output_dir}")
    print(f"📊 Generating {len(STUDENTS)} QR codes...")
    print()
    
    # Generate QR codes
    generated = []
    for student in STUDENTS:
        try:
            output_path = create_qr_with_label(
                student['number'],
                student['name'],
                student['schedule'],
                output_dir
            )
            generated.append(output_path)
            print(f"✅ {student['number']:<10} - {student['name']:<25} ({student['schedule']})")
        except Exception as e:
            print(f"❌ {student['number']:<10} - Error: {e}")
    
    print()
    print("=" * 70)
    print(f"✅ Generated {len(generated)}/{len(STUDENTS)} QR codes")
    print(f"📁 Location: {output_dir.absolute()}")
    print()
    print("🔍 To test scanning:")
    print("   1. Print the QR codes or display them on another device")
    print("   2. Hold QR code in front of camera")
    print("   3. System will validate against today's roster")
    print()
    print("📋 Test Scenarios:")
    print("   • Morning students (2021001-2021003): Should work 7 AM - 12 PM")
    print("   • Afternoon students (2021004-2021005): Should work 1 PM - 6 PM")
    print("   • Both sessions (2021006-2021007): Should work 7 AM - 6 PM")
    print("   • Flexible (STU001, STU002, etc.): Should work anytime")
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()
