<div align="center">

<img src="assets/anteumbra-logo.svg" width="120" alt="Anteumbra">

# Anteumbra

<img src="https://img.shields.io/badge/version-2.0.0.dev0-blue?style=flat-square" alt="Version">
<img src="https://img.shields.io/badge/python-3.8%2B-green?style=flat-square" alt="Python">
<img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
<img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
<img src="https://img.shields.io/badge/tests-79%2F79-brightgreen?style=flat-square" alt="Tests">

**Lightweight Web Perimeter Security** — Passive Detection · Semi-Active Response

</div>

---

Anteumbra (formerly Trident) is a production-grade WebShell detection system for Linux and Windows. It monitors file system changes in real time, detects WebShells using an embedded YARA rule engine, and provides a web-based management dashboard.

Key capabilities:

- **Real-time file monitoring** — Linux Inotify / Windows ReadDirectoryChangesW adaptive switching
- **Manual scanner** — Active directory scanning with SSE real-time progress, scan history, printable reports
- **YARA rule engine** — 18+ rule files covering PHP, ASP, JSP, ASPX, Godzilla, Behinder; hot-reload supported
- **Threat profiling** — Attacker behavior clustering via UA/time-bucket, IP pool merging, decay engine
- **File similarity clustering** — ssdeep/TLSH/SimHash hash engine with 0.80 threshold grouping
- **Log heuristic engine** — Behavior-level detection: brute force, scanner, error storm, tool signature, suspicious path
- **Memory shell detection** — Java/ASP.NET reference tools + access log tracer for WebShell origin correlation
- **Batch operations** — Cross-page multi-select for Records/Quarantine with batch quarantine/restore/delete
- **SIEM export** — CEF/JSON Lines/Syslog formats with file rotation and real-time UDP streaming
- **Plugin system** — Config-driven plugin manager with lifecycle, event dispatch, 4 WAF adapters
- **Dual storage** — JSON + SQLite (WAL mode) with configurable backend switching and auto-migration
- **WAL transaction logs** — Async batch writes with auto rotation, minimal data loss under file locking
- **Smart alerting** — Exponential backoff with adaptive thresholds to reduce false positives
- **Web dashboard** — Dark theme terminal-style interface, SSE real-time log stream, HTMX-driven, SPA navigation
- **Enterprise security** — CSRF protection, IP whitelist, Scrypt password hashing, static JS auth guard
- **Production deployment** — Gunicorn multi-worker config, systemd service, `pip install -e .` dev setup
- **Core test suite** — 79 tests across 7 modules, one-click Windows runner

## Quick Start

```bash
pip install anteumbra
anteumbra --help
```

### From Source

```bash
git clone https://github.com/SxyLao1/Anteumbra.git
cd Anteumbra
pip install -e .
python -m pytest tests/core/ -v
```

### Windows

```powershell
git clone https://github.com/SxyLao1/Anteumbra.git
cd Anteumbra
.\run_tests.bat
```

Then open `http://127.0.0.1:8080`. Default username is `admin`; password is printed in the console during first setup.

## Architecture

```
src/anteumbra/
├── domain/               # Domain layer: entities + ports (Plugin, Repository, Detector, Notifier, EventSource)
├── application/          # Application layer: PluginManager (lifecycle, event dispatch)
├── infrastructure/       # Infrastructure: persistence (JSON/SQLite), detection, monitoring, config, utils
└── interfaces/           # Interfaces: Flask blueprints, templates, static assets
```

Architecture Decision Records (ADRs) are documented in `PROJECT_MASTER_Trident-Anteumbra.md`.

## Ecosystem & Related Projects

Anteumbra is designed to complement these excellent open-source tools:

**Memory Shell Detection**:
- [c0ny1/java-memshell-scanner](https://github.com/c0ny1/java-memshell-scanner) — JSP-based Tomcat/Jetty/WebLogic scanner
- [yzddmr6/As-Exploits](https://github.com/yzddmr6/As-Exploits) — ASP.NET memory shell scanner
- [private-xss/memory-shell-detector](https://github.com/private-xss/memory-shell-detector) — Java GUI+CLI detector (MIT)

**WAF / Log Analysis**:
- [SpiderLabs/ModSecurity](https://github.com/SpiderLabs/ModSecurity) — WAF engine
- [SpiderLabs/owasp-modsecurity-crs](https://github.com/SpiderLabs/owasp-modsecurity-crs) — OWASP Core Rule Set

**Hashing & Similarity**:
- [ssdeep-project/ssdeep](https://github.com/ssdeep-project/ssdeep) — CTPH fuzzy hashing
- [trendmicro/tlsh](https://github.com/trendmicro/tlsh) — Trend Micro Locality Sensitive Hash

## Migration from Trident

Anteumbra is the successor to [Trident](https://github.com/SxyLao1/Trident) (v1.9.5). If you were using Trident:

```bash
# Uninstall old package
pip uninstall trident-webshell

# Install Anteumbra
pip install anteumbra

# Your config.toml and data/ directory are compatible
```

## License

MIT License. Free for production, academic research, and personal use.

Third-party tools bundled in `tools/` retain their original licenses.

---

<div align="center">
  <sub>Anteumbra v2.0 — MIT License</sub>
</div>
