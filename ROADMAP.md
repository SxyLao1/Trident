# Roadmap

> **Current Version**: v1.8.4-stable (2026-06-27)  
> **Next Milestone**: v1.9.0  
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

## v1.9.x — SQLite + Multi-Site + WAF Adapters (2026-Q3)

**Priority items**:
1. **SQLite persistence** — replace JSON for performance
2. **Multi-site support** — [[website]] array
3. **WAF standard adapters** — ModSecurity/Cloudflare/AWS/Syslog
4. **gunicorn deployment** — multi-worker
5. **SIEM export** (CEF/Syslog)
6. **Core module tests** — 80%+ coverage + CI/CD
7. **Memory shell plugin** — Java reflection PoC
8. **Log heuristic engine** — behavior-level detection

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
