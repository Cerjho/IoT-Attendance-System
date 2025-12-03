#!/bin/bash
# Start Real-time Monitoring Dashboard
# Displays live system status, events, and metrics

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   IoT Attendance - Real-time Dashboard        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check if virtual environment exists
if [ -d ".venv" ]; then
    VENV_DIR=".venv"
elif [ -d "venv" ]; then
    VENV_DIR="venv"
else
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo -e "${YELLOW}Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo -e "${BLUE}🔐 Loading environment variables...${NC}"
    export $(grep -v '^#' .env | xargs)
fi

# Get port from argument or use default
PORT="${1:-8888}"

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port $PORT is already in use${NC}"
    echo -e "${YELLOW}Try a different port: ./start_monitor.sh <port>${NC}"
    exit 1
fi

# Ensure logs directory exists
mkdir -p data/logs

echo -e "${GREEN}✅ Starting real-time monitoring dashboard...${NC}"
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Access Dashboard:                             ║${NC}"
echo -e "${BLUE}║  ${GREEN}http://localhost:$PORT/dashboard${BLUE}                 ║${NC}"
echo -e "${BLUE}║                                                ║${NC}"
echo -e "${BLUE}║  API Endpoints:                                ║${NC}"
echo -e "${BLUE}║  • /api/status  - Complete dashboard data     ║${NC}"
echo -e "${BLUE}║  • /api/metrics - Current metrics             ║${NC}"
echo -e "${BLUE}║  • /api/events  - Recent events               ║${NC}"
echo -e "${BLUE}║  • /api/alerts  - Recent alerts               ║${NC}"
echo -e "${BLUE}║  • /api/stream  - Real-time event stream      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Start dashboard
python scripts/realtime_dashboard.py $PORT
