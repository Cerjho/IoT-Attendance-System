#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

echo "======================================================================"
echo "IoT ATTENDANCE SYSTEM - SETUP"
echo "======================================================================"
echo "Root: $ROOT_DIR"

# OS dependency hints
if command -v apt-get >/dev/null 2>&1; then
  echo "\nChecking OS dependencies (Debian/Raspberry Pi OS)..."
  MISSING=()
  for pkg in libzbar0 libatlas-base-dev; do
    dpkg -s "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
  done
  if (( ${#MISSING[@]} )); then
    echo "\nThe following OS packages are recommended:" 
    echo "  sudo apt-get update && sudo apt-get install -y ${MISSING[*]}"
  else
    echo "✓ OS dependencies present"
  fi
fi

# Python venv
if [[ ! -d "venv" ]]; then
  echo "\nCreating Python virtual environment..."
  python3 -m venv venv
fi
source venv/bin/activate
python -m pip install --upgrade pip

# Install Python dependencies
if [[ -f requirements.txt ]]; then
  echo "\nInstalling Python dependencies..."
  pip install -r requirements.txt
else
  echo "requirements.txt not found; skipping pip install"
fi

# Create runtime directories
mkdir -p data/photos data/qr_codes data/logs

# Summary
echo "\nSetup complete. Next steps:"
echo "  1) Create and fill .env (copy from .env.example)"
echo "  2) Run: bash scripts/start_attendance.sh --headless"
echo "======================================================================"