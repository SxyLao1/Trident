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
  <img src="https://img.shields.io/badge/version-1.7.9-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/status-stable-success?style=flat-square" alt="Status">
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
- **YARA rule engine** — 18+ rule files covering PHP, ASP, JSP, ASPX, Godzilla, Behinder; hot-reload supported
- **WAL transaction logs** — Async batch writes with auto rotation, minimal data loss under file locking
- **Smart alerting** — Exponential backoff with adaptive thresholds to reduce false positives
- **Web dashboard** — Dark theme terminal-style interface, SSE real-time log stream, HTMX-driven
- **Enterprise security** — CSRF protection, IP whitelist, Scrypt password hashing
- **Wildcard log tracing** — Recursive path matching like `**/access.log` with attacker IP extraction

## Quick Start

### Linux / macOS

```bash
git clone https://github.com/yourusername/trident.git
cd trident
chmod +x install.sh
./install.sh
```

### Windows

```powershell
git clone https://github.com/yourusername/trident.git
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
├── config/                 # Config loader & registry
├── core/                   # Detection engine, WAL, metrics, notifier
├── web/                    # Flask blueprints, templates, static assets
├── rules/webshell/         # YARA rule files
├── tools/                  # Admin utilities
├── scripts/                # Installers & service templates
└── tests/                  # Compatibility & tool validation
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

## License

MIT License. Free for production, academic research, and personal use.

---

<div align="center">
  <sub>Trident Security Platform — MIT License</sub>
</div>
