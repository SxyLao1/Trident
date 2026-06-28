# Anteumbra Roadmap

> **Current Version**: v2.0.0.dev0 (2026-06-28)  
> **Vision**: Lightweight Web Perimeter Security — Passive Detection + Semi-Active Response  
> **Status**: DDD architecture migrated, 79/79 tests passing

---

## v2.0.0 — Rename + Architecture Migration ✅ (Complete)

| Milestone | Status |
|-----------|--------|
| Trident v1.9.5 → Anteumbra v2.0.0 | ✅ |
| DDD four-layer architecture | ✅ |
| `pip install anteumbra` package | ✅ |
| SVG logo + professional README | ✅ |
| 79/79 core tests passing | ✅ |

## v1.9.x — Architecture + Ecosystem (Trident) ✅

See [Trident CHANGELOG](https://github.com/SxyLao1/Trident/blob/main/CHANGELOG.md) for v1.7.9–v1.9.5 details.

**Key accomplishments (2026-06-28):**
- Blueprint split (3767→2155 lines), JS modularization (1455→561)
- SQLite backend (WAL mode) + DualWriteRepository
- Plugin Manager + stdout_logger + 4 WAF adapters
- Log Heuristic Engine + SIEM CEF/JSON Lines exporter
- Memory Shell Tracer + reference tools
- Gunicorn production config + Core test suite (79 tests)
- Code quality fixes: SQL injection, thread safety, timezone handling

## v2.1.0 — Multi-Site + Geo-IP (Planned)

| Priority | Feature |
|----------|---------|
| P0 | Multi-site support (`[[website]]` array) |
| P1 | Geo-IP integration (MaxMind GeoLite2) |
| P1 | Java Memory Shell Agent PoC |
| P2 | Admin 2FA (TOTP) + API key management |
| P2 | MISP / AbuseIPDB threat intelligence |
| P3 | EventBus (asyncio) + Pydantic Schema migration |

## v2.2.0 — Production Hardening

| Priority | Feature |
|----------|---------|
| P0 | Docker multi-arch image |
| P1 | Redis session backend |
| P1 | Prometheus metrics endpoint |
| P2 | CI/CD pipeline (GitHub Actions) |
| P2 | SIEM syslog live streaming (completed, needs integration) |
