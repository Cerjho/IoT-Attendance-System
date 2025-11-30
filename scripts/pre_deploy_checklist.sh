#!/bin/bash
#
# Pre-deployment Checklist Runner
# Validates all requirements before production deployment
#

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          PRODUCTION DEPLOYMENT CHECKLIST                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")/.."

# Helper function
check_item() {
    local description="$1"
    local command="$2"
    
    echo -n "[ ] $description..."
    if eval "$command" >/dev/null 2>&1; then
        echo -e "\r[✓] $description"
        return 0
    else
        echo -e "\r[✗] $description"
        return 1
    fi
}

echo "🔐 SECURITY:"
check_item "Environment file exists                    " "test -f .env"
check_item "Environment file permissions (600)         " "test \$(stat -c %a .env) = '600'"
check_item "URL signing secret configured              " "grep -q '^URL_SIGNING_SECRET=' .env"
check_item "Dashboard API key configured               " "grep -q '^DASHBOARD_API_KEY=' .env"
check_item ".env in gitignore                          " "git check-ignore .env"

echo ""
echo "⚙️  CONFIGURATION:"
check_item "Config file exists                         " "test -f config/config.json"
check_item "Defaults file exists                       " "test -f config/defaults.json"
check_item "Dashboard auth enabled                     " "grep -q '\"auth_enabled\".*:.*true' config/config.json"
check_item "Signed URLs enabled                        " "grep -q '\"use_signed_urls\".*:.*true' config/config.json"
check_item "Config uses placeholders (secure)          " "grep -q '\${SUPABASE_URL}' config/config.json"

echo ""
echo "🧪 TESTING:"
check_item "Python dependencies installed              " "python3 -c 'import cv2, requests'"
check_item "Signed URL tests pass                      " "python3 tests/test_signed_urls.py"
check_item "Config loads successfully                  " "python3 -c 'from src.utils.config_loader import ConfigLoader; ConfigLoader(\"config/config.json\")'"

echo ""
echo "🖥️  SERVICES:"
check_item "Dashboard service running                  " "systemctl is-active --quiet attendance-dashboard"
check_item "Dashboard service enabled (auto-start)     " "systemctl is-enabled --quiet attendance-dashboard"

echo ""
echo "🌐 CONNECTIVITY:"
check_item "Dashboard API responding                   " "curl -s http://localhost:8080/health"
check_item "Internet connectivity                      " "ping -c 1 -W 2 8.8.8.8"

echo ""
echo "💾 FILESYSTEM:"
check_item "Database file exists                       " "test -f data/attendance.db"
check_item "Data directory exists                      " "test -d data"
check_item "Logs directory exists                      " "test -d data/logs"
check_item "Photos directory exists                    " "test -d data/photos"
check_item "Sufficient disk space (>1GB free)          " "test \$(df --output=avail . | tail -1) -gt 1000000"

echo ""
echo "📋 SCRIPTS:"
check_item "Deploy script executable                   " "test -x scripts/deploy_production.sh"
check_item "Production check executable                " "test -x scripts/production_check.sh"
check_item "Monitor script executable                  " "test -x scripts/monitor.py"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ Run full check:  bash scripts/production_check.sh             ║"
echo "║ Deploy system:    sudo bash scripts/deploy_production.sh      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
