#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="attendance.service"
SERVICE_SRC="$(pwd)/scripts/deployment/${SERVICE_NAME}"
SERVICE_DEST="/etc/systemd/system/${SERVICE_NAME}"

echo "Installing ${SERVICE_NAME} to systemd..."
sudo cp "${SERVICE_SRC}" "${SERVICE_DEST}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
echo "Service enabled. You can start it now with: sudo systemctl start ${SERVICE_NAME}"
echo "Check logs with: journalctl -u ${SERVICE_NAME} -f"
