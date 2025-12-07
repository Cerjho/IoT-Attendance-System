#!/bin/bash

# Deploy server-side configuration migration to Supabase
# This script deploys sms_templates and notification_preferences tables

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Deploy Server-Side Configuration Migration                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}✓${NC} Loading environment variables from .env"
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
else
    echo -e "${RED}✗${NC} .env file not found"
    exit 1
fi

# Check required environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_KEY" ]; then
    echo -e "${RED}✗${NC} Missing required environment variables:"
    echo "  - SUPABASE_URL"
    echo "  - SUPABASE_KEY"
    exit 1
fi

echo -e "${GREEN}✓${NC} Environment variables loaded"
echo ""

# Migration file
MIGRATION_FILE="$PROJECT_ROOT/supabase/migrations/20251207000000_server_side_config.sql"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo -e "${RED}✗${NC} Migration file not found: $MIGRATION_FILE"
    exit 1
fi

echo -e "${BLUE}📄 Migration file:${NC} $(basename $MIGRATION_FILE)"
echo ""

# Read SQL file
SQL_CONTENT=$(cat "$MIGRATION_FILE")

# Function to execute SQL
execute_sql() {
    local sql="$1"
    local description="$2"
    
    echo -e "${YELLOW}→${NC} $description"
    
    # Use psql if available, otherwise use Supabase REST API
    if command -v psql &> /dev/null; then
        # Extract database URL from SUPABASE_URL
        DB_HOST=$(echo "$SUPABASE_URL" | sed -E 's|https://([^.]+)\.supabase\.co.*|db.\1.supabase.co|')
        
        # Try to execute with psql (may need password)
        echo "$sql" | psql "postgresql://postgres:[password]@$DB_HOST:5432/postgres" 2>/dev/null || {
            echo -e "${YELLOW}  Note: psql execution failed, use Supabase Dashboard SQL Editor${NC}"
            return 1
        }
    else
        echo -e "${YELLOW}  Note: psql not available, use Supabase Dashboard SQL Editor${NC}"
        return 1
    fi
}

# Try to execute the migration
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Executing migration...${NC}"
echo ""

# Since we typically don't have direct psql access, provide instructions
echo -e "${YELLOW}⚠  Direct SQL execution requires database credentials.${NC}"
echo -e "${YELLOW}   Please deploy manually using one of these methods:${NC}"
echo ""
echo -e "${BLUE}Method 1: Supabase Dashboard${NC}"
echo "  1. Go to: $SUPABASE_URL/project/_/sql"
echo "  2. Click 'New Query'"
echo "  3. Copy the SQL from: $MIGRATION_FILE"
echo "  4. Click 'Run'"
echo ""
echo -e "${BLUE}Method 2: Supabase CLI (if installed)${NC}"
echo "  supabase db push"
echo ""
echo -e "${BLUE}Method 3: Copy SQL for manual execution${NC}"
echo "  cat $MIGRATION_FILE | pbcopy  # macOS"
echo "  cat $MIGRATION_FILE | xclip -selection clipboard  # Linux"
echo ""

# Verification queries
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}After deployment, verify with these queries:${NC}"
echo ""

cat << 'SQL'
-- 1. Check SMS templates table
SELECT template_type, template_name, is_active 
FROM sms_templates 
ORDER BY template_type;

-- 2. Verify 8 templates exist
SELECT COUNT(*) as template_count FROM sms_templates;

-- 3. Check notification preferences table structure
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'notification_preferences';

-- 4. Test get_sms_template function
SELECT * FROM get_sms_template('check_in');

-- 5. Test should_send_notification function
SELECT should_send_notification(
    '+1234567890',
    '00000000-0000-0000-0000-000000000001'::uuid,
    'check_in'
);
SQL

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}REST API Test (after deployment):${NC}"
echo ""

cat << 'BASH_EOF'
# Test get_sms_template RPC
curl -X POST "${SUPABASE_URL}/rest/v1/rpc/get_sms_template" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"template_type_param": "check_in"}'

# Expected output: JSON with template_type, message_template, variables
BASH_EOF

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Deployment instructions provided${NC}"
echo -e "${GREEN}✓ Run verification queries after manual deployment${NC}"
echo ""
