# Copilot Instructions for IoT Attendance System

These project-specific guidelines help AI coding agents work productively in this codebase. Focus on the concrete patterns, files, and workflows used here.

## Code Organization Principles

**ALWAYS maintain clean, organized code:**

1. **Module Structure:** Keep modules focused and single-purpose under `src/` domain folders
2. **File Size:** Break large files (>500 lines) into logical submodules
3. **Imports:** Group imports (stdlib, third-party, local) with blank lines between groups
4. **Documentation:** Every module must have docstrings explaining purpose and key functions
5. **Consistent Naming:**
   - Functions/methods: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`
   - Private: prefix with `_`
6. **Error Handling:** Use specific exception types; avoid bare `except:`
7. **Type Hints:** Add type hints for function parameters and returns when adding new code
8. **Comments:** Explain "why" not "what"; keep comments updated with code changes
9. **Testing:** Add tests for new features; maintain existing test patterns
10. **Logging:** Use appropriate log levels (debug, info, warning, error); include context

**When refactoring:**
- Preserve existing functionality exactly
- Update all related documentation
- Ensure all tests still pass
- Maintain backward compatibility unless explicitly changing API

## Architecture Overview
- **Entry point:** `attendance_system.py` orchestrates scanning, face-quality validation, local save, cloud sync, and notifications.
- **Core modules (`src/`):**
  - `camera/` (capture pipeline), `face_quality.py` (9 checks + stability), `lighting/` (illumination analysis)
  - `database/` (SQLite cache + offline queue), `cloud/` (Supabase REST + storage), `sync/` (daily roster)
  - `notifications/` (SMS), `network/` (connectivity), `attendance/` (schedule windows & scan type via `schedule_manager.py`), `utils/` (config, logging, helpers)
- **Data flow (typical scan):** QR validated → quality stable 3s → photo saved → local DB write → cloud sync (if online) → SMS.
- **Privacy model:** Roster synced daily; cache wiped each evening. System is designed to operate offline with eventual cloud sync.

## Configuration & Secrets
- **Config file:** `config/config.json` for feature flags and service settings (e.g., `cloud.enabled`, Supabase `url`/`api_key`). Use `src/utils/config_loader.py` patterns when adding config.
- **Env vars:** `.env` for credentials (loaded by `scripts/start_attendance.sh` and `scripts/start_dashboard.sh`). Do not hardcode secrets.
  - Required: `SUPABASE_URL`, `SUPABASE_KEY`, `DEVICE_ID`
  - Optional: `DASHBOARD_API_KEY` (for admin dashboard authentication)
  - SMS: `SMS_USERNAME`, `SMS_PASSWORD`, `SMS_DEVICE_ID`, `SMS_API_URL`
- **Device ID:** `device_id` in config is used in cloud sync status; ensure it's set.
- **Dashboard auth:** Set `admin_dashboard.auth_enabled: true` in config and `DASHBOARD_API_KEY` in `.env` for secure remote access.

## Run & Test Workflows
- **Start (GUI/headless):**
  - `bash scripts/start_attendance.sh [--headless|--demo]`
  - Shim: `start_attendance.sh` at repo root delegates to the script above.
- **Start (dashboard only):**
  - `bash scripts/start_dashboard.sh` - Standalone admin dashboard without camera requirement
  - Access at `http://localhost:8080` (requires API key if auth enabled)
- **Start (real-time monitoring):**
  - `bash scripts/start_monitor.sh [port]` - Real-time monitoring dashboard (default port 8888)
  - Access at `http://localhost:8888/dashboard` - Live system metrics, events, alerts
- **Direct run:** `python attendance_system.py [--demo]`
- **Pytest:** `pytest -q` (see `pytest.ini`; markers: `hardware`, `integration`). Prefer unit tests under `tests/` and avoid hardware markers unless necessary.
- **Dashboard tests:**
  - `bash scripts/tests/test_endpoints.sh <api_key>` - Test all 10 API endpoints
  - `bash scripts/tests/test_security.sh <api_key>` - Validate authentication
  - `bash scripts/tests/test_ip_whitelist.sh <api_key>` - Validate IP restrictions
- **Health checks:**
  - Roster: `python utils/test-scripts/test_roster_sync.py`
  - Face quality: `python utils/test-scripts/test_face_quality.py`
  - System status: `python scripts/status.py` or `utils/check_status.py`
  - Dashboard health: `bash scripts/health_check.sh` (auto-restart on failure)
 - **Force cloud sync:** Use `CloudSyncManager.force_sync_all()` via scripts or REPL when online.

## Testing
- **Unit/Integration:** Use `pytest -q` (configured in `pytest.ini`).
- **Markers:**
  - Hardware-dependent: add `@pytest.mark.hardware` (GPIO, camera). Excluded from default CI.
  - Cross-component flows: add `@pytest.mark.integration`.
- **Run subsets:**
  ```bash
  # Fast unit tests only
  pytest -q -m "not hardware and not integration"

  # Integration-only
  pytest -q -m integration

  # Hardware tests (requires device)
  pytest -q -m hardware
  ```
- **Targeted tests:**
  ```bash
  pytest -q tests/test_simple_flow.py
  pytest -q tests/test_system_integration.py -m integration
  pytest -q tests/test_face_quality.py
  pytest -q tests/test_cloud_sync_unit.py
  pytest -q tests/test_queue_sync_integration.py -m integration
  pytest -q tests/test_cloud_sync_extended.py -m integration
  ```
- **SMS quick check:** Run `tests/test_sms_quick.sh` for a minimal notifier check.

## Integration Coverage Highlights
- **Queue → Cloud Sync:** `tests/test_queue_sync_integration.py` asserts queued records are marked `synced=1` with `cloud_record_id` after mocked REST success.
- **Photo Upload Remarks:** `tests/test_cloud_sync_extended.py` verifies `PhotoUploader.upload_photo()` URL is included in `remarks` payload.
- **Negative Paths:** Student not found and REST `500` keep records in `sync_queue` with incremented `retry_count` (backoff per config).
- **Force Sync:** `tests/test_cloud_sync_extended.py::test_force_sync_all_marks_records_synced` validates `force_sync_all()`.

## Safe Run
- **Startup script behavior:** `scripts/start_attendance.sh` activates `.venv`/`venv`, loads `.env` (`export $(cat .env | grep -v '^#' | xargs)`), echoes mode (`--headless|--demo`), and runs `python attendance_system.py`.
- **Root shim:** `start_attendance.sh` at repo root delegates to `scripts/start_attendance.sh` and exists to satisfy tests expecting a root launcher.
- **Recommended invocation:**
  ```bash
  # Create and activate venv if needed
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt

  # Ensure `.env` exists with SUPABASE_URL and SUPABASE_KEY
  printf "SUPABASE_URL=https://your-project.supabase.co\nSUPABASE_KEY=your_api_key\n" > .env

  # Start (GUI)
  bash scripts/start_attendance.sh

  # Start (headless)
  bash scripts/start_attendance.sh --headless
  ```

## Data & Artifacts
- **Local DB:** `data/attendance.db`; logs under `data/logs/`; photos under `data/photos/`; QR codes under `data/qr_codes/`.
- **Exports:** Attendance JSON exports like `data/attendance_export_*.json` are generated by viewer tools.

## Key Patterns & Conventions
- **Scheduling/scan type:** Use `src/attendance/schedule_manager.py` to determine `LOGIN/LOGOUT` windows and late status. Don't duplicate logic.
- **Quality gating:** Keep the 9-check + 3-second stability contract (`face_quality.py`). If adding checks, preserve timing semantics and thresholds.
- **Offline-first:** Write to local SQLite and queue for cloud sync; cloud is authoritative but system must continue when offline.
- **Cloud integration:** Supabase REST for rows; Storage for photos. Follow existing `src/cloud/*` methods and avoid new client SDKs unless justified.
- **Robustness patterns (Phase 1):**
  - **Disk monitoring (`src/utils/disk_monitor.py`):** Check space before saves with `check_space_available()`, run `auto_cleanup()` periodically for old photos/logs, enforce size limits.
  - **Circuit breakers (`src/utils/circuit_breaker.py`):** Wrap all Supabase REST calls with `CircuitBreaker.call()` (students/attendance endpoints); handle `CircuitBreakerOpen` gracefully.
  - **Camera recovery (`src/camera/camera_handler.py`):** Init with retry (`max_init_retries`), periodic health checks, auto-recovery from transient failures, fallback to offline mode.
  - **Transaction safety (`src/utils/db_transactions.py`):** Use `SafeAttendanceDB.save_attendance_with_queue()` for atomic saves, `mark_synced_and_cleanup_queue()` for sync completion, `with transaction(conn)` for multi-step ops.
- **Phase 2 improvements:**
  - **Network timeouts (`src/utils/network_timeouts.py`):** Always use `NetworkTimeouts` for `requests` calls; configure per service (Supabase, Storage, SMS); prevents hangs.
  - **Queue validation (`src/utils/queue_validator.py`):** Validate data with `QueueDataValidator.validate_attendance()` before queueing; auto-fix common issues; sanitize invalid fields.
  - **File locking (`src/utils/file_locks.py`):** Use `DatabaseLock` for critical DB sections, `PhotoLock` for photo operations, or `file_lock()` context manager for any file; prevents races.
  - **Structured logging (`src/utils/structured_logging.py`):** Set correlation IDs with `set_correlation_id()` at operation boundaries; use `StructuredLogger` for rich context; JSON logs for monitoring.
- **Admin dashboard (`src/utils/admin_dashboard.py`):**
  - **Authentication:** API key via `Authorization: Bearer <key>` or `X-API-Key: <key>` header; constant-time comparison prevents timing attacks.
  - **IP whitelisting:** Configure `admin_dashboard.allowed_ips` array in config (supports CIDR notation like `192.168.1.0/24`).
  - **Security headers:** HSTS, X-Frame-Options, X-XSS-Protection, X-Content-Type-Options automatically added.
  - **CORS:** Preflight handling via `do_OPTIONS()`; configurable origins.
  - **Endpoints:** `/health`, `/status`, `/metrics`, `/metrics/prometheus`, `/scans/recent`, `/queue/status`, `/config`, `/system/info`.
  - **Standalone mode:** Run via `scripts/start_dashboard_only.py` without camera/attendance system for monitoring only.
- **Real-time monitoring (integrated with fleet dashboard):**
  - **Core engine (`src/utils/realtime_monitor.py`):** Event tracking, metrics calculation, alert generation, system state tracking; thread-safe with background monitoring (5s interval).
  - **Integration:** Real-time monitoring now integrated into admin dashboard at port 8080; no separate dashboard needed.
  - **API endpoints (admin dashboard):** `/api/realtime/status`, `/api/realtime/metrics`, `/api/realtime/events`, `/api/realtime/alerts`, `/api/realtime/stream` (SSE).
  - **Fleet Dashboard UI:** Access monitoring via "📊 Monitor" tab in multi-device dashboard at `http://localhost:8080/`.
  - **Metrics tracked:** Scans today/hour, success rate, queue size, failed syncs, uptime, component health (camera/cloud/SMS/queue).
  - **Alert conditions:** Queue >50 (warning), failed syncs >10 (error), success rate <80% with >10 scans (warning); 5-min deduplication.
  - **Integration points:** Camera status, photo captures, attendance records, cloud sync, SMS notifications logged automatically.
  - **Start integrated dashboard:** `bash scripts/start_dashboard.sh` (port 8080); access at `http://localhost:8080/` then click "Monitor" tab.
  - **Usage pattern (in code):**
    ```python
    from src.utils.realtime_monitor import get_monitor
    monitor = get_monitor()
    monitor.start()
    monitor.log_event("scan", "Attendance recorded", {"student_id": "2021001"})
    monitor.update_system_state("camera", "online", "640x480")
    ```
  - **Note:** Old standalone dashboard (`scripts/realtime_dashboard.py` on port 8888) deprecated in favor of integrated dashboard.
- **Supabase REST details:**
  - Attendance insert: `POST {url}/rest/v1/attendance` with headers `apikey`, `Authorization: Bearer <key>`, `Prefer: return=representation`.
  - Payload fields: `student_id` (UUID), `date` (ISO date), `time_in` or `time_out` (ISO time), `status`, `device_id`, `remarks`.
  - Student lookup: `GET {url}/rest/v1/students?student_number=eq.<num>&select=id` to resolve `student_id`.
  - Storage upload: `POST {url}/storage/v1/object/<bucket>/<path>` with image bytes; public URL at `.../object/public/<bucket>/<path>`.
- **Notifications:** SMS sending flows live in `src/notifications/`; ensure idempotency with scan cooldown rules in `ScheduleManager`.
- **Logging:** Centralized logger via `src/utils/logger_config.py` (if present). Use module loggers (`logging.getLogger(__name__)`).
- **Logging patterns:** Use per-module logger; levels: info for lifecycle, debug for timers/reset, warning for retries/timeouts, error for failures. Logs go to `data/logs/` via configured handlers.
- **File layout:** Keep new modules under the existing domain folders; avoid monoliths in `attendance_system.py`—prefer delegating to `src/*`.

## HTML/Public Views
- **Public site:** `public/view-attendance.html` and `docs/view-attendance.html` serve simple attendance views via GitHub Pages; keep client-side UUID/roster logic in sync with server IDs.
- **Data expectations:** Public views expect student UUID-resolved attendance rows; verify mapping from local `student_number` → cloud `students.id` as implemented in `src/cloud/cloud_sync.py`.

## When Making Changes
- **Extend, don’t fork:** Add functions/classes in the relevant `src/` submodule; wire through `attendance_system.py`.
- **Config-driven:** New behavior should be toggleable via `config/config.json` with safe defaults.
- **Tests first for flows:** For cross-component changes, add or update tests under `tests/` (e.g., `test_simple_flow.py`, `test_system_integration.py`). Respect pytest markers.
- **Keep scripts working:** If you change startup or env handling, update `scripts/start_attendance.sh` and root `start_attendance.sh` shim.

## Do / Don't
- **Do:** Use `ScheduleManager` for scan type/status; keep 3s stability in auto-capture; write unsynced rows to SQLite and queue.
- **Do:** Use Supabase REST endpoints and `PhotoUploader` for storage; include `device_id` and useful `remarks`.
- **Do:** Use `DiskMonitor` to check space before saving photos/logs; use `CircuitBreaker` for all Supabase calls; use `SafeAttendanceDB` for atomic attendance+queue saves.
- **Do:** Configure camera recovery params in config; leverage auto-retry and health checks for production deployments.
- **Do:** Use `NetworkTimeouts` for all network calls (don't hardcode timeouts); validate queue data before insert; use file locking for critical sections; set correlation IDs for tracing.
- **Do:** Enable dashboard authentication for remote access; use `DASHBOARD_API_KEY` env var; configure IP whitelist for additional security.
- **Do:** Use `scripts/start_dashboard.sh` to ensure `.env` is loaded; never run dashboard Python directly in production.
- **Do:** Test dashboard endpoints with `scripts/tests/test_*.sh` after security changes; verify authentication working before exposing remotely.
- **Don't:** Hardcode secrets; bypass queue when offline; duplicate schedule/quality logic outside existing modules.
- **Don't:** Introduce SDKs without justification; break `start_attendance.sh` env loading behavior.
- **Don't:** Skip disk space checks before file writes; make direct REST calls without circuit breaker; write attendance and queue separately (use transactions); use hardcoded timeouts; skip queue validation; write to DB/photos without locks in concurrent code.
- **Don't:** Expose dashboard to internet without authentication; commit API keys to git; disable auth for convenience in production.
- **Don't:** Run dashboard on port 8080 exposed to internet (use Nginx reverse proxy with HTTPS instead).

## Useful References
- `README.md` (overview, commands), `PROJECT_STRUCTURE.md` (module map), `docs/technical/SYSTEM_OVERVIEW.md` (architecture), `docs/technical/AUTO_CAPTURE.md` (quality), `supabase/migrations/` (schema), `tests/` (usage examples).
- **Dashboard & Security:**
  - `docs/DASHBOARD_DEPLOYMENT.md` - Quick deployment reference
  - `docs/security/SECURITY_SETUP.md` - Complete security guide with examples
  - `docs/security/IP_WHITELIST_CONFIG.md` - IP-based access control
  - `docs/security/SECURE_DEPLOYMENT_SUMMARY.md` - Quick status and next steps
  - `scripts/README_DASHBOARD.md` - Detailed operations manual
  - `scripts/tests/README.md` - Test suite documentation
- **HTTPS Setup:**
  - `scripts/nginx_dashboard.conf` - Nginx reverse proxy config
  - `scripts/generate_ssl_cert.sh` - SSL certificate generation
- **Real-time Monitoring (Integrated):**
  - Access via admin dashboard at `http://localhost:8080/` → "📊 Monitor" tab
  - `docs/REALTIME_MONITORING.md` - Complete monitoring guide
  - `docs/MONITORING_QUICKREF.md` - Quick reference card
  - `docs/summaries/REALTIME_MONITORING_SUMMARY.md` - Implementation details

## Examples
- Determine expected scan type and status:
  ```python
  from src.attendance.schedule_manager import ScheduleManager
  sm = ScheduleManager(config)
  scan_type, session = sm.get_expected_scan_type()
  status = sm.determine_attendance_status(datetime.now(), session, scan_type)
  ```
- Start system headless:
  ```bash
  bash scripts/start_attendance.sh --headless
  ```
- Start dashboard only (no camera):
  ```bash
  bash scripts/start_dashboard.sh
  # Access: http://localhost:8080/health
  ```
- Test dashboard with authentication:
  ```bash
  API_KEY=$(grep DASHBOARD_API_KEY .env | cut -d= -f2)
  curl -H "Authorization: Bearer $API_KEY" http://localhost:8080/status
  ```
- Setup HTTPS for dashboard:
  ```bash
  bash scripts/generate_ssl_cert.sh
  sudo apt install nginx
  sudo cp scripts/nginx_dashboard.conf /etc/nginx/sites-available/dashboard
  sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
  sudo nginx -t && sudo systemctl reload nginx
  ```
- Start integrated dashboard with real-time monitoring:
  ```bash
  bash scripts/start_dashboard.sh
  # Access: http://localhost:8080/ then click "📊 Monitor" tab
  ```
- Monitor metrics via API (requires authentication):
  ```bash
  API_KEY=$(grep DASHBOARD_API_KEY .env | cut -d= -f2)
  curl -H "Authorization: Bearer $API_KEY" http://localhost:8080/api/realtime/metrics
  curl -N -H "Authorization: Bearer $API_KEY" http://localhost:8080/api/realtime/stream  # Live SSE stream
  ```

## Detailed Thresholds & Queues
- **Face quality thresholds (from `src/face_quality.py`):**
  - **Face size:** min width `80px`.
  - **Centered:** deviation ≤ `12%` of frame both axes.
  - **Head pose:** yaw ≤ `15°`, pitch ≤ `15°`, roll ≤ `10°` (estimated via eye geometry).
  - **Eyes open:** average EAR ≥ `0.25` (via Haar eye boxes).
  - **Mouth closed:** openness ≤ `0.5` of face height in mouth region.
  - **Sharpness:** Laplacian variance ≥ `80`.
  - **Brightness:** `70–180` grayscale avg.
  - **Illumination:** std-dev `< 40` and dark-pixel ratio `< 0.20`.
  - **Stability:** all checks must pass continuously for `3s`; session timeout `15s`.
- **Offline queue (from `src/database/sync_queue.py` and `src/cloud/cloud_sync.py`):**
  - Attendance rows saved locally with `synced=0`; photos saved under `data/photos/`.
  - Queue table `sync_queue` stores records with JSON `data`, `retry_count`, and priority.
  - When cloud disabled/offline, records added via `add_to_queue('attendance', id, {attendance, photo_path})`.
  - On connectivity, `process_sync_queue()` uploads photo (Storage) then inserts attendance (REST). Success marks row synced and removes queue record; optional local photo cleanup.
  - Retries use exponential backoff (`30s`, `60s`, `120s`, capped `300s`), up to `retry_attempts` from config; exceeded retries can be cleared via `clear_old_failed_records()`.

## Cloud Payload Examples
- **Attendance insert (REST `POST /rest/v1/attendance`):**
  ```json
  {
    "student_id": "3c2c6e8f-7d3e-4f7a-9a1b-3f82a1cdb1a4",
    "date": "2025-11-29",
    "time_in": "07:12:34",
    "status": "present",
    "device_id": "pi-lab-01",
    "remarks": "QR: 2021001 | Photo: https://.../object/public/attendance-photos/2021001/20251129_071234_img.jpg"
  }
  ```
- **Student lookup (REST `GET /rest/v1/students`):**
  ```http
  GET {url}/rest/v1/students?student_number=eq.2021001&select=id
  Headers: apikey: <key>, Authorization: Bearer <key>
  ```
- **Storage upload (REST `POST /storage/v1/object/<bucket>/<path>`):**
  - Path example: `attendance-photos/2021001/20251129_071234_img.jpg`
  - Public URL: `{url}/storage/v1/object/public/attendance-photos/2021001/20251129_071234_img.jpg`

## Troubleshooting Cloud Sync
- **Invalid credentials:** Check `.env` is loaded; values must not start with `${...}`. See `CloudSyncManager._validate_credentials()`.
- **Student not found:** Ensure `students` table has `student_number`; lookup uses `select=id`. Verify with curl.
- **Storage upload fails:** Confirm bucket `attendance-photos` exists and is public; check status code and `response.text` in logs.
- **Queue stuck:** Use `SyncQueueManager.clear_old_failed_records()`; verify connectivity via `ConnectivityMonitor.is_online()`.
- **Photo not deleted:** `cleanup_photos_after_sync` controls deletion; ensure file exists and path correct.

## Supabase Schema References
- See `supabase/migrations/` and `supabase/sql/` for table definitions.
- Attendance table (new schema) expects: `student_id (UUID)`, `date (DATE)`, `time_in/time_out (TIME)`, `status (TEXT)`, `device_id (TEXT)`, `remarks (TEXT)`.

## Quick Cloud Checks
- **Setup env for curl (clean):**
  ```bash
  # Load from .env into shell variables
  export $(grep -v '^#' .env | xargs)
  # Map to expected names for examples
  SUPABASE_URL="$SUPABASE_URL"
  SUPABASE_KEY="$SUPABASE_KEY"
  ```
- **Test students REST:**
  ```bash
  curl -s "${SUPABASE_URL}/rest/v1/students?select=id&limit=1" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}"
  ```
- **Test attendance insert (dry-run idea):** Prefer inserting via app; for manual check use a minimal payload and verify 200/201.
  ```bash
  curl -s -X POST "${SUPABASE_URL}/rest/v1/attendance" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=representation" \
    -d '{"student_id":"<uuid>","date":"2025-11-29","time_in":"07:12:34","status":"present","device_id":"pi-lab-01"}'
  ```
- **Test storage upload:**
  ```bash
  curl -s -X POST "${SUPABASE_URL}/storage/v1/object/attendance-photos/test/hello.jpg" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_KEY}" \
    -H "Content-Type: image/jpeg" \
    --data-binary @/path/to/local.jpg
  ```

## Force Sync Example
```python
from src.cloud.cloud_sync import CloudSyncManager
from src.database.sync_queue import SyncQueueManager
from src.network.connectivity import ConnectivityMonitor
from src.utils.config_loader import load_config  # clean config loading

# Load config from config/config.json (and environment overrides if loader supports it)
config = load_config("config/config.json")

# Ensure required fields are present
config.setdefault("enabled", True)
config.setdefault("retry_attempts", 3)
config.setdefault("retry_delay", 30)

sync_queue = SyncQueueManager(db_path="data/attendance.db")
connectivity = ConnectivityMonitor(config)
cloud = CloudSyncManager(config, sync_queue, connectivity)

result = cloud.force_sync_all()
print(result)
```
