"""Tests for core/domain/entities.py and core/domain/registry_adapter.py"""
import pytest
from anteumbra.domain.entities import FileRecord, DetectionSource, FileStatus, ScanResult, QuarantineRecord
from anteumbra.domain.registry_adapter import RegistryRepository, get_registry_repository


class TestFileRecord:
    def test_create_minimal(self):
        r = FileRecord(file_path="/tmp/test.php")
        assert r.file_path == "/tmp/test.php"
        assert r.status == FileStatus.ACTIVE
        assert r.is_active is True

    def test_create_full(self):
        r = FileRecord(
            file_path="C:\\www\\shell.php",
            display_name="shell.php",
            features=["php_eval", "base64_decode"],
            detection_source=DetectionSource.ACTIVE,
            first_seen_ip="10.0.0.1",
            file_size=1234,
        )
        assert r.file_path == "C:/www/shell.php"  # Normalized
        assert r.detection_source == DetectionSource.ACTIVE
        assert r.first_seen_ip == "10.0.0.1"

    def test_quarantined_status(self):
        r = FileRecord(file_path="/tmp/q.php", quarantine_id="q-abc123")
        assert r.status == FileStatus.QUARANTINED
        assert r.is_active is False

    def test_false_positive_status(self):
        r = FileRecord(file_path="/tmp/fp.php", marked_false_positive=True)
        assert r.status == FileStatus.FALSE_POSITIVE

    def test_deleted_status(self):
        r = FileRecord(file_path="/tmp/del.php", deleted_at="2026-06-28T12:00:00Z")
        assert r.status == FileStatus.DELETED

    def test_roundtrip_dict(self):
        original = FileRecord(
            file_path="/var/www/x.php",
            features=["a", "b", "c"],
            detection_source=DetectionSource.WAF,
            metadata={"key": "value"},
        )
        data = original.to_dict()
        restored = FileRecord.from_dict(data)
        assert restored.file_path == original.file_path
        assert restored.features == original.features
        assert restored.detection_source == original.detection_source
        assert restored.metadata == {"key": "value"}

    def test_auto_display_name(self):
        r = FileRecord(file_path="/var/www/html/backdoor.php")
        assert r.display_name == "backdoor.php"

    def test_auto_timestamp(self):
        r = FileRecord(file_path="/tmp/a.php")
        assert r.detected_at  # Auto-generated

    def test_default_values(self):
        r = FileRecord(file_path="/tmp/b.php")
        assert r.features == []
        assert r.file_exists is True
        assert r.communication_count == 0
        assert r.alerted is False
        assert r.marked_false_positive is False
        assert r.quarantine_id is None


class TestScanResult:
    def test_to_record(self):
        from pathlib import Path
        sr = ScanResult(
            Path("/tmp/malware.php"),
            is_suspicious=True,
            score=0.95,
            engine="yara",
            features=["php_webshell"],
            detection_source=DetectionSource.PASSIVE,
        )
        record = sr.to_record()
        assert isinstance(record, FileRecord)
        assert record.file_path == "/tmp/malware.php"
        assert record.features == ["php_webshell"]


class TestQuarantineRecord:
    def test_create(self):
        qr = QuarantineRecord(
            quarantine_id="q-001",
            original_path="/tmp/bad.php",
            quarantine_path="data/quarantine/q-001",
            rule_name="php_webshell",
            features=["eval"],
        )
        assert qr.quarantine_id == "q-001"
        assert qr.original_path == "/tmp/bad.php"
        assert qr.created_at is not None


class TestRegistryAdapter:
    def test_singleton(self):
        r1 = get_registry_repository()
        r2 = get_registry_repository()
        assert r1 is r2

    def test_get_entity_nonexistent(self):
        repo = RegistryRepository()
        r = repo.get_entity("/nonexistent/path.php")
        assert r is None

    def test_save_and_get(self, temp_dir):
        # Create a real file so registry_add succeeds
        test_file = temp_dir / "test_repo.php"
        test_file.write_text("<?php echo 'test'; ?>")
        repo = RegistryRepository()
        entity = FileRecord(
            file_path=str(test_file),
            features=["test_entity"],
        )
        repo.save_entity(entity)
        restored = repo.get_entity(str(test_file))
        assert restored is not None, f"Failed to retrieve entity after save"
        assert restored.features == ["test_entity"]

    def test_get_active(self):
        repo = RegistryRepository()
        active = repo.get_active()
        assert isinstance(active, list)
        for r in active:
            assert isinstance(r, FileRecord)
            assert r.is_active is True

    def test_stats(self):
        repo = RegistryRepository()
        stats = repo.get_stats()
        assert "active" in stats
        assert "total" in stats
        assert "quarantined" in stats
        assert stats["total"] >= stats["active"]
