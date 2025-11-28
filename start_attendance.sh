#!/usr/bin/env bash
# Shim launcher to keep compatibility with tests expecting this file at repo root
# Delegates to scripts/start_attendance.sh if present

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x "$ROOT_DIR/scripts/start_attendance.sh" ]]; then
  exec "$ROOT_DIR/scripts/start_attendance.sh" "$@"
elif [[ -f "$ROOT_DIR/scripts/start_attendance.sh" ]]; then
  bash "$ROOT_DIR/scripts/start_attendance.sh" "$@"
else
  echo "scripts/start_attendance.sh not found."
  echo "Run: source venv/bin/activate && python attendance_system.py --demo"
  exit 1
fi
