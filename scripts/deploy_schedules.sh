#!/bin/bash
# Deploy school schedules table to Supabase

set -e

echo "======================================================================"
echo "📅 DEPLOYING SCHOOL SCHEDULES TABLE TO SUPABASE"
echo "======================================================================"
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ Error: .env file not found"
    exit 1
fi

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "❌ Error: psql is not installed"
    echo "   Install with: sudo apt-get install postgresql-client"
    exit 1
fi

# Check environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "❌ Error: SUPABASE_URL or SUPABASE_KEY not set in .env"
    exit 1
fi

# Extract database connection string from Supabase
# Note: You'll need the direct Postgres connection string from Supabase dashboard
# Format: postgresql://postgres:[password]@[host]:5432/postgres

echo "⚠️  This script requires direct Postgres connection string"
echo "   Get it from: Supabase Dashboard → Settings → Database"
echo ""
read -p "Enter Postgres connection string: " DB_CONNECTION_STRING

if [ -z "$DB_CONNECTION_STRING" ]; then
    echo "❌ Canceled"
    exit 1
fi

echo ""
echo "🔄 Applying migration..."
psql "$DB_CONNECTION_STRING" -f supabase/migrations/20251206150000_create_schedules_table.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================================"
    echo "✅ MIGRATION SUCCESSFUL"
    echo "======================================================================"
    echo ""
    echo "The school_schedules table has been created in Supabase with:"
    echo "  • Default schedule pre-populated"
    echo "  • Morning/afternoon session times"
    echo "  • Login/logout windows"
    echo "  • Late thresholds"
    echo "  • RLS policies enabled"
    echo ""
    echo "Next steps:"
    echo "  1. Test schedule sync:"
    echo "     python utils/test-scripts/test_schedule_sync.py"
    echo ""
    echo "  2. Start attendance system:"
    echo "     bash scripts/start_attendance.sh --headless"
    echo ""
    echo "  3. Manage schedules in Supabase dashboard:"
    echo "     • Update default schedule times"
    echo "     • Create additional schedules for different sections"
    echo "     • Assign schedules to specific sections"
    echo ""
    echo "======================================================================"
else
    echo ""
    echo "❌ Migration failed"
    exit 1
fi
