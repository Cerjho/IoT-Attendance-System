#!/usr/bin/env python3
"""
Deploy Server-Side Configuration Migration
Executes SQL migration via Supabase SQL API
"""

import os
import sys
import requests
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', SUPABASE_KEY)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)

# Read migration file
migration_file = Path(__file__).parent.parent / 'supabase/migrations/20251207000000_server_side_config.sql'
if not migration_file.exists():
    print(f"❌ Migration file not found: {migration_file}")
    sys.exit(1)

sql_content = migration_file.read_text()

print("╔═══════════════════════════════════════════════════════════════════╗")
print("║     Deploying Server-Side Configuration Migration                ║")
print("╚═══════════════════════════════════════════════════════════════════╝")
print()
print(f"📄 Migration: {migration_file.name}")
print(f"📏 Size: {len(sql_content)} characters")
print()

# Try to execute via Supabase REST API using query endpoint
# Note: This may not work for all SQL statements via REST API
# The best way is via Supabase Dashboard SQL Editor or CLI

print("⚠️  Note: Direct SQL execution via REST API has limitations.")
print("   For complex migrations, use Supabase Dashboard SQL Editor:")
print(f"   → https://supabase.com/dashboard/project/_/sql")
print()
print("   OR use Supabase CLI:")
print("   → supabase db push")
print()

# Alternative: Execute individual statements via REST API
# Split SQL into individual statements
statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

print(f"📊 Found {len(statements)} SQL statements")
print()

# Try to execute via direct PostgreSQL query (if service role key available)
print("🔧 Attempting to execute migration...")
print()

headers = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json"
}

# Use the query endpoint (if available)
# Note: This endpoint may require service role key and may not be available in all Supabase plans
query_url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"

# Alternative: Try to execute via db/query endpoint
db_query_url = f"{SUPABASE_URL}/rest/v1/rpc/sql"

# Since direct SQL execution isn't available via REST API for DDL statements,
# we'll provide the SQL for manual execution

print("⚠️  Automatic execution not available.")
print("   Please execute the SQL manually using one of these methods:")
print()
print("Method 1: Copy SQL to clipboard and paste in Supabase Dashboard")
print("─" * 70)
print()
print(sql_content[:500] + "...")
print()
print(f"[...{len(sql_content) - 500} more characters...]")
print()
print("─" * 70)
print()
print("Method 2: Use psql if you have database credentials")
print("─" * 70)
print(f"cat {migration_file} | psql <your_connection_string>")
print()

# Save to a temp file for easy copying
temp_file = Path('/tmp/supabase_migration.sql')
temp_file.write_text(sql_content)
print(f"✓ SQL saved to: {temp_file}")
print()

print("Method 3: Execute via Supabase Dashboard SQL Editor")
print("─" * 70)
print(f"1. Go to: {SUPABASE_URL.replace('https://', 'https://supabase.com/dashboard/project/')}/sql")
print(f"2. Copy SQL from: {temp_file}")
print("3. Paste and click 'Run'")
print()

print("╔═══════════════════════════════════════════════════════════════════╗")
print("║  After deployment, restart the service:                           ║")
print("║  sudo systemctl restart attendance-system.service                 ║")
print("╚═══════════════════════════════════════════════════════════════════╝")
