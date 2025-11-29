#!/usr/bin/env bash
set -euo pipefail

# Enable Raspberry Pi power button on GPIO 3 (pin 5) for shutdown + power-on
# - Adds dtoverlay=gpio-shutdown with proper parameters
# - Works on Raspberry Pi OS Bullseye/Bookworm (handles /boot and /boot/firmware)
# - Idempotent: safe to run multiple times

REQUIRED_OVERLAY="dtoverlay=gpio-shutdown,gpio_pin=3,active_low=1,gpio_pull=up"

# Detect config.txt path
CFG=""
if [[ -f /boot/firmware/config.txt ]]; then
  CFG=/boot/firmware/config.txt
elif [[ -f /boot/config.txt ]]; then
  CFG=/boot/config.txt
else
  echo "ERROR: Could not find /boot/firmware/config.txt or /boot/config.txt"
  exit 1
fi

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "This script needs root. Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

# Backup first
TS=$(date +%Y%m%d_%H%M%S)
BACKUP="${CFG}.backup_${TS}"
cp "$CFG" "$BACKUP"
echo "Backed up ${CFG} -> ${BACKUP}"

# Ensure the overlay line exists (exact match) once
if grep -q "^${REQUIRED_OVERLAY}$" "$CFG"; then
  echo "Overlay already present: ${REQUIRED_OVERLAY}"
else
  # If another gpio-shutdown line exists, comment it out for clarity
  if grep -q '^dtoverlay=gpio-shutdown' "$CFG"; then
    echo "Found existing gpio-shutdown overlay. Commenting it out to avoid conflict..."
    sed -i 's/^dtoverlay=gpio-shutdown/# & (disabled by enable_power_button.sh)/' "$CFG"
  fi
  echo "Adding overlay: ${REQUIRED_OVERLAY}"
  printf "\n# Enable power button on GPIO3 (pin 5) for shutdown + wake\n%s\n" "$REQUIRED_OVERLAY" >> "$CFG"
fi

# Show summary
echo
echo "Done. Review tail of ${CFG}:"
tail -n 6 "$CFG"

echo
cat <<'EOF'
Next steps:
1) Wire a momentary push button between GPIO 3 (pin 5) and GND (pin 6).
2) Reboot to apply overlay:
   sudo reboot

Usage after reboot:
- Short press: triggers safe OS shutdown.
- While halted: press button to power the Pi back on (GPIO3 is wake-capable).

Note:
- Our app also monitors the button for safe shutdown, but the kernel overlay
  handles shutdown/wake even if the app isn't running.
EOF
