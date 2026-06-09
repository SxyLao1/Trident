# Trident v1.7.8 — Release Notes

**Release Date**: 2026-05-27  
**Status**: Production-Ready

---

## Highlights

v1.7.8 completes the engineering overhaul started in v1.7.7, adding a modular installer, background launcher scripts, and full bilingual documentation.

### For Users
- One-line installer for Linux/macOS/Windows — auto-detects Python, creates venv, installs deps
- Config-aware install: Keep / Overwrite / Review existing configuration
- Background/foreground start scripts with PID-based graceful stop
- Uninstall scripts that clean venv and data while preserving config and logs

### For Developers
- All install logic centralized in `scripts/install.py`; shell/bat wrappers never change across versions
- Version zero-hardcoding: `config.toml` → `config/version.py` → cascade to all consumers
- CI/CD matrix with compatibility tests and tool validation
- Docker multi-stage build with health check endpoint

---

## Installation

### Linux / macOS / WSL
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

### Docker
```bash
docker-compose up -d
```

---

## Verification Checklist

- [ ] Login page shows matrix-rain animation
- [ ] Dashboard loads four quadrants (Metrics / Log Stream / YARA / Records)
- [ ] Records show correct filename, time, rule, communication count
- [ ] YARA card scrolls to show all rules
- [ ] YARA Upload button opens modal, supports drag-and-drop
- [ ] Each YARA rule has Edit/Delete buttons
- [ ] LIVE LOG STREAM shows historical logs
- [ ] SSE appends new logs without overwriting history
- [ ] Records False Pos button marks FP, becomes Cancel FP
- [ ] Records pagination Prev/Next/jump works correctly
- [ ] Records search retains pagination parameters
- [ ] System Management quadrants load correctly
- [ ] WAL Replay replays and refreshes status
- [ ] Session Cleanup refreshes without error
- [ ] Config Reload triggers hot-reload
- [ ] Refresh button refreshes current page
- [ ] Mobile sidebar expands/collapses
- [ ] Login FX toggle disables matrix rain
- [ ] Password change rejects weak passwords
- [ ] Health check open endpoint `/api/v1/health` returns `{"status": "healthy"}`
- [ ] Authenticated health check `/admin/health` returns full diagnostics

---

## Known Issues

| Issue | Severity | Workaround | Target Fix |
|-------|----------|------------|------------|
| Batch ops hidden in compact mode | Low | Use full Records page | v1.7.9 |
| SSE history capped at 1000 events | Low | Increase buffer rotation | v1.7.9 |
| WAL archives display only (no download) | Low | Manual download from `data/` | v1.7.9 |
| Windows background PID stale | Low | Task Manager fallback | v1.7.9 |

---

## Security Notes

- Replace default `secret_key` in production
- Default `allowed_ips` is `["127.0.0.1"]` — extend to LAN for team access
- Generate strong password hash via `python tools/admin_passwd.py`
- Enable HTTPS for public exposure
- Version numbers are not exposed in login page or unauthenticated endpoints
