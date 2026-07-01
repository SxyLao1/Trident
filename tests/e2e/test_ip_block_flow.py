# -*- coding: utf-8 -*-
"""
E2E Test: IP Block → Ledger → Export → Unblock

Flow:
  1. Block an IP — verify it's written to ledger
  2. Query entries with filters
  3. Update notes on an entry
  4. Export ledger
  5. Get stats
  6. Remove entry (unblock)
"""
import json
import pytest


class TestIPBlockFlow:
    """Full IP block → ledger lifecycle."""

    @pytest.fixture(autouse=True)
    def clear_ledger(self):
        """Clear ledger cache between tests."""
        import anteumbra.infrastructure.block_ledger as bl
        bl._LEDGER_CACHE = []
        yield
        bl._LEDGER_CACHE = []

    def test_add_entry_creates_ledger_record(self):
        """Block an IP and verify it appears in the ledger."""
        from anteumbra.infrastructure.block_ledger import add_entry, get_entries

        entry = add_entry(
            ip="10.99.99.1",
            source="auto",
            reason="Profile abc123 — AntSword scan / risk 0.95",
            profile_id="abc123",
            blocked_by="system",
        )

        assert entry is not None
        assert entry["ip"] == "10.99.99.1"
        assert entry["source"] == "auto"
        assert "AntSword" in entry["reason"]
        assert entry["profile_id"] == "abc123"

        # Verify via get_entries
        entries, total = get_entries()
        assert total >= 1, f"Should have at least 1 entry, got {total}"
        found = [e for e in entries if e["ip"] == "10.99.99.1"]
        assert len(found) == 1, "Should find the blocked IP"

    def test_add_entry_dedup_updates_existing(self):
        """Blocking the same IP again should update the existing entry, not duplicate."""
        from anteumbra.infrastructure.block_ledger import add_entry, get_entries

        # First block
        add_entry(ip="10.88.77.2", source="manual", reason="First block")
        # Second block — should update
        add_entry(ip="10.88.77.2", source="auto", reason="Updated block")

        entries, total = get_entries()
        matches = [e for e in entries if e["ip"] == "10.88.77.2"]
        assert len(matches) == 1, (
            f"Should have exactly 1 entry for deduped IP, got {len(matches)}"
        )
        assert matches[0]["source"] == "auto", "Source should be updated"
        assert "Updated" in matches[0]["reason"], "Reason should be updated"

    def test_update_notes(self):
        """Update notes on a blocked IP."""
        from anteumbra.infrastructure.block_ledger import (
            add_entry, update_notes, get_entries,
        )

        add_entry(ip="10.66.55.4", reason="Test entry")
        ok = update_notes("10.66.55.4", "This is a suspected C2 server")
        assert ok is True

        entries, _ = get_entries()
        match = [e for e in entries if e["ip"] == "10.66.55.4"]
        assert match[0]["notes"] == "This is a suspected C2 server"

    def test_stats_reflect_entries(self):
        """Verify ledger stats count entries correctly."""
        from anteumbra.infrastructure.block_ledger import (
            add_entry, get_stats, remove_entry,
        )

        # Clean slate — remove any existing entries
        for ip in ["10.1.1.1", "10.1.1.2"]:
            remove_entry(ip)

        add_entry(ip="10.1.1.1", source="auto", reason="Auto blocked")
        add_entry(ip="10.1.1.2", source="manual", reason="Manual blocked")

        stats = get_stats()
        assert stats["total"] >= 2, f"Should have at least 2 entries, got {stats}"
        assert stats["auto"] >= 1, f"Should have at least 1 auto entry, got {stats}"
        assert stats["manual"] >= 1, f"Should have at least 1 manual entry, got {stats}"

    def test_export_json(self):
        """Export ledger as JSON."""
        from anteumbra.infrastructure.block_ledger import (
            add_entry, export_ledger, remove_entry,
        )

        remove_entry("10.22.33.4")
        add_entry(ip="10.22.33.4", reason="Export test")

        exported = export_ledger(fmt="json")
        data = json.loads(exported)
        assert isinstance(data, list)
        assert any(e["ip"] == "10.22.33.4" for e in data), (
            "Exported JSON should contain the test entry"
        )

    def test_remove_entry(self):
        """Unblock an IP — remove it from the ledger."""
        from anteumbra.infrastructure.block_ledger import add_entry, remove_entry, get_entries

        add_entry(ip="10.44.55.6", reason="To be removed")
        ok = remove_entry("10.44.55.6")
        assert ok is True

        entries, _ = get_entries()
        assert not any(e["ip"] == "10.44.55.6" for e in entries), (
            "Removed IP should not appear in entries"
        )

    def test_search_filter(self):
        """Search entries by IP/reason text."""
        from anteumbra.infrastructure.block_ledger import add_entry, get_entries

        add_entry(ip="192.168.99.1", reason="Brute force SSH from China")
        add_entry(ip="192.168.99.2", reason="Normal probe")

        # Search by "China" — should find only the first
        entries, total = get_entries(search="China")
        assert total >= 1
        assert all("China" in e.get("reason", "") for e in entries)

    def test_source_filter(self):
        """Filter entries by source type."""
        from anteumbra.infrastructure.block_ledger import add_entry, get_entries

        # Add both auto and manual entries
        add_entry(ip="172.16.1.1", source="auto", reason="Auto block")
        add_entry(ip="172.16.1.2", source="manual", reason="Manual block")

        auto_entries, auto_total = get_entries(source_filter="auto")
        manual_entries, manual_total = get_entries(source_filter="manual")

        assert all(e["source"] == "auto" for e in auto_entries), (
            "Auto filter should only return auto entries"
        )
        assert all(e["source"] == "manual" for e in manual_entries), (
            "Manual filter should only return manual entries"
        )
