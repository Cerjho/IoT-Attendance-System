# Maintenance Scripts

Utility scripts for system maintenance, diagnostics, and troubleshooting.

## Scripts

### `detect_cameras.sh`
Detects available cameras and tests if they can capture frames.

**Usage:**
```bash
bash scripts/maintenance/detect_cameras.sh
```

**Output:**
- Lists all video devices
- Tests camera indices 0-5
- Shows which cameras can capture frames
- Recommends camera index to use in config

### `fix_iot_devices_permissions.sh`
Helper script to apply Supabase permissions fix for the enrichment trigger.

**Usage:**
```bash
bash scripts/maintenance/fix_iot_devices_permissions.sh
```

**What it does:**
- Displays the SQL migration needed
- Provides instructions for manual application via Supabase Dashboard
- Shows the SQL content for copy/paste

**Note:** This script displays SQL but cannot apply it directly. You must run the SQL in Supabase Dashboard SQL Editor.

## Related

- Migration file: `supabase/migrations/20251206120000_fix_iot_devices_permissions.sql`
- Troubleshooting docs: `docs/troubleshooting/`
