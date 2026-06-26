#!/usr/bin/env python3
"""
Trident Mock WAF Server v1.8.1
Simulates structured WAF attack events for profiling engine development.

Usage:
    python tests/mock_waf_server.py                    # default port 9999, speed 60x
    python tests/mock_waf_server.py --port 9999 --speed 120

API:
    GET  /                    — list scenarios + active status
    GET  /api/open/events?start=<ts>&end=<ts>  — Trident polls events in time window
    POST /start?scenario=<name>&speed=<N>      — start scenario at Nx speed
    POST /stop?scenario=<name>                 — stop scenario
    POST /stop/all                              — stop all
    GET  /status                                — detailed status of all scenarios

Design decisions:
    - Stateful: tracks current timestamp per scenario, returns only new events
    - Time compression: 1 real second = N simulated seconds (default 60x)
    - All generated events buffered in memory, polled by time range
    - IP pool: random octets within configured CIDR pattern
    - URL patterns: {i} placeholder for variant numbering
"""
import sys, os, json, random, time, threading, uuid, argparse
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ── Load scenarios ──────────────────────────────────────────
SCENARIOS_FILE = Path(__file__).parent / "mock_waf_scenarios.json"
with open(SCENARIOS_FILE, encoding='utf-8') as f:
    SCENARIO_DATA = json.load(f)
SCENARIOS = SCENARIO_DATA["scenarios"]
DEFAULTS = SCENARIO_DATA["defaults"]

# ── Global state ─────────────────────────────────────────────
_active = {}       # scenario_name -> {config, state}
_event_buffer = []  # [{timestamp, src_ip, user_agent, url, ...}, ...]
_buffer_lock = threading.Lock()
_simulated_start = None  # wall-clock time when scenario started

# ── IP generation ────────────────────────────────────────────
_ip_cache = {}

def _generate_ip_pool(cidr_template, pool_size):
    if cidr_template in _ip_cache:
        return _ip_cache[cidr_template]
    ips = []
    for _ in range(pool_size):
        oct2 = random.randint(1, 254)
        oct3 = random.randint(1, 254)
        oct4 = random.randint(1, 254)
        ip = cidr_template.replace("{octet2}", str(oct2)).replace("{octet3}", str(oct3)).replace("{octet4}", str(oct4))
        ips.append(ip)
    _ip_cache[cidr_template] = ips
    return ips

# ── Event generation ─────────────────────────────────────────
def _generate_url(pattern, variant_index=None):
    if variant_index is not None and "{i}" in pattern:
        return pattern.replace("{i}", str(variant_index))
    return pattern

def _generate_event(cfg, sim_timestamp, ip_pool, event_index):
    ip = random.choice(ip_pool)
    url_pattern = random.choice(cfg["url_patterns"])
    url = _generate_url(url_pattern, event_index if cfg.get("variant_count") else None)
    method = random.choice(cfg.get("http_methods", ["POST"]))
    ua = cfg["user_agent"]
    # For mixed campaigns, sometimes use alternate UA
    if not cfg.get("user_agent_sticky", True) and cfg.get("user_agent_alt"):
        if random.random() < 0.3:
            ua = cfg["user_agent_alt"]

    score_min, score_max = cfg.get("waf_score_range", [0.7, 1.0])
    waf_score = round(random.uniform(score_min, score_max), 3)
    rule_id = random.choice(cfg.get("waf_rule_ids", ["unknown"]))

    return {
        "event_id": str(uuid.uuid4())[:8],
        "src_ip": ip,
        "timestamp": sim_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
        "http_method": method,
        "url": url,
        "user_agent": ua,
        "waf_rule_id": rule_id,
        "waf_score": waf_score,
        "attack_type": cfg.get("attack_type", "unknown")
    }

def _scenario_worker(name):
    """Background thread: generate events at compressed time rate"""
    global _event_buffer
    cfg = SCENARIOS[name]
    state = _active[name]
    speed = state["speed"]
    duration = cfg["duration_seconds"]
    ip_pool = _generate_ip_pool(cfg["ip_pool_cidr"], cfg["ip_pool_size"])
    events_per_sim_sec = cfg["events_per_minute"] / 60.0
    # Real seconds to wait between events
    real_interval = 1.0 / (events_per_sim_sec * speed) if events_per_sim_sec > 0 else 1.0

    sim_time = state.get("sim_offset", 0)  # simulated seconds elapsed
    event_index = state.get("event_index", 0)

    while sim_time < duration and state["running"]:
        # Calculate how many events this tick (handles burst)
        n_events = 1
        if cfg.get("burst_enabled") and event_index % cfg.get("burst_frequency", 5) == 0:
            n_events = cfg.get("burst_multiplier", 3)

        for _ in range(n_events):
            if sim_time >= duration:
                break
            sim_dt = datetime.fromtimestamp(
                _simulated_start.timestamp() + sim_time / speed
            ) if _simulated_start else datetime.now()
            event = _generate_event(cfg, sim_dt, ip_pool, event_index)
            with _buffer_lock:
                _event_buffer.append(event)
            event_index += 1

        sim_time += 1  # 1 simulated second per event tick
        state["sim_offset"] = sim_time
        state["event_index"] = event_index
        time.sleep(real_interval)

    state["running"] = False
    state["completed"] = True
    print(f"[MOCK_WAF] Scenario '{name}' completed: {event_index} events generated")

# ── API Endpoints ────────────────────────────────────────────
INDEX_HTML = """<!DOCTYPE html>
<html><head><title>Trident Mock WAF</title>
<style>body{background:#0a0a0a;color:#ccc;font-family:monospace;padding:20px}
h1{color:#00ff41} .card{background:#111;border:1px solid #1a1a1a;padding:12px;margin:8px 0;border-radius:4px}
button{background:#000;color:#00ff41;border:1px solid #00ff41;padding:6px 14px;cursor:pointer;margin:4px}
button:hover{background:#002200} .running{color:#ffaa00} .completed{color:#00ff41} .stopped{color:#666}
pre{background:#000;padding:8px;overflow-x:auto;}</style></head><body>
<h1>Trident Mock WAF Server v1.8.1</h1>
{% for name, cfg in scenarios.items() %}
<div class="card">
<h3>{{ cfg.name }} <span class="{{ statuses.get(name, 'stopped') }}">[{{ statuses.get(name, 'stopped') }}]</span></h3>
<p>{{ cfg.description }}</p>
<p>IPs: {{ cfg.ip_pool_size }} | Duration: {{ cfg.duration_seconds }}s | Rate: {{ cfg.events_per_minute }}/min</p>
<form method="POST" action="/start" style="display:inline">
  <input name="scenario" value="{{ name }}" hidden>
  <input name="speed" value="60" style="width:60px;background:#000;color:#ccc;border:1px solid #333;padding:4px">
  <button>Start (Nx speed)</button>
</form>
<form method="POST" action="/stop" style="display:inline">
  <input name="scenario" value="{{ name }}" hidden><button>Stop</button>
</form>
</div>{% endfor %}
<p>API: <code>GET /api/open/events?start=&lt;ISO&gt;&end=&lt;ISO&gt;</code></p>
{% if events_preview %}
<h3>Latest Events</h3><pre>{{ events_preview }}</pre>
{% endif %}
</body></html>"""

@app.route("/")
def index():
    statuses = {}
    for name, state in _active.items():
        if state.get("completed"): statuses[name] = "completed"
        elif state.get("running"): statuses[name] = "running"
        else: statuses[name] = "stopped"
    for name in SCENARIOS:
        if name not in statuses: statuses[name] = "stopped"

    preview = ""
    with _buffer_lock:
        for evt in _event_buffer[-5:]:
            preview += json.dumps(evt) + "\n"

    return render_template_string(INDEX_HTML, scenarios=SCENARIOS, statuses=statuses, events_preview=preview)

@app.route("/api/open/events", methods=["GET"])
def poll_events():
    """Trident polls events by time range. Only returns events not yet sent."""
    start_str = request.args.get("start", "")
    end_str = request.args.get("end", "")
    max_events = int(request.args.get("limit", DEFAULTS["max_events_per_poll"]))

    results = []
    with _buffer_lock:
        for evt in _event_buffer:
            if len(results) >= max_events:
                break
            ts = evt["timestamp"]
            if start_str and ts < start_str:
                continue
            if end_str and ts >= end_str:
                continue
            if evt.get("_sent"):
                continue
            evt["_sent"] = True
            results.append({k: v for k, v in evt.items() if k != "_sent"})

    return jsonify(results)

@app.route("/start", methods=["POST"])
def start_scenario():
    global _simulated_start
    name = request.form.get("scenario") or request.args.get("scenario")
    speed = int(request.form.get("speed") or request.args.get("speed", DEFAULTS["speed_multiplier"]))

    if name not in SCENARIOS:
        return jsonify({"error": f"Unknown scenario: {name}", "available": list(SCENARIOS.keys())}), 404

    if name in _active and _active[name].get("running"):
        return jsonify({"error": f"Scenario '{name}' is already running"}), 409

    _active[name] = {"running": True, "completed": False, "speed": speed, "sim_offset": 0, "event_index": 0}
    _simulated_start = datetime.now()

    t = threading.Thread(target=_scenario_worker, args=(name,), daemon=True)
    t.start()
    _active[name]["thread"] = t

    print(f"[MOCK_WAF] Started '{name}' at {speed}x speed")
    return jsonify({"success": True, "scenario": name, "speed": speed})

@app.route("/stop", methods=["POST"])
def stop_scenario():
    name = request.form.get("scenario") or request.args.get("scenario")
    if name == "all":
        for n, state in _active.items():
            state["running"] = False
        return jsonify({"success": True, "stopped": list(_active.keys())})

    if name not in _active:
        return jsonify({"error": f"Scenario '{name}' is not active"}), 404

    _active[name]["running"] = False
    return jsonify({"success": True, "scenario": name})

@app.route("/status")
def status():
    result = {}
    for name, state in _active.items():
        cfg = SCENARIOS[name]
        result[name] = {
            "running": state.get("running", False),
            "completed": state.get("completed", False),
            "speed": state.get("speed", 1),
            "events_generated": state.get("event_index", 0),
            "sim_time_elapsed": state.get("sim_offset", 0),
            "total_duration": cfg["duration_seconds"],
            "progress_pct": round(state.get("sim_offset", 0) / cfg["duration_seconds"] * 100, 1) if cfg["duration_seconds"] > 0 else 0
        }
    with _buffer_lock:
        result["_total_events_buffered"] = len(_event_buffer)
    return jsonify(result)

# ── Main ─────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trident Mock WAF Server")
    parser.add_argument("--port", type=int, default=DEFAULTS["port"])
    parser.add_argument("--speed", type=int, default=DEFAULTS["speed_multiplier"])
    args = parser.parse_args()

    print(f"[MOCK_WAF] Starting on http://127.0.0.1:{args.port}")
    print(f"[MOCK_WAF] Default speed: {args.speed}x")
    print(f"[MOCK_WAF] Scenarios: {', '.join(SCENARIOS.keys())}")
    print(f"[MOCK_WAF] Web UI: http://127.0.0.1:{args.port}")
    print(f"[MOCK_WAF] Events API: http://127.0.0.1:{args.port}/api/open/events")
    app.run(host="127.0.0.1", port=args.port, debug=False)
