#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

echo "Cleaning workspace at: $ROOT_DIR"

# 1) Remove Python caches and test cache
find "$ROOT_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} + || true
rm -rf "$ROOT_DIR/.pytest_cache" || true
rm -rf "$ROOT_DIR/tests/.pytest_cache" || true

# 2) Remove logs
find "$ROOT_DIR/logs" -maxdepth 1 -type f -name "*.log" -print -delete 2>/dev/null || true
find "$ROOT_DIR/data/logs" -maxdepth 1 -type f -name "*.log" -print -delete 2>/dev/null || true

# 3) Remove generated photos and QR codes (keep structure via .gitkeep)
for dir in "$ROOT_DIR/data/photos" "$ROOT_DIR/data/qr_codes"; do
  if [[ -d "$dir" ]]; then
    find "$dir" -type f ! -name ".gitkeep" \( -name "*.jpg" -o -name "*.png" -o -name "*.txt" \) -print -delete || true
  fi
done

# 4) Remove temporary files
find "$ROOT_DIR" -type f \( -name "*.tmp" -o -name "*~" -o -name "*.bak" -o -name "*.backup" \) -print -delete || true

# 5) Summarize remaining sizes for data and logs
for d in "$ROOT_DIR/data" "$ROOT_DIR/logs"; do
  if [[ -d "$d" ]]; then
    echo "Remaining in $(basename "$d"):"
    du -sh "$d" 2>/dev/null || true
  fi
done

echo "Cleanup complete."