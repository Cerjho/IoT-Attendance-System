# System Scripts

## Production Scripts

### start_attendance.sh
Main system startup script.

**Purpose:** Start the IoT attendance system with proper environment configuration.

**Features:**
- Auto-loads environment variables from .env
- Supports GUI and headless modes
- Displays system workflow information

**Usage:**
```bash
# GUI mode (with display)
./scripts/start_attendance.sh

# Headless mode (no display)
./scripts/start_attendance.sh --headless

# Demo mode (simulated data)
./scripts/start_attendance.sh --demo
```

## Deployment Scripts

Located in `deployment/` directory:

### migrate_supabase.sh
Supabase database migration script.

**Purpose:** Apply database schema changes to Supabase.

**Usage:**
```bash
./scripts/deployment/migrate_supabase.sh
```

## Archive

Old/deprecated scripts are stored in `archive/` directory for reference.
