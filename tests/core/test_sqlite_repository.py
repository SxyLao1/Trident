"""Tests for core/repositories/sqlite_repository.py"""
import pytest
from pathlib import Path
from anteumbra.infrastructure.persistence.sqlite_repository import SqliteRepository, DualWriteRepository
from anteumbra.infrastructure.persistence.json_repository import JsonRepository


@pytest.fixture
def sql_repo(temp_dir):
    p = temp_dir / "test.db"
    repo = SqliteRepository(str(p))
    yield repo
    repo.close()


class TestSqliteRepository:
    def test_save_and_get(self, sql_repo):
        sql_repo.save("rec-1", {"file_path": "/tmp/test.php", "features": ["a", "b"]})
        r = sql_repo.get("rec-1")
        assert r is not None
        assert "file_path" in r

    def test_delete(self, sql_repo):
        sql_repo.save("rec-x", {"file_path": "/tmp/x.php"})
        assert sql_repo.delete("rec-x") is True
        assert sql_repo.get("rec-x") is None

    def test_count(self, sql_repo):
        assert sql_repo.count() == 0
        sql_repo.save("a", {"file_path": "/a"})
        sql_repo.save("b", {"file_path": "/b"})
        assert sql_repo.count() == 2

    def test_list_all_pagination(self, sql_repo):
        for i in range(10):
            sql_repo.save(f"r{i}", {"file_path": f"/tmp/{i}.php", "detected_at": f"2026-06-28T12:0{i}:00"})
        page = sql_repo.list_all(limit=3, offset=0)
        assert len(page) == 3

    def test_ledger_crud(self, sql_repo):
        sql_repo.save_ledger("10.0.0.1", {
            "ip": "10.0.0.1", "source": "manual", "reason": "test block",
            "broadcast_devices": ["stdout"], "broadcast_status": "success"
        })
        entries, total = sql_repo.get_ledger(limit=10, offset=0)
        assert total >= 1
        e = entries[0]
        assert e["ip"] == "10.0.0.1"
        assert e["source"] == "manual"

    def test_scan_history(self, sql_repo):
        sql_repo.save_scan("scan-test", {
            "scan_id": "scan-test", "target_dir": "/tmp", "status": "completed",
            "total_files": 100, "findings": [{"file": "a.php"}]
        })
        s = sql_repo.get_scan("scan-test")
        assert s is not None
        assert s["status"] == "completed"

    def test_transaction_context(self, sql_repo):
        with sql_repo.transaction():
            sql_repo.save("tx-test", {"file_path": "/tx.php"})
        assert sql_repo.get("tx-test") is not None


class TestDualWriteRepository:
    def test_dual_write_save_and_read(self, temp_dir):
        import time
        jp = temp_dir / "dual.json"
        sp = temp_dir / "dual.db"
        json_repo = JsonRepository(jp, key_field="file_path")
        sql_repo = SqliteRepository(str(sp))
        dual = DualWriteRepository(json_repo, sql_repo)
        dual.save("dual-test", {"file_path": "/tmp/dual_test.php", "features": ["test_feature"],
                                 "detected_at": "2026-06-28T12:00:00"})
        r = dual.get("dual-test")
        assert r is not None
        assert "test_feature" in str(r)
        assert dual.count() >= 1
        sql_repo.close()
        time.sleep(0.1)  # Allow WAL to flush before temp dir cleanup
