# Trident v1.7.9 Release Notes

> **Status**: v1.7.9-stable  
> **Release Date**: 2026-06-25

---

## Overview

v1.7.9 "Stable" is a major reliability and security release. Key upgrades: unified quarantine pipeline eliminating data inconsistency, 6 security vulnerability fixes, smart notification batching, and comprehensive log symbol standardization.

---

## Security Fixes

- **V-001/V-002 (CRITICAL)**: YARA rules were readable/writable without authentication. All `/admin/yara/*` routes now require `@require_auth`. Extracted shared `web/auth.py` module.
- **V-003 (HIGH)**: YARA search endpoint unauthenticated — fixed.
- **V-004 (MEDIUM)**: Path traversal via `../` and null-byte injection causing 500 errors. Unified `_validate_rule_path()` now rejects traversal attempts.
- **V-005 (LOW)**: Server header exposed Werkzeug/Python versions. Monkey-patched at `WSGIRequestHandler` level.
- **V-006 (LOW)**: Login brute force possible. In-memory rate limiter: 5 attempts/min/IP.
- Global HTMX CSRF token injection for all `hx-post` requests.

## Quarantine Pipeline (5 Critical Bugs Fixed)

- **Unified transaction**: `add()` moved from `scanner.py` to `_do_scan()` — registration + quarantine + mark in single try block.
- **Atomic write**: `.tmp` → `.bak` → `replace` prevents data corruption on crash.
- **Auto-recovery**: `_load_db()` rebuilds from disk files if `quarantine.json` is missing or corrupt.
- **Race condition**: `mark_quarantined` uses `_save_registry_sync()`; `remove()` preserves existing `quarantine_id`.
- **Timing fix**: `file_size` captured before `shutil.move()` (was called after the file was already moved).
- **Memory snapshot**: `_load_registry()` prefers `_last_registry_snapshot` to avoid stale disk reads during async save window.

## Smart Notifications

- **Quarantine success**: Batched — aggregated every 50 files or 5 minutes.
- **Quarantine failure**: Immediate per-file alert (requires human attention).
- **Restore whitelist**: Restored files excluded from re-quarantine for 30 seconds.

## Frontend

- Quarantine Restore/Delete return HTML fragments (not JSON), preserving page state.
- Audit pagination preserves `audit` mode across page navigation.
- Quarantine filter links use `hx-get` (no full page reload, sidebar state preserved).
- `loadDashboard()` no longer overwrites non-dashboard pages (quarantine, audit).
- Record Detail modal close properly removes blur overlay (`classList.remove('active')`).
- Metrics and Records auto-refresh every 10 seconds via HTMX polling.

## Logging & Observability

- 98 log symbols reorganized into 13 functional modules (MONITOR, SCAN, QUARANTINE, REGISTRY, etc.).
- All `[UNKNOWN]` symbol prefixes eliminated.
- Terminal output: emoji replaced with `[OK]`/`[ERR]`/`[WARN]` labels.
- Version single source of truth: `config.toml` → `config/version.py`.

## Upgrade from v1.7.8

```bash
git checkout main && git pull
pip install -r requirements.txt  # quarantine module added
python scripts/install.py        # re-run installer
```

No database migration needed — quarantine.json is auto-recovered on first load.

## Known Issues

- 266 scan count may differ from Registry entries (some files scanned as SAFE by YARA).
- Full `logger` → `log_with_symbol` migration deferred to v2.0 (different loggers route to different files).
- Werkzeug dev server; production use requires Gunicorn (v2.0 migration).

---

*Full changelog: [CHANGELOG.md](./CHANGELOG.md)*  
*中文版: [RELEASE_NOTES_v1.7.9-cn.md](./RELEASE_NOTES_v1.7.9-cn.md)*
