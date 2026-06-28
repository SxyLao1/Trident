# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.9.5] - 2026-06-28

### Added
- **Log Heuristic Engine** (`core/log_heuristic.py`): behavior-level detection from access logs with 5 detectors (brute force, scanner, error storm, known tools, suspicious paths)
- **SIEM Exporter** (`core/siem_exporter.py`): JSON Lines/CEF/Syslog export with auto-rotate file + UDP streaming
- **Memory Shell Tracer** (`core/memory_shell_tracer.py`): traces memory shell detection back to original WebShell file via access log correlation
- **Memory Shell Tools** (`tools/memory-shell/`): Java/ASP.NET reference scanners with upstream attribution (7 projects in README ecosystem section)
- **Gunicorn Config** (`gunicorn.conf.py`): multi-worker production WSGI deployment (2-4x CPU)
- **Core Test Suite**: 63 tests across 6 modules (log_heuristic, json_repo, sqlite_repo, siem_exporter, memory_shell_tracer, plugin_manager)
- **Dev Infrastructure**: `pyproject.toml` (pip install -e .), `pytest.ini`, `run_tests.bat`
- **Settings Frontend**: SIEM Export, Storage Status, Plugin Status panels

### Changed
- Settings page: added 3 new status cards (EXPORT & SIEM, STORAGE, PLUGINS)
- Config: `[plugins] enabled = true`, `[storage] backend = "both"`, `[siem] enabled = true`
- Version: config.toml → v1.9.5-dev

### Fixed
- File Clusters page: `stats` undefined in template (now computed from cluster data)
- Test suite: IIS parser, tool detection thresholds, DualWrite schema compatibility

## [1.9.0–1.9.4] - 2026-06-28

### Added — Architecture (v1.9.0)
- **Blueprint split**: admin_bp.py 3767→2155 lines, 4 independent Blueprints (scanner, blocklist, profiles, records) — 86 total endpoints
- **JS modularization**: dashboard.js 1455→561 lines, 4 page modules in `js/modules/`
- **Interface layer**: `core/interfaces/` — 5 ABCs (Plugin, Detector, Repository, Notifier, EventSource)
- **Repository layer**: `core/repositories/` — JsonRepository (thread-safe atomic write) + DualWriteRepository
- **Shared helpers**: `web/blueprints/_shared.py` — file verification, SSE token, rate limiting

### Added — Storage (v1.9.2)
- **SQLite backend** (`core/repositories/sqlite_repository.py`): WAL mode, 5 tables auto-create, indexes, transactions
- **Dual-write mode**: JSON safety net + SQLite read priority, configurable via `[storage] backend`

### Added — Plugins (v1.9.3–v1.9.4)
- **Plugin Manager** (`core/plugin_manager.py`): singleton lifecycle manager, event dispatch, config-driven loading
- **stdout_logger**: colored terminal alert plugin (Plugin + Notifier interface)
- **WAF Adapters**: ModSecurity JSON audit, Cloudflare GraphQL, AWS WAF CloudWatch, Syslog CEF (4 adapters)
- Config: `[plugins]` section with per-plugin configuration

## [1.8.4] - 2026-06-27

### Added
- **Manual Scanner**: active directory scanning with SSE real-time progress, YARA + static analysis
- **Batch Operations**: cross-page multi-select for Records and Quarantine with batch quarantine/restore/delete/FP
- **File Clusters Tab**: ssdeep/TLSH/SimHash similarity clustering view in Threats page
- **Record Detail → Profile linking**: linked threat profiles shown in record detail modal
- **Scan History**: persistent scan results in `data/scans/`, restorable via history panel
- **Scan Reports**: printable HTML reports with findings summary
- **`detection_source` field**: differentiates passive (Watchdog) vs active (Manual Scanner) detections
- Static JS protection: unauthenticated access returns 404

### Changed
- **UI Consolidation**: Records/Quarantine toolbars unified into single-row layout with inline search
- Scanner page: three-card layout (Config / Results / History) with auto-collapse
- Records rows: only Source + Detail per-row; batch actions moved to toolbar
- Audit Log pagination: unique container IDs for Active/Audit tabs
- Toolbar selectors: class-based instead of ID-based to prevent duplicate-ID bugs
- `suspicious_registry.add()` accepts `detection_source` parameter

### Fixed
- File viewer backslash corruption on Windows paths (switched to `dataset.path`)
- Audit Log pagination unresponsive (duplicate `#records-table-container` ID)
- Audit Log page-jump missing `audit` parameter
- Overview ACTIVE THREATS quadrant scrollbar missing
- IP checkbox manual toggle not updating selection Set
- IP Select All only capturing current page
- Scanner SSE crash (`current_app.logger` outside app context)
- Scanner progress bar stuck (added threading + queue architecture)
- Quarantined records leaking into Active Threats list
- Records showing Restore button on active threats

---

## [1.7.9] - 2026-06-25

### Added
- Automated file quarantine: `core/quarantine.py` with isolate/restore/delete
- Recursive webshell scan tool: `tools/recursive_webshell_scan.py`
- Shared auth module: `web/auth.py`
- Smart notification batching: success aggregated (50/batch or 5min), failure immediate
- Restore whitelist: 30s TTL prevents re-quarantine of restored files
- Playwright-based automated frontend testing
- `sync_to_runtime.bat` for instant test deployment
- Quarantine detail modal with inline content loading

### Changed
- Registry+Quarantine pipeline unified in `_do_scan()` (single transaction)
- `scanner.py` no longer has side effects (pure scan only)
- Log symbols reorganized: 98 symbols across 13 functional modules
- Versioning: single source of truth in `config.toml` → `config/version.py`
- Terminal output: emoji replaced with `[OK]/[ERR]/[WARN]` labels
- Records page: shows only active threats (quarantined files in Audit view)
- Git tag versioning replaces directory-based backup

### Fixed
- 6 security vulnerabilities (V-001~V-006): auth bypass, path traversal, info leak, rate limiting
- 5 quarantine pipeline bugs: async race, atomic write indent, file_size timing, DELETE overwrite, orphan records
- Quarantine detail/pagination: HTMX CSRF injection, audit pagination params, block template overrides
- Record detail modal: blur overlay not removed on close
- Login spam: empty-username POSTs no longer log as failures
- `loadDashboard()` no longer overwrites quarantine/audit page content
- `__pycache__` excluded from git

### Security
- V-001/V-002: YARA rules unauthorized read/write (CRITICAL) — all `/admin/yara/*` routes now require auth
- V-003: YARA search unauthorized access (HIGH)
- V-004: Path traversal DoS (MEDIUM) — unified `_validate_rule_path()` with null byte detection
- V-005: Server info leak (LOW) — Werkzeug version hidden via monkey-patch
- V-006: Login brute force (LOW) — in-memory rate limiter (5/min/IP)

---

## [1.8.0-dev] - In Development

### Added
- Navigation refactor: 6→4 items (Overview/Threats/Rules/Settings)
- Web Config Panel + dynamic config.toml editor + structured .env editor
- Log Analyzer with 4-dimension filtering
- System modals, Threats tabs, YARA batch operations

### Changed
- LIVE LOG reads history from monitor.log
- Page toolbars stay in content, header reserved for multi-site selector

### Fixed
- HTMX script execution, modal overlay persistence, audit pagination, SSE buffer

---

## [1.8.3] - 2026-06-26

### Added
- Attacker Profiling Engine: UA+time clustering, IP-overlap merge, decay visualization
- File Similarity Clustering: 3-track hash engine (ssdeep/py-tlsh/SimHash)
- WebShell Decoder Filter: Multi-pass deobfuscation before YARA scan
- IP Blocker: Multi-device broadcast, retry queue with exponential backoff
- Mock WAF Server: 4 scenarios, time-compressed, stateful polling
- Report Generator: Printable HTML with MITRE ATT&CK + timeline
- Log Analyzer: Full-screen 4-dimension filtering
- Dynamic Config Editor: Tree view + search + .env editor
- Threats Tabs + YARA Batch Operations

### Changed
- Navigation: 6 → 5 items (Overview/Threats/Rules/Profiles/Settings)
- Profile ID: UA+time only, URL downgraded to metadata
- LIVE LOG reads from monitor.log

### Fixed
- Quarantine pipeline 5 bugs, HTMX script execution, 6 security vulns

---

## [1.7.8] - 2026-05-27

### Added
- Modular installer architecture: `scripts/install.py` handles all install logic; `install.sh`/`install.bat` are minimal entry wrappers
- Config-aware installation: reads existing `config.toml` and offers Keep / Overwrite / Review modes
- Launcher scripts: `start.sh`/`start.bat` (foreground), `start_background.sh`/`start_background.bat` (background), `stop.sh`/`stop.bat`, `uninstall.sh`/`uninstall.bat`
- Systemd service template for Linux auto-start
- Full documentation overhaul with badges, quick start, and troubleshooting
- CHANGELOG and RELEASE_NOTES in both English and Chinese

### Changed
- Zero hardcoding: install scripts no longer embed version numbers; version cascades from `config.toml` through `config/version.py`
- `banner.txt` includes version and release date metadata
- `ci.yml` workflow name synchronized with current version

### Fixed
- `install.bat` Python detection rewritten for Windows (fixed failure on Python 3.12)
- `install.sh` Python detection now tries python3, python, py3, py in order
- README-cn.md fully rewritten to match v1.7.8 feature set

---

## [1.7.7] - 2026-05-26

### Added
- Cyberpunk terminal frontend: dark theme with neon green accent, Canvas matrix-rain login animation
- CSS/JS modularization: 6 CSS files + 4 JS files
- WAL high-cohesion migration: all WAL functionality extracted to `core/wal_manager.py`
- Full-site CSRF protection via Flask-WTF
- Records single-view with inline false-positive toggle
- SSE history embedding: backend directly embeds log buffer into dashboard template
- Zero-hardcoding pagination: all pagination params read from `config.toml`
- Batch operations for Records and YARA rules
- Navigation simplified to Dashboard / System / Account

### Changed
- Frontend theme switched from light/admin-style to cyberpunk dark terminal
- `suspicious_registry.py` no longer manages WAL
- SSE log stream now embeds history server-side

### Fixed
- Container nesting bug when switching panels via innerHTML replacement
- YARA upload modal not available in compact mode (moved to global scope)
- CSRF token missing on HTMX POST requests
- Version number inconsistency across config files

### Security
- Full-site CSRF protection
- IP whitelist for admin access
- Scrypt password hashing with strength validation

---

## [1.7.6] - 2026-01-20

### Added
- SSE refactoring: native EventSource replaces HTMX SSE extension
- Account security management: password change with strength validation
- System management quadrants: Registry / WAL / Session / Config
- Ghost directory detection with lazy cache
- `utils/sse_manager.py`: independent SSE push manager
- `utils/password_utils.py`: password strength validation
- `tools/ci_quick_validator.py`: CI quick validation

### Changed
- Metrics panel switched from SSE to HTMX polling (10s interval)
- Registry update debounced to 500ms

### Fixed
- SSE connection leaks and duplicate refresh issues
- Session authentication edge cases
- Config hot-reload persistence failures

---

## [1.7.5] - 2025-12

### Added
- Ghost directory detection with LRU cache (capacity 100)
- Wildcard log path support: `**/access.log` recursive matching
- Session authentication with filesystem backend
- Three-layer intelligent alerting with exponential backoff

### Changed
- Windows polling optimized with directory cache TTL

---

## [1.7.0] - 2025-11

### Added
- HTMX-based management frontend (zero Node.js dependency)
- WAL transaction logs for write reliability
- Three-layer alerting: exponential backoff + adaptive thresholds
- Cross-platform monitoring: Linux Inotify / Windows polling auto-switch
- YARA rule engine integration
- Webhook / WeChat / Email multi-channel notifications

---

## [1.0.0] - 2025

### Added
- Initial release: file system monitoring + basic alerting
