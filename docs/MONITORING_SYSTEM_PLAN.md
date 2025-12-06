
## Plan: Standalone Supabase Real-Time IoT Monitoring System

Build a production-grade, framework-agnostic real-time monitoring platform for IoT devices using Supabase Realtime as the backbone, completely independent from the existing attendance system, with sub-second latency, offline resilience, and secure multi-device coordination.

### Steps

1. **Design complete Supabase schema** in new project `supabase/migrations/001_realtime_monitoring_core.sql` with tables: `devices` (PK uuid, device_id unique, name, location json, status enum, last_heartbeat timestamptz, metadata jsonb), `device_heartbeats` (device_id FK, cpu float, ram float, temp float, storage float, uptime_seconds int, queue_length int, network_status text, created_at timestamptz with index), `attendance_logs` (device_id, student_id, student_name, result enum [success/fail/not_found], scan_type enum [qr/face], error_details jsonb, timestamp timestamptz with index), `error_logs` (device_id FK, level enum [info/warn/error/critical], code text, message text, stack_trace text, context jsonb, created_at timestamptz with index), `device_commands` (uuid PK, device_id FK, command enum [reboot/clear_queue/sync_now/update_config], args jsonb, status enum [pending/sent/executing/executed/failed/timeout], created_at, updated_at, executed_at timestamptz); add composite indexes on `(device_id, created_at DESC)` for all time-series tables; enable realtime publication on all tables (`ALTER PUBLICATION supabase_realtime ADD TABLE devices, device_heartbeats, attendance_logs, error_logs, device_commands`).

2. **Create RLS policies** in `002_realtime_security.sql` with device-scoped JWT claims: policy `devices_device_own_read` allows `SELECT WHERE device_id = auth.jwt() ->> 'device_id'::text`, policy `heartbeats_device_insert` allows `INSERT WHERE device_id = auth.jwt() ->> 'device_id'::text AND NEW.created_at > NOW() - INTERVAL '1 minute'` (prevents timestamp spoofing), policy `commands_device_read` allows `SELECT WHERE device_id = auth.jwt() ->> 'device_id'::text AND status IN ('pending', 'sent')`, policy `commands_device_update` allows `UPDATE WHERE device_id = auth.jwt() ->> 'device_id'::text AND status != 'pending'` (prevents tampering with new commands), policy `admin_full_access` allows `ALL WHERE auth.role() = 'authenticated'` (dashboard access); add rate limiting via `pgaudit` extension tracking inserts per device (max 1000 heartbeats/hour).

3. **Build Python Pi agent** in `pi-agent/` with structure: `monitor_agent.py` (main orchestrator with async event loop), `collectors/system_metrics.py` (psutil wrapper collecting CPU via `psutil.cpu_percent(interval=1)`, RAM via `psutil.virtual_memory()`, disk via `psutil.disk_usage('/')`, temperature via `vcgencmd measure_temp` with psutil fallback, uptime via `uptime`, all collected every 30s), `collectors/app_metrics.py` (adapter interface for attendance system integration reading attendance.db for queue size and last scan timestamp), `realtime/client.py` (Supabase Realtime client using `realtime-py==1.0.0` with channel subscriptions, reconnection logic using exponential backoff [1s, 2s, 4s, 8s, max 60s], JWT refresh every 90 minutes), `realtime/publisher.py` (batches heartbeats every 30s to reduce DB load, publishes attendance events immediately, publishes errors immediately with severity-based throttling), `commands/executor.py` (listens to Realtime `device_commands` channel filtered by device_id, executes via subprocess with 60s timeout, updates command status atomically), `offline/queue.py` (extends existing `src/database/sync_queue.py` from attendance system with proven exponential backoff [30s, 60s, 120s, 240s, max 300s], max 5 retries, auto-archive to `failed_queue` table after max retries), `config.py` (imports existing `src/utils/config_loader.py` with env var substitution already implemented).

   **Reuse Existing Utilities from Attendance System:**
   - `src/utils/config_loader.py` - Config loading with `${ENV_VAR}` substitution ✓
   - `src/network/connectivity.py` - `ConnectivityMonitor` (pings 8.8.8.8 every 5s) ✓
   - `src/utils/queue_validator.py` - `QueueDataValidator` for data sanitization ✓
   - `src/database/sync_queue.py` - `SyncQueueManager` with exponential backoff ✓
   - `src/utils/network_timeouts.py` - `NetworkTimeouts` for service-specific timeouts ✓
   - `src/utils/circuit_breaker.py` - `CircuitBreaker` for failure protection ✓
   - `src/utils/structured_logging.py` - `StructuredLogger` with correlation IDs ✓
   - `src/utils/file_locks.py` - `DatabaseLock`, `PhotoLock` for SQLite safety ✓
   - `src/utils/db_transactions.py` - Atomic transaction patterns ✓

4. **Implement device JWT service** in `backend/jwt_service/` (optional FastAPI microservice): `app.py` with endpoint `POST /token` accepting `{"device_id": "...", "api_secret": "..."}` payload, validates `api_secret` against Supabase `devices.api_secret` column via REST lookup, generates JWT with claims `{"sub": device_id, "device_id": device_id, "role": "device", "exp": now + 2h}` signed with Supabase JWT secret from env, returns `{"access_token": "...", "expires_in": 7200, "refresh_token": "..."}` (refresh token stored in `device_tokens` table for rotation); secure with per-device API key (32-byte hex) generated on device registration; deploy as systemd service or Docker container; add rate limiting via `slowapi` (10 requests/minute per device); alternative simpler approach: embed short-lived JWT in Pi agent config with auto-refresh via Supabase function `refresh_device_token(device_id)`.

5. **Create React dashboard** in `dashboard/` using Vite + TypeScript + Tailwind CSS with file structure: `src/components/DeviceGrid.tsx` (grid of device cards showing online status via green/red indicator, last heartbeat relative time, CPU/RAM/temp gauges using Recharts `<RadialBarChart>`, current queue size badge, click opens detail modal), `src/components/DeviceDetail.tsx` (modal with tabs: "Metrics" showing 1-hour time-series charts of CPU/RAM/temp/queue via `<LineChart>` subscribed to `device_heartbeats:INSERT` filtered by `device_id=eq.${id}`, "Logs" showing real-time attendance stream via `attendance_logs:INSERT` subscription with filters for success/fail/not_found, "Errors" showing error timeline with severity badges, "Commands" with buttons for reboot/clear_queue/sync_now posting to `device_commands` table), `src/components/LiveLog.tsx` (infinite scroll attendance feed across all devices via Realtime subscription with `SELECT * FROM attendance_logs ORDER BY timestamp DESC`, filters by device/date/result), `src/components/AlertPanel.tsx` (toast notifications via `react-hot-toast` triggered by `error_logs:INSERT` subscription filtered by `level=eq.error OR level=eq.critical`, auto-dismiss after 10s, persistent list in sidebar), `src/hooks/useRealtimeSubscription.ts` (wrapper for Supabase Realtime with auto-reconnect, stale data detection via 15s keepalive, fallback to polling on connection failure); use `@supabase/supabase-js` client initialized with anon key + RLS for admin dashboard access.

6. **Implement offline resilience** in Pi agent via `offline/queue.py`: use existing `src/network/connectivity.py::ConnectivityMonitor` (already pings `8.8.8.8` every 5s), buffer heartbeats in SQLite `local_queue` table (max 10,000 rows with FIFO eviction), buffer attendance/error logs similarly; on reconnection, batch-upload via `realtime/uploader.py` using Supabase REST bulk insert (`POST /rest/v1/device_heartbeats` with JSON array payload up to 1000 rows per request), mark uploaded rows as synced; use existing `src/utils/queue_validator.py::QueueDataValidator` to sanitize data before queueing (already validates timestamps, clamps numeric ranges, sanitizes text fields); use existing `src/utils/circuit_breaker.py::CircuitBreaker` to wrap Supabase calls with automatic failure protection; monitor queue size and alert via `error_logs` insert if queue >5000 (80% full) or queue growth rate >100/minute; apply existing `src/utils/db_transactions.py` transaction patterns for atomic queue operations.

7. **Add data retention policies** via Supabase cron job using `pg_cron` extension: create migration `003_data_lifecycle.sql` with function `cleanup_old_heartbeats()` deleting `device_heartbeats WHERE created_at < NOW() - INTERVAL '7 days'`, schedule via `SELECT cron.schedule('cleanup-heartbeats', '0 2 * * *', 'SELECT cleanup_old_heartbeats()')` (runs daily 2 AM); create aggregation table `device_metrics_daily` with columns `device_id, date, avg_cpu, avg_ram, max_temp, total_scans, uptime_hours` populated by function `aggregate_daily_metrics()` running at midnight; keep `attendance_logs` for 90 days, `error_logs` for 30 days; add Supabase Edge Function `expire-old-data` as backup cleanup mechanism callable via cron or webhook.

8. **Configure Tailscale networking** documented in `docs/TAILSCALE_SETUP.md`: install Tailscale on all Pi devices and admin workstations via `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up --accept-routes`, note device IPs (format `100.x.x.x`), configure Supabase project "Authentication > URL Configuration" to allow Tailscale CIDR `100.64.0.0/10` in CORS origins, set dashboard `VITE_SUPABASE_URL` to use Tailscale IP if Supabase also on Tailscale network (or keep public URL with IP whitelist), document MagicDNS hostnames (e.g., `pi-lab-01.tailscale.net`) for easier device discovery, add ACL rules via Tailscale admin console to restrict device-to-device communication (Pi agents can only reach Supabase, dashboard can reach all devices for SSH); alternative: use WireGuard if Tailscale not feasible, document setup in `docs/WIREGUARD_SETUP.md`.

9. **Build device discovery mechanism** via multicast DNS (mDNS) in `pi-agent/discovery/advertiser.py`: use `zeroconf` library to broadcast service `_iot-monitor._tcp.local.` with TXT records `{"device_id": "...", "name": "...", "location": "...", "api_port": 8080}`, dashboard discovers via `src/utils/DeviceDiscovery.ts` calling Supabase function `discover_devices()` that polls mDNS or reads from `devices` table updated by Pi agents on startup; add manual registration endpoint in dashboard `POST /api/devices/register` accepting `{device_id, name, ip_address, location}` payload inserting into Supabase `devices` table with status `pending`, Pi agent polls for registration approval and updates status to `active` on first heartbeat.

10. **Implement metrics aggregation service** in `backend/aggregator/` (optional): Python service subscribing to Realtime `device_heartbeats` channel, calculates rolling 5-minute averages via sliding window (using `collections.deque` with 10 entries = 5 min at 30s intervals), inserts into `device_metrics_5min` table for faster dashboard queries; pre-aggregate common queries like "CPU avg per building" via materialized view `device_stats_by_location` refreshed every 5 minutes via `pg_cron`; expose aggregated data via REST endpoint `GET /api/metrics/summary?timeRange=1h&groupBy=building` for dashboard overview page.

11. **Add attendance system adapter** (optional integration bridge) in `pi-agent/adapters/attendance_adapter.py`: monitors existing attendance system's `data/attendance.db` via polling (every 5s), reads from actual tables: `attendance` (id, student_number, date, time_in, time_out, status, photo_path, synced), `sync_queue` (id, record_type, record_id, data, priority, retry_count, created_at), `students` (student_number, name, year_level, section), `device_status` (device_id, status, last_update); transforms to monitoring schema: `{"device_id": config.device_id, "student_id": row.student_number, "student_name": lookup_from_students_table(row.student_number), "result": map_status(row.status), "scan_type": "qr", "timestamp": f"{row.date} {row.time_in or row.time_out}", "photo_url": row.photo_path}`, publishes via `realtime/publisher.py`; reads `sync_queue WHERE synced=0` for queue size metric; status mapping: `{"present": "success", "late": "success", "absent": "not_found", "excused": "success"}`; configure via `config.json` section `{"adapters": {"attendance": {"enabled": true, "db_path": "/home/iot/attendance-system/data/attendance.db", "poll_interval": 5, "tables": {"attendance": "attendance", "queue": "sync_queue", "students": "students"}}}}` allowing gradual integration without modifying attendance system code.

   **Implementation Example:**
   ```python
   # pi-agent/adapters/attendance_adapter.py
   import sqlite3
   from pathlib import Path
   
   class AttendanceSystemAdapter:
       def __init__(self, db_path: str):
           self.db_path = Path(db_path)
           self.last_id = 0
       
       def get_new_scans(self):
           conn = sqlite3.connect(self.db_path)
           cursor = conn.execute(
               "SELECT id, student_number, date, time_in, time_out, status, photo_path "
               "FROM attendance WHERE id > ? ORDER BY id", (self.last_id,)
           )
           for row in cursor.fetchall():
               yield {
                   "student_id": row[1],
                   "student_name": self._lookup_name(row[1]),
                   "result": self._map_status(row[5]),
                   "timestamp": f"{row[2]} {row[3] or row[4]}",
                   "photo_url": row[6]
               }
               self.last_id = row[0]
           conn.close()
       
       def get_queue_size(self):
           conn = sqlite3.connect(self.db_path)
           size = conn.execute("SELECT COUNT(*) FROM sync_queue WHERE synced=0").fetchone()[0]
           conn.close()
           return size
   ```

12. **Create deployment automation** via scripts: `scripts/install_pi.sh` (detects existing attendance system at `/home/iot/attendance-system`, enables adapter if found, clones monitoring repo, installs Python 3.11, creates venv or reuses existing `.venv` from attendance system, installs requirements, generates device API secret, registers device with Supabase, creates systemd service `iot-monitor-agent.service`, enables on boot), `scripts/install_dashboard.sh` (installs Node 20, runs `npm install && npm run build`, configures Nginx reverse proxy on port 443 with SSL via Let's Encrypt avoiding conflict with removed attendance dashboard port 8080, creates systemd service `iot-dashboard.service`), `scripts/generate_device_secret.sh` (generates 32-byte hex secret, inserts into Supabase `devices` table via REST, saves to .env), `scripts/health_check.sh` (curl dashboard health endpoint and agent health endpoint, exits 1 if either fails, suitable for monitoring via Nagios/Zabbix).

   **Coexistence Detection in `scripts/install_pi.sh`:**
   ```bash
   # Detect existing attendance system
   if [ -d "/home/iot/attendance-system" ]; then
       echo "✓ Attendance system detected, enabling adapter"
       CONFIG_TEMPLATE="config-with-adapter.json"
       # Optionally reuse venv
       if [ -d "/home/iot/attendance-system/.venv" ]; then
           ln -s /home/iot/attendance-system/.venv .venv
       fi
   else
       echo "ℹ No attendance system, standalone mode"
       CONFIG_TEMPLATE="config-standalone.json"
   fi
   ```

13. **Add comprehensive testing** with structure: `tests/unit/test_metrics_collector.py` (mocks psutil, verifies metrics calculation), `tests/unit/test_realtime_client.py` (mocks Supabase Realtime, verifies reconnection logic), `tests/integration/test_offline_queue.py` (disables network, captures metrics, re-enables network, verifies upload), `tests/integration/test_command_execution.py` (inserts command into Supabase, verifies Pi agent executes and updates status), `tests/e2e/test_dashboard_realtime.py` (uses Playwright to verify dashboard updates within 2s of Pi agent heartbeat); add GitHub Actions workflow `.github/workflows/test.yml` running unit tests on push, integration tests on PR, E2E tests nightly.

14. **Document complete system** in docs with files: `ARCHITECTURE.md` (system diagram, data flow, component responsibilities, relationship to attendance system with integration modes: standalone/sidecar/deep-integration), `DEPLOYMENT.md` (step-by-step Pi agent and dashboard deployment, Supabase project setup, Tailscale configuration, DNS setup, coexistence with attendance system), `API.md` (Supabase table schemas, RLS policies, REST endpoints, Realtime channel filters, example queries), `CONFIGURATION.md` (all config options with defaults and examples, environment variables, secrets management, shared utilities reference), `TROUBLESHOOTING.md` (common issues: JWT expired, offline queue full, Realtime disconnected, high latency; solutions with diagnostic commands), `SECURITY.md` (threat model, RLS policy rationale, JWT rotation strategy, rate limiting, audit logging); add `SHARED_COMPONENTS.md` (documents reused utilities from attendance system: ConnectivityMonitor, SyncQueueManager, ConfigLoader, CircuitBreaker, StructuredLogging patterns); add README.md with quickstart guide completing full setup in <30 minutes.

15. **Migration path from removed attendance system dashboard** (removed December 2024): document transition strategy in `docs/MIGRATION.md`:
   - Old `src/utils/admin_dashboard.py` (1277 lines, port 8080, SSE-based) → New React dashboard (port 443, Realtime-based)
   - Old `src/utils/multi_device_manager.py` → New `devices` table + RLS policies
   - Old `src/database/device_registry.py` → New Supabase `devices` table
   - Old `src/utils/realtime_monitor.py` → New `pi-agent/monitor_agent.py`
   - Old systemd service `attendance-dashboard.service` → New `iot-monitor-agent.service`
   - Create `scripts/migrate_from_old_dashboard.py` to backfill historical metrics from `data/logs/` into Supabase for continuity
   - Document that monitoring is now **completely independent** but can **optionally integrate** via adapter pattern
   - Add architecture diagram showing three integration modes:
     1. **Standalone Mode** - Monitor generic IoT devices, no attendance system
     2. **Sidecar Mode** - Monitor attendance system as one of many devices  
     3. **Deep Integration Mode** - Use attendance adapter to stream scan data

### Further Considerations

1. **Historical analytics database?** Option A: Keep 90-day raw data in Supabase Postgres with daily aggregates for long-term (acceptable for <100 devices), Option B: Add TimescaleDB extension to Supabase for efficient time-series queries with automatic partitioning (better for 100+ devices), Option C: Export old data to S3 via Supabase Storage and query via DuckDB/Athena for cost optimization (best for >1000 devices with cold storage). *Recommendation: Start with Option A, add `pg_partman` extension for automatic partitioning when device count exceeds 50.*

2. **Command security & audit trail?** Add `device_command_history` table logging all command executions with columns `command_id FK, executed_by uuid, execution_result jsonb, stdout text, stderr text, exit_code int, duration_ms int`; require dashboard users to authenticate via Supabase Auth (email/password or SSO) before issuing commands; add approval workflow for dangerous commands (reboot/factory_reset) via `command_approvals` table with two-person rule (command creator ≠ approver); log all command activity to Supabase Edge Function `audit-log` forwarding to external SIEM via webhook. *Recommendation: Implement basic audit trail (history table) in Phase 1, add approval workflow in Phase 2 if managing >10 devices.*

3. **Device provisioning at scale?** Create `scripts/bulk_provision.py` accepting CSV `device_id,name,location,building,floor,room` generating unique API secrets per device, inserting into Supabase `devices` table, creating device-specific config files `config-device-001.json` with pre-filled credentials; add `scripts/provision_from_fleet.sh` that SSHs to devices via Tailscale, copies config, installs agent, starts service; use Ansible playbook `playbooks/deploy_agent.yml` for 100+ device rollouts with parallel execution and rollback capability; add QR code generator creating unique setup codes encoding device credentials for mobile-based provisioning. *Recommendation: CSV + script for <50 devices, Ansible for 50+ devices.*