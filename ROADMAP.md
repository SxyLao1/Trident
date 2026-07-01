# Anteumbra Roadmap

> **Current Version**: v1.0.1 (2026-07-01)  
> **Vision**: Web Perimeter Threat Intelligence — Passive Detection · Semi-Active Response · File-Level Forensics  
> **Status**: DDD architecture migrated, 79/79 tests passing, frontend bugs fixed

---

## v1.0.0-dev — Anteumbra Reborn (Current)

Anteumbra is a fresh start. Trident v1.9.5 is archived at `legacy-trident-v1.9.5` tag.

| Milestone | Status |
|-----------|--------|
| Trident v1.9.5 → Anteumbra rename | Done |
| DDD four-layer architecture | Done |
| `pip install anteumbra` package | Done |
| Unified CLI (`anteumbra run|start|stop|status|config`) | Done |
| Flask-Babel i18n (en/zh, auto-detect) | Done |
| Registry format normalization (dict/list consistency) | Done |
| Quarantine logging + status tracking | Done |
| Batch operation CSRF + stats refresh | Done |
| Audit Log status badges (FP/DEL/ALERT/ACTIVE) | Done |
| Scanner cross-page selection + quarantine UX | Done |
| Bilingual README (EN/ZH) | Done |
| SVG logo + professional README | Done |
| 79/79 core tests passing | Done |

### v1.0.0 Release Checklist

| Item | Status |
|------|--------|
| Registry persistence stability (dict→list fix) | Done |
| i18n translations path fix + lang cookie | Done |
| Frontend batch ops JSON error handling | Done |
| Quarantine → Active Threats removal | Done |
| False Positive → Security Report update | Done |
| Template `_()` i18n coverage (full pass) | Pending |
| v1.9.0 plan: Block Ledger + Bidirectional Links + Broadcast | Pending |
| End-to-end integration test suite | Pending |
| PyPI first release | Pending |

---

## v1.9.x — Architecture + Ecosystem (Trident, Archived)

See [Trident CHANGELOG](https://github.com/SxyLao1/Trident/blob/main/CHANGELOG.md) for v1.7.9–v1.9.5 details.

**Key accomplishments (2025–2026):**
- Blueprint split (3767→2155 lines), JS modularization (1455→561)
- SQLite backend (WAL mode) + DualWriteRepository
- Plugin Manager + stdout_logger + 4 WAF adapters
- Log Heuristic Engine + SIEM CEF/JSON Lines exporter
- Memory Shell Tracer + reference tools
- Gunicorn production config + Core test suite (79 tests)
- Code quality fixes: SQL injection, thread safety, timezone handling

---

## v1.1.0 — Multi-Site + Geo-IP (Planned)

| Priority | Feature |
|----------|---------|
| P0 | Multi-site support (`[[website]]` array) |
| P1 | Geo-IP integration (MaxMind GeoLite2) |
| P1 | Java Memory Shell Agent PoC |
| P2 | Admin 2FA (TOTP) + API key management |
| P2 | MISP / AbuseIPDB threat intelligence |
| P3 | EventBus (asyncio) + Pydantic Schema migration |

## v1.2.0 — Production Hardening

| Priority | Feature |
|----------|---------|
| P0 | Docker multi-arch image |
| P1 | Redis session backend |
| P1 | Prometheus metrics endpoint |
| P2 | CI/CD pipeline (GitHub Actions) |
| P2 | SIEM syslog live streaming (completed, needs integration) |
