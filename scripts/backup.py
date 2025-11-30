#!/usr/bin/env python3
"""Daily backup script for attendance system"""
import shutil
import os
from datetime import datetime
from pathlib import Path

backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = backup_dir / f"backup_{timestamp}"
backup_path.mkdir()

# Backup database
if Path("data/attendance.db").exists():
    shutil.copy2("data/attendance.db", backup_path / "attendance.db")
    print(f"✅ Database backed up to {backup_path}")

# Backup recent photos (last 7 days)
photos = Path("data/photos")
if photos.exists():
    recent = [p for p in photos.glob("*.jpg") if (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)).days < 7]
    if recent:
        photo_backup = backup_path / "photos"
        photo_backup.mkdir()
        for p in recent:
            shutil.copy2(p, photo_backup / p.name)
        print(f"✅ {len(recent)} recent photos backed up")

# Keep only last 30 backups
backups = sorted(backup_dir.glob("backup_*"))
if len(backups) > 30:
    for old in backups[:-30]:
        shutil.rmtree(old)
    print(f"✅ Cleaned up old backups, kept last 30")
