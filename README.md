<div align="center">

<pre>
 _____     _     _            _   
|_   _| __(_) __| | ___ _ __ | |_ 
  | || '__| |/ _` |/ _ \ '_ \| __|
  | || |  | | (_| |  __/ | | | |_ 
  |_||_|  |_|\__,_|\___|_| |_|\__|
</pre>

<h1>Trident WebShell Detector</h1>

<p>
  <a href="README-cn.md">中文</a> | <strong>English</strong>
</p>

<p>
  <img src="https://img.shields.io/badge/version-1.9.5-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/status-dev--stable-success?style=flat-square" alt="Status">
  <img src="https://img.shields.io/badge/python-3.8%2B-green?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
</p>

<p>Cross-Platform WebShell Detection System with Real-time Monitoring</p>

</div>

---

Trident is a production-grade WebShell detection system for Linux and Windows. It monitors file system changes in real time, detects WebShells using an embedded YARA rule engine, and provides a web-based management dashboard.

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
- **Plugin system** — Config-driven plugin manager with lifecycle, event dispatch, 4 WAF adapters (ModSecurity/Cloudflare/AWS/Syslog)
- **Dual storage** — JSON + SQLite (WAL mode) with configurable backend switching and auto-migration
- **WAL transaction logs** — Async batch writes with auto rotation, minimal data loss under file locking
- **Smart alerting** — Exponential backoff with adaptive thresholds to reduce false positives
- **Web dashboard** — Dark theme terminal-style interface, SSE real-time log stream, HTMX-driven, SPA navigation
- **Enterprise security** — CSRF protection, IP whitelist, Scrypt password hashing, static JS auth guard
- **Production deployment** — Gunicorn multi-worker config, systemd service, pip install -e . dev setup
- **Core test suite** — 63 tests across 6 modules, one-click Windows runner

## Quick Start

### Linux / macOS

```bash
git clone https://github.com/SxyLao1/Trident.git
cd trident
chmod +x install.sh
./install.sh
```

### Windows

```powershell
git clone https://github.com/SxyLao1/Trident.git
cd trident
.\install.bat
```

The installer auto-detects Python, creates a virtual environment, installs dependencies, and prompts for configuration (website path, admin password, allowed IPs).

### Docker

```bash
docker-compose up -d
```

Then open `http://127.0.0.1:8080`. Default username is `admin`; password is printed in the console during first setup.

## Project Structure

```
Trident/
├── app.py                  # Entry point
├── config.toml             # Main configuration
├── pyproject.toml          # pip install -e . dev setup
├── gunicorn.conf.py        # Production WSGI deployment
├── config/                 # Config loader & registry
├── core/                   # Detection engine, WAL, metrics, notifier
│   ├── interfaces/         # Plugin/Detector/Repository/Notifier ABCs
│   ├── repositories/       # JSON + SQLite storage implementations
│   └── similarity/         # ssdeep/TLSH/SimHash hash engine
├── plugins/                # Plugin ecosystem (stdout_logger, WAF adapters)
├── web/                    # Flask blueprints, templates, static assets
├── rules/webshell/         # YARA rule files
├── tools/memory-shell/     # Java/ASP.NET reference scanners
├── scripts/                # Installers & service templates
└── tests/core/             # 63-test suite (pytest)
```

## Requirements

- Python 3.8+
- yara-python
- Flask + Flask-WTF
- psutil (Windows monitoring optimization)

See `requirements.txt` for the full list.

## Security Notes

- Change the default `secret_key` in production
- Restrict `allowed_ips` to your management network
- Generate a strong admin password via `python tools/admin_passwd.py`
- Use HTTPS when exposing to public networks

## Ecosystem & Related Projects

Trident is designed to complement these excellent open-source tools:

**Memory Shell Detection** (bundled in `tools/memory-shell/`):
- [c0ny1/java-memshell-scanner](https://github.com/c0ny1/java-memshell-scanner) — JSP-based Tomcat/Jetty/WebLogic memory shell scanner
- [yzddmr6/As-Exploits](https://github.com/yzddmr6/As-Exploits) — ASP.NET memory shell scanner (VirtualPath/Filter/Router)
- [private-xss/memory-shell-detector](https://github.com/private-xss/memory-shell-detector) — Java GUI+CLI memshell detector (MIT)
- [4ra1n/shell-analyzer](https://github.com/4ra1n/shell-analyzer) — GUI JVM monitor with decompile & kill
- [y1shiny1shin/KMBA](https://github.com/y1shiny1shin/KMBA) — Arthas-based memshell killer (12 types)

**WAF / Log Analysis**:
- [SpiderLabs/ModSecurity](https://github.com/SpiderLabs/ModSecurity) — WAF engine (Trident ingests audit logs)
- [SpiderLabs/owasp-modsecurity-crs](https://github.com/SpiderLabs/owasp-modsecurity-crs) — OWASP Core Rule Set

**Hashing & Similarity**:
- [ssdeep-project/ssdeep](https://github.com/ssdeep-project/ssdeep) — CTPH fuzzy hashing (C implementation)
- [trendmicro/tlsh](https://github.com/trendmicro/tlsh) — Trend Micro Locality Sensitive Hash

## License

MIT License. Free for production, academic research, and personal use.

Third-party tools bundled in `tools/` retain their original licenses. See `tools/memory-shell/README.md` for attribution details.

---

<div align="center">
  <sub>Trident Security Platform — MIT License</sub>
</div>
