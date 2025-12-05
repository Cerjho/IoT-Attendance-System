#!/usr/bin/env bash
set -euo pipefail

# Enable Raspberry Pi power button - Standard configuration
# - GPIO 3 (pin 5): Wake-from-halt only (gpio-poweroff overlay)
# - GPIO 17 (pin 11): Shutdown control via app
# - Both GPIOs connected to same button
# - Works on Raspberry Pi OS Bullseye/Bookworm (handles /boot and /boot/firmware)
# - Idempotent: safe to run multiple times

REQUIRED_OVERLAY="dtoverlay=gpio-poweroff,gpiopin=3,active_low=1"

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
  # If old gpio-shutdown line exists, comment it out
  if grep -q '^dtoverlay=gpio-shutdown' "$CFG"; then
    echo "Found existing gpio-shutdown overlay. Commenting it out..."
    sed -i 's/^dtoverlay=gpio-shutdown/# & (disabled by enable_power_button.sh)/' "$CFG"
  fi
  # If old gpio-poweroff line exists, comment it out
  if grep -q '^dtoverlay=gpio-poweroff' "$CFG"; then
    echo "Found existing gpio-poweroff overlay. Commenting it out..."
    sed -i 's/^dtoverlay=gpio-poweroff/# & (disabled by enable_power_button.sh)/' "$CFG"
  fi
  echo "Adding overlay: ${REQUIRED_OVERLAY}"
  printf "\n# Power button: GPIO 3 (pin 5) wake-only, GPIO 17 (pin 11) shutdown via app\n%s\n" "$REQUIRED_OVERLAY" >> "$CFG"
fi

# Show summary
echo
echo "Done. Review tail of ${CFG}:"
tail -n 6 "$CFG"

echo
cat <<'EOF'
Next steps:
1) Wire a momentary push button:
   - Button Pin 1 → GPIO 17 (pin 11) + GPIO 3 (pin 5) [bridge both]
   - Button Pin 2 → GND (any ground pin)
2) Reboot to apply overlay:
   sudo reboot

Usage after reboot:
- While running: Short press = safe shutdown, Long press = force (via GPIO 17)
- While halted: Press to wake Pi (GPIO 3 wake capability)

Standard GPIO Setup:
- GPIO 3: Wake-from-halt only (gpio-poweroff overlay)
- GPIO 17: Shutdown control via app (short/long press detection)
- Both GPIOs connected to same button
EOF
