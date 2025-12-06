#!/bin/bash
# Apply iot_devices permissions fix to Supabase
# Reads credentials from .env and applies the SQL migration

set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "❌ Error: .env file not found"
    exit 1
fi

# Check required variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo "❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env"
    exit 1
fi

echo "===================================================================="
echo "IoT DEVICES PERMISSION FIX"
echo "===================================================================="
echo ""
echo "This script will fix the 'permission denied for table iot_devices' error"
echo "by granting proper permissions to the enrichment trigger function."
echo ""

MIGRATION_FILE="supabase/migrations/20251206120000_fix_iot_devices_permissions.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Error: Migration file not found: $MIGRATION_FILE"
    exit 1
fi

echo "📝 Reading migration SQL..."
SQL_CONTENT=$(cat "$MIGRATION_FILE")

echo "🔧 Applying migration to Supabase..."
echo "   URL: $SUPABASE_URL"
echo ""

# Apply via Supabase SQL REST endpoint
# Note: This uses the /rest/v1/rpc endpoint to execute SQL
# Alternative: Use psql if connection string is available

# Method 1: Try direct SQL execution via service role
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${SUPABASE_URL}/rest/v1/rpc/query" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"query\": $(echo "$SQL_CONTENT" | jq -Rs .)}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo "✅ Migration applied successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Test attendance sync: python scripts/force_sync.py"
    echo "  2. Start the system: bash scripts/start_attendance.sh --headless"
    echo ""
else
    echo "⚠️  REST API method failed (this is expected - Supabase doesn't expose direct SQL execution)"
    echo "HTTP Code: $HTTP_CODE"
    echo ""
    echo "📋 MANUAL APPLICATION REQUIRED:"
    echo "===================================================================="
    echo ""
    echo "Please apply this SQL manually via Supabase Dashboard:"
    echo "  1. Go to: ${SUPABASE_URL%/}/project/_/sql"
    echo "  2. Create a new query"
    echo "  3. Copy the SQL from: $MIGRATION_FILE"
    echo "  4. Run the query"
    echo ""
    echo "Or use psql if you have the connection string:"
    echo "  psql \$DATABASE_URL -f $MIGRATION_FILE"
    echo ""
    echo "===================================================================="
    echo ""
    echo "📄 Migration file content:"
    echo "===================================================================="
    cat "$MIGRATION_FILE"
    echo "===================================================================="
fi
