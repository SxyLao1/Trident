# Roadmap

> **Current Version**: v1.7.8 (Stable)  
> **Next Milestone**: v1.8.0  
> **Vision**: Lightweight Web Perimeter Security — Passive Detection + Semi-Active Response

---

## v1.8.0 — Threat Detection Expansion (2026-Q3)

**Goal**: Expand from "WebShell-only" to "Web-layer threat detection platform".

**Core Principles**:
- Passive detection first: file system monitoring + log analysis, no HTTP interception
- Semi-active response: auto-quarantine files + IP blocking upon detection, leave HTTP filtering to Nginx/WAF
- Open APIs: IP blocking API for integration with existing WAF/FW
- Attack surface reduction: admin panel hardening, multi-site support, no version exposure in frontend

**Planned Features**:

| # | Feature | Module | Complexity |
|---|---------|--------|------------|
| 1 | Auto file quarantine | `core/quarantine.py` | Low |
| 2 | IP auto-blocking (local blacklist) | `core/ip_blocker.py` | Medium |
| 3 | IP blocking API (external WAF/FW) | `core/ip_blocker.py` | Medium |
| 4 | Process behavior monitoring | `core/process_monitor.py` | Medium |
| 5 | Memory shell plugin architecture | `plugins/java-memshell/` | High |
| 6 | PE/EXE upload detection | `core/pe_detector.py` | Low |
| 7 | Webhook alerts (DingTalk/WeCom/Feishu) | `core/notifier.py` | Low |
| 8 | SIEM export (JSON Lines / CEF / Syslog) | `utils/siem_formatter.py` | Medium |
| 9 | MITRE ATT&CK tags | Event schema | Low |
| 10 | Attack chain reconstruction | Dashboard timeline | Medium |

**Design Decisions**:

- **IP Blocking**: "Event Emitter, Not Executor" — maintain internal blacklist table + webhook output; let external WAF/FW execute blocks
- **Auto-Response**: Three-tier confidence (Low/Medium/High) with configurable thresholds
- **Memory Shell**: Plugin architecture with subprocess orchestration; no JVM/CLR embedded in Python
- **Storage**: v1.8 stays JSON; v1.9 introduces SQLite (optional) behind abstraction layer

---

## v1.9.x — Multi-Site + Ecosystem (2026-Q4)

- Multi-site monitoring: `[[website]]` array in `config.toml`, single Dashboard for all sites
- Site isolation: independent registry/WAL per site or shared central WAL
- Centralized alerting: one webhook with `site_id` tag
- Geo-IP: MaxMind GeoLite2 integration
- Threat intelligence: MISP / AbuseIPDB integration
- Admin panel hardening: 2FA (TOTP), login rate limiting, brute-force detection
- API key management: scoped keys for external systems
- SQLite default backend

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
