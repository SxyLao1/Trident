#!/usr/bin/env python3
"""Anteumbra WAF Proxy v1.0 — Lightweight HTTP reverse proxy with WAF rules.

Usage:
  python waf_proxy.py                     # :8081 -> :80
  python waf_proxy.py 8081 8080           # proxy to Trident/Anteumbra test
  python waf_proxy.py 8081 80             # proxy to phpstudy

Dashboard: http://127.0.0.1:PORT/
API:       http://127.0.0.1:PORT/api/events?since=<ISO timestamp>

Features: SQLi, XSS, traversal, webshell upload, command injection detection.
Logs: data/waf_events.jsonl (JSON Lines, Trident-compatible).
"""
import http.server, json, os, re, socketserver, sys, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
BACKEND_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 80
BACKEND_HOST = "127.0.0.1"
LOG_FILE = Path("data/waf_events.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

SQLI = [re.compile(r"(?:'|%27)\s*(?:or|and|union|select|insert|update|delete|drop|alter|exec|execute)\s", re.I),
        re.compile(r"union\s+(?:all\s+)?select", re.I),
        re.compile(r"\b(?:information_schema|sysobjects|syscolumns|xp_cmdshell)\b", re.I)]
XSS_R = [re.compile(r"<script[^>]*>.*?</script>", re.I),
         re.compile(r"on\w+\s*=\s*[\"'][^\"']*[\"']", re.I),
         re.compile(r"javascript\s*:", re.I)]
TRAV = [re.compile(r"\.\.(?:/|\\)", re.I)]
SHELL = [re.compile(r"<\?(?:php|=)", re.I), re.compile(r"<%@\s+(?:page|import)", re.I),
         re.compile(r"eval\s*\(.*base64_decode", re.I), re.compile(r"Runtime\.getRuntime\(\)\.exec", re.I)]
CMD_R = [re.compile(r"[;&|]\s*(?:id|whoami|uname|ls|dir|cat|wget|curl|nc|netcat|bash|sh|cmd|powershell)\b", re.I),
         re.compile(r"\$\((.*?)\)", re.I)]


def analyze(method, path, query, body):
    full_text = (path + "?" + query + " " + (body or "")).lower()
    score, reasons = 0.0, []
    for p in SQLI:
        if p.search(full_text): score += 0.7; reasons.append("sqli"); break
    for p in XSS_R:
        if p.search(full_text): score += 0.6; reasons.append("xss"); break
    for p in TRAV:
        if p.search(path): score += 0.8; reasons.append("traversal"); break
    for p in SHELL:
        if p.search(body or "") or p.search(query or ""): score += 0.9; reasons.append("webshell"); break
    for p in CMD_R:
        if p.search(full_text): score += 0.7; reasons.append("cmd_injection"); break
    blocked = score >= 0.7
    return blocked, ",".join(reasons) if reasons else "clean", round(score, 2)


def log_event(event):
    with open(str(LOG_FILE), "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


class WAFHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/open/events"): return self._api_open_events()
        if self.path.startswith("/api/events"): return self._api_events()
        if self.path in ("/", "/dashboard"): return self._dashboard()
        self._proxy("GET")

    def do_POST(self): self._proxy("POST")

    def do_PUT(self): self._proxy("PUT")

    def _proxy(self, method):
        cl = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(cl).decode("utf-8", errors="replace") if cl > 0 else ""
        path = self.path
        query = urllib.parse.urlparse(self.path).query
        blocked, reason, score = analyze(method, path, query, body)
        client = self.client_address[0]
        event = {"timestamp": datetime.now().isoformat(), "src_ip": client, "method": method,
                 "url": path, "user_agent": self.headers.get("User-Agent", ""), "waf_rule_id": reason,
                 "waf_score": score, "attack_type": reason, "action": "block" if blocked else "pass",
                 "status": 403 if blocked else "proxied"}
        log_event(event)
        if blocked:
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Forbidden", "reason": reason, "score": score}).encode())
            return
        try:
            url = f"http://{BACKEND_HOST}:{BACKEND_PORT}{path}"
            req = urllib.request.Request(url, data=body.encode() if body else None, method=method)
            for k, v in self.headers.items():
                if k.lower() not in ("host", "content-length"): req.add_header(k, v)
            # v2.0: 透传真实客户端 IP，避免后端日志全是 127.0.0.1
            client_ip = self.client_address[0]
            req.add_header("X-Forwarded-For", client_ip)
            req.add_header("X-Real-IP", client_ip)
            resp = urllib.request.urlopen(req, timeout=30)
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() != "transfer-encoding": self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp.read())
        except Exception as exc:
            self.send_response(502); self.end_headers()
            self.wfile.write(f"Bad Gateway: {exc}".encode())

    def _api_events(self):
        since = self.path.split("since=")[-1] if "since=" in self.path else ""
        events = []
        if LOG_FILE.exists():
            with open(str(LOG_FILE), "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        e = json.loads(line)
                        if since and e.get("timestamp", "") <= since: continue
                        events.append(e)
        events = events[-100:]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(events, indent=2).encode())

    def _api_open_events(self):
        """Mock WAF-compatible endpoint for Trident WAF poller."""
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(self.path).query)
        start = qs.get("start", [""])[0]
        end = qs.get("end", [""])[0]
        limit = int(qs.get("limit", ["100"])[0])
        events = []
        if LOG_FILE.exists():
            with open(str(LOG_FILE), "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        e = json.loads(line)
                        ts = e.get("timestamp", "")
                        if start and ts < start: continue
                        if end and ts >= end: continue
                        if len(events) >= limit: break
                        # Remap to Mock WAF field names (what WAFPoller expects)
                        events.append({
                            "event_id": ts.replace(":", "").replace("-", "").replace("T", ""),
                            "src_ip": e.get("src_ip", ""),
                            "timestamp": ts,
                            "http_method": e.get("method", "GET"),
                            "url": e.get("url", ""),
                            "user_agent": e.get("user_agent", ""),
                            "waf_rule_id": e.get("waf_rule_id", "proxy"),
                            "waf_score": e.get("waf_score", 0.5),
                            "attack_type": e.get("attack_type", "unknown"),
                        })
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(events, indent=2).encode())

    def _dashboard(self):
        events = []
        if LOG_FILE.exists():
            with open(str(LOG_FILE), "r", encoding="utf-8") as f:
                for line in list(f)[-50:]:
                    if line.strip(): events.append(json.loads(line))
        b = sum(1 for e in events if e.get("action") == "block")
        html = "<!DOCTYPE html><html><head><title>Anteumbra WAF</title>"
        html += "<style>body{background:#0a0a0a;color:#ccc;font-family:monospace;padding:20px}"
        html += "h1{color:#00ff41}.card{background:#111;border:1px solid #1a1a1a;padding:12px;margin:8px 0}"
        html += ".stat{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}</style></head><body>"
        html += f"<h1>Anteumbra WAF Proxy v1.0</h1>"
        html += f"<p>:{PORT} -> {BACKEND_HOST}:{BACKEND_PORT} | Events:{len(events)} | Blocked:{b}</p>"
        html += "<div class='stat'>"
        html += f"<div class='card'><h3 style='color:#00ff41'>SQLi</h3><p>{sum(1 for e in events if 'sqli' in e.get('waf_rule_id',''))}</p></div>"
        html += f"<div class='card'><h3 style='color:#ffaa00'>XSS</h3><p>{sum(1 for e in events if 'xss' in e.get('waf_rule_id',''))}</p></div>"
        html += f"<div class='card'><h3 style='color:#ff6b35'>Traversal</h3><p>{sum(1 for e in events if 'traversal' in e.get('waf_rule_id',''))}</p></div>"
        html += f"<div class='card'><h3 style='color:#ff4444'>WebShell</h3><p>{sum(1 for e in events if 'webshell' in e.get('waf_rule_id',''))}</p></div>"
        html += "</div><h3>Recent</h3><pre style='background:#000;padding:8px;max-height:400px;overflow-y:auto'>"
        for e in reversed(events[-30:]): html += json.dumps(e, ensure_ascii=False) + "\n"
        html += "</pre></body></html>"
        self.send_response(200); self.send_header("Content-Type", "text/html;charset=utf-8"); self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, *a): pass


if __name__ == "__main__":
    print(f"Anteumbra WAF Proxy v1.0")
    print(f"  Listening: http://0.0.0.0:{PORT}")
    print(f"  Backend:   http://{BACKEND_HOST}:{BACKEND_PORT}")
    print(f"  Dashboard: http://127.0.0.1:{PORT}")
    print(f"  API:       http://127.0.0.1:{PORT}/api/events")
    socketserver.ThreadingTCPServer(("0.0.0.0", PORT), WAFHandler).serve_forever()
