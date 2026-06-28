# Roadmap

> **Current Version**: v1.9.5-dev (2026-06-28)  
> **Next Milestone**: v1.10.0 (Multi-Site) / v2.0 (Architecture)  
> **Vision**: Lightweight Web Perimeter Security — Passive Detection + Semi-Active Response

---

## v1.7.9 — Quarantine Pipeline + Security Hardening ✅ (Complete)

See [CHANGELOG.md](./CHANGELOG.md).

---

## v1.8.0 — Web Config Panel + Threat Detection Expansion ✅ (Complete, 2026-06-21)

| # | Feature | Status |
|---|---------|--------|
| 1 | Auto file quarantine | ✅ |
| 2 | IP auto-blocking | ✅ |
| 3 | IP blocking API | ✅ |
| 7 | Webhook alerts | ✅ |
| 9 | MITRE ATT&CK tags | ✅ |
| 10 | Attack chain reconstruction | ✅ |

---

## v1.8.1–v1.8.4 — Profile Engine + Scanner + Batch Ops + Block Ledger ✅ (Complete, 2026-06-27)

Major additions since v1.8.0:

| Feature | Status |
|---------|--------|
| Threat profiling (UA+time+IP pool+decay) | ✅ |
| File similarity clustering (ppdeep/TLSH/SimHash) | ✅ |
| Manual scanner (SSE progress + history + reports) | ✅ |
| Batch operations (Records + Quarantine cross-page select) | ✅ |
| Block audit ledger (persistent + editable notes + export) | ✅ |
| Multi-device broadcast (dynamic device toggles) | ✅ |
| Bidirectional links (Records ↔ Profiles) | ✅ |
| File Clusters tab in Threats | ✅ |
| Security: static JS auth guard, CSRF, file viewer whitelist | ✅ |
| ppdeep pure-Python CTPH for Windows | ✅ |

---

## v1.9.x — Architecture Refactoring + Plugin Ecosystem ✅ (Mostly Complete, 2026-06-28)

### v1.9.0 — Blueprint Split + Interface Layer ✅
| Feature | Status |
|---------|--------|
| Blueprint split (admin_bp.py 3767→2155, 4 new BPs) | ✅ |
| JS modularization (dashboard.js 1455→561, 4 page modules) | ✅ |
| core/interfaces/ — 5 ABCs (Plugin, Detector, Repository, Notifier, EventSource) | ✅ |
| core/repositories/ — JsonRepository + DualWriteRepository | ✅ |
| web/blueprints/_shared.py — common helpers | ✅ |

### v1.9.1–v1.9.2 — Storage + Performance ✅
| Feature | Status |
|---------|--------|
| SQLite backend (WAL mode, 5 tables, auto-migration) | ✅ |
| DualWriteRepository (JSON safety net + SQLite read priority) | ✅ |
| config.toml: `[storage] backend = "json" | "sqlite" | "both"` | ✅ |

### v1.9.3–v1.9.4 — Plugin Ecosystem ✅
| Feature | Status |
|---------|--------|
| Plugin Manager (singleton, lifecycle, event dispatch) | ✅ |
| stdout_logger plugin (colored terminal alerts) | ✅ |
| WAF adapters: ModSecurity, Cloudflare, AWS WAF, Syslog | ✅ |
| config.toml: `[plugins] enabled = true` | ✅ |

### v1.9.5 — Detection Pipeline + SIEM + Tests ✅
| Feature | Status |
|---------|--------|
| Log Heuristic Engine (5 behavioral detectors) | ✅ |
| SIEM CEF/JSON Lines exporter (file + syslog UDP) | ✅ |
| Memory Shell Tracer (access log → WebShell file correlation) | ✅ |
| Memory Shell reference tools (JSP/ASPX, upstream attribution) | ✅ |
| Gunicorn production config (multi-worker, 2-4x CPU) | ✅ |
| Core test suite (63 tests, 6 modules) | ✅ |
| pyproject.toml + pip install -e . dev setup | ✅ |
| Settings frontend: SIEM Export, Storage, Plugin status panels | ✅ |
| README ecosystem section (7 upstream projects credited) | ✅ |

### Pending (v1.10.0 / v2.0)

| Priority | Feature | Notes |
|----------|---------|-------|
| P0 | Multi-site support | `[[website]]` array, per-site isolation |
| P1 | Java Memory Shell Agent PoC | Custom Java agent for reflection detection |
| P1 | Geo-IP integration | MaxMind GeoLite2 |
| P2 | Admin 2FA | TOTP, login rate limiting |
| P2 | API key management | Scoped keys for external systems |
| P3 | Threat intelligence | MISP / AbuseIPDB integration |

---

## v2.0-alpha — Architecture Refactoring (2026-Q3/Q4)

**Goal**: Upgrade from "script project" to "Python package" with clean architecture.

**Structural Changes**:
- Add `pyproject.toml` for `pip install -e .`
- Move `app.py` to `src/trident/` package structure
- Introduce `domain/ports.py` abstraction layer
- Separate domain / application / infrastructure layers
- Plugin contracts for new detection engines
- Storage abstraction: `JsonEventRepository` → `SQLiteEventRepository`

**Target Layout**:
```
trident/
├── pyproject.toml
├── src/trident/
│   ├── domain/      (models, ports, events)
│   ├── application/ (use cases, plugin manager)
│   ├── infrastructure/ (persistence, config, web, monitoring)
│   └── interfaces/  (CLI, API, dashboard)
└── plugins/
```
