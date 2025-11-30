#!/usr/bin/env python3
"""
Generate a sample signed URL for testing.
Usage: python scripts/generate_sample_link.py [student_number]
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth.url_signer import URLSigner

# Load environment variables manually (dotenv not required)
def load_env():
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

def main():
    # Get student number from command line or use default
    student_number = sys.argv[1] if len(sys.argv) > 1 else "2021001"
    
    # Get secret from environment
    secret = os.environ.get('URL_SIGNING_SECRET')
    if not secret:
        print("❌ Error: URL_SIGNING_SECRET not found in environment")
        print("Make sure .env file exists and contains URL_SIGNING_SECRET")
        return 1
    
    # Get base URL from config or use default
    base_url = "https://cerjho.github.io/IoT-Attendance-System/view-attendance.html"
    
    # Create signer and generate URL
    signer = URLSigner(secret)
    signed_url = signer.sign_url(base_url, student_number, expiry_hours=48)
    
    # Display results
    print("=" * 80)
    print("📱 SAMPLE SIGNED ATTENDANCE URL")
    print("=" * 80)
    print(f"\nStudent Number: {student_number}")
    print(f"Valid For: 48 hours")
    print(f"\n🔗 Full URL:")
    print(f"\n{signed_url}")
    print(f"\n📋 URL Components:")
    
    # Parse URL to show components
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(signed_url)
    params = parse_qs(parsed.query)
    
    print(f"  Base: {parsed.scheme}://{parsed.netloc}{parsed.path}")
    print(f"  Student ID: {params.get('student_id', [''])[0]}")
    print(f"  Expires: {params.get('expires', [''])[0]}")
    print(f"  Signature: {params.get('sig', [''])[0][:20]}...")
    
    print(f"\n✅ This URL can be sent via SMS to parents")
    print(f"   The signature ensures only authorized access")
    print(f"   URL expires in 48 hours from generation")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
