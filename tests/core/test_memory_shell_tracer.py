"""Tests for core/memory_shell_tracer.py"""
import pytest
from pathlib import Path
from datetime import datetime
from core.memory_shell_tracer import MemoryShellTracer, trace_memory_shell


class TestMemoryShellTracer:
    def test_trace_no_logs(self):
        tracer = MemoryShellTracer(lookback_hours=1)
        r = tracer.trace("10.0.0.1", datetime(2026, 6, 28, 12, 0, 0), log_paths=[])
        assert r["found"] is False
        assert r["confidence"] == "low"
        assert "No upload activity" in r["summary"]

    def test_trace_with_sample_log(self, temp_dir):
        p = temp_dir / "access.log"
        lines = [
            '192.168.1.100 - - [28/Jun/2026:08:15:30 +0800] "POST /uploads/shell.php HTTP/1.1" 201 1234 "-" "AntSword/2.1"',
            '192.168.1.100 - - [28/Jun/2026:08:16:00 +0800] "PUT /images/backdoor.jsp HTTP/1.1" 200 567 "-" "curl/7.88"',
            '10.0.0.1 - - [28/Jun/2026:08:17:00 +0800] "GET /index.html HTTP/1.1" 200 890 "-" "Mozilla/5.0"',
        ]
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")

        tracer = MemoryShellTracer(lookback_hours=24)
        r = tracer.trace("192.168.1.100", datetime(2026, 6, 28, 9, 0, 0), log_paths=[p])
        assert r["found"] is True
        assert r["writes"] >= 1
        assert len(r["candidates"]) >= 1
        # Highest-scored candidate should be the POST to shell.php (score 10)
        top = r["candidates"][0]
        assert top["path"] == "/uploads/shell.php"
        assert top["method"] == "POST"
        assert top["score"] >= 8

    def test_trace_different_ip_no_match(self, temp_dir):
        p = temp_dir / "access2.log"
        p.write_text(
            '10.0.0.99 - - [28/Jun/2026:08:15:30 +0800] "GET /index.html HTTP/1.1" 200 890 "-" "Mozilla/5.0"\n',
            encoding="utf-8")
        tracer = MemoryShellTracer(lookback_hours=1)
        r = tracer.trace("192.168.1.100", datetime(2026, 6, 28, 9, 0, 0), log_paths=[p])
        assert r["found"] is False
        assert r["writes"] == 0

    def test_convenience_function(self, temp_dir):
        p = temp_dir / "access3.log"
        p.write_text(
            '10.0.0.5 - - [28/Jun/2026:08:30:00 +0800] "POST /shell.php HTTP/1.1" 201 567 "-" "curl/7"\n',
            encoding="utf-8")
        r = trace_memory_shell("10.0.0.5", datetime(2026, 6, 28, 9, 0, 0), log_paths=[p])
        assert r["found"] is True
        assert len(r["candidates"]) == 1

    def test_cross_reference_unmatched(self):
        tracer = MemoryShellTracer()
        r = tracer.trace("10.0.0.1", datetime.now(), log_paths=[])
        assert r["matched"] is None
        assert r["confidence"] == "low"
