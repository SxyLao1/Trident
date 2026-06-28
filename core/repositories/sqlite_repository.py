# -*- coding: utf-8 -*-
"""
v1.9.2: SQLite 仓库实现

实现 Repository 和 EventRepository 接口。
特性：
  - WAL 模式（高并发读）
  - 线程安全（threading.local 连接池）
  - 自动建表（首次启动）
  - 双写模式兼容（与 JSON 并行写入）
"""
import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from core.interfaces.repository import Repository, EventRepository

logger = logging.getLogger(__name__)

# ── SQL Schema ────────────────────────────────────────────

SCHEMA = {
    "registry": """
        CREATE TABLE IF NOT EXISTS registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT UNIQUE NOT NULL,
            file_path TEXT NOT NULL,
            display_name TEXT,
            detected_at TEXT,
            features TEXT,              -- JSON array
            file_exists INTEGER DEFAULT 1,
            file_size INTEGER DEFAULT 0,
            communication_count INTEGER DEFAULT 0,
            first_seen_ip TEXT,
            alerted INTEGER DEFAULT 0,
            marked_false_positive INTEGER DEFAULT 0,
            false_positive_at TEXT,
            quarantine_id TEXT,
            deleted_at TEXT,
            detection_source TEXT DEFAULT 'passive',
            raw_json TEXT,              -- 完整 JSON 备份（兼容性）
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """,
    "quarantine": """
        CREATE TABLE IF NOT EXISTS quarantine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quarantine_id TEXT UNIQUE NOT NULL,
            original_path TEXT NOT NULL,
            quarantine_path TEXT,
            rule_name TEXT,
            features TEXT,              -- JSON array
            file_size INTEGER DEFAULT 0,
            status TEXT DEFAULT 'quarantined',
            created_at TEXT DEFAULT (datetime('now')),
            restored_at TEXT,
            raw_json TEXT
        )
    """,
    "block_ledger": """
        CREATE TABLE IF NOT EXISTS block_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT UNIQUE NOT NULL,
            source TEXT DEFAULT 'manual',
            reason TEXT,
            notes TEXT DEFAULT '',
            profile_id TEXT,
            blocked_by TEXT DEFAULT 'system',
            broadcast_devices TEXT,     -- JSON array
            broadcast_status TEXT DEFAULT 'success',
            blocked_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """,
    "scan_history": """
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id TEXT UNIQUE NOT NULL,
            target_dir TEXT NOT NULL,
            start_time REAL,
            end_time REAL,
            status TEXT DEFAULT 'completed',
            total_files INTEGER DEFAULT 0,
            scanned_files INTEGER DEFAULT 0,
            new_findings INTEGER DEFAULT 0,
            known_findings INTEGER DEFAULT 0,
            clean INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            duration REAL DEFAULT 0,
            findings TEXT,              -- JSON array (max 200)
            created_at TEXT DEFAULT (datetime('now'))
        )
    """,
    "threat_profiles": """
        CREATE TABLE IF NOT EXISTS threat_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT UNIQUE NOT NULL,
            ua_fingerprint TEXT,
            tool_signature TEXT,
            risk_score REAL DEFAULT 0,
            ip_pool TEXT,               -- JSON array
            target_files TEXT,          -- JSON array
            target_urls TEXT,           -- JSON array
            attack_chain TEXT,          -- JSON array
            status TEXT DEFAULT 'active',
            decay_factor REAL DEFAULT 1.0,
            last_seen TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """,
}

# 索引（加速常见查询）
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_registry_file_path ON registry(file_path)",
    "CREATE INDEX IF NOT EXISTS idx_registry_quarantine ON registry(quarantine_id)",
    "CREATE INDEX IF NOT EXISTS idx_registry_detected ON registry(detected_at)",
    "CREATE INDEX IF NOT EXISTS idx_quarantine_status ON quarantine(status)",
    "CREATE INDEX IF NOT EXISTS idx_block_ledger_ip ON block_ledger(ip)",
    "CREATE INDEX IF NOT EXISTS idx_block_ledger_source ON block_ledger(source)",
    "CREATE INDEX IF NOT EXISTS idx_scan_history_time ON scan_history(start_time)",
    "CREATE INDEX IF NOT EXISTS idx_threat_profiles_score ON threat_profiles(risk_score)",
]


# ── SqliteRepository ──────────────────────────────────────

class SqliteRepository(EventRepository):
    """基于 SQLite 的数据仓库，实现 Repository + EventRepository 接口"""

    def __init__(self, db_path: str = "data/trident.db"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._ensure_schema()

    # ── 连接管理 ────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接（自动创建）"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")       # 高并发读
            conn.execute("PRAGMA synchronous=NORMAL")      # 平衡性能/安全
            conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _ensure_schema(self):
        """建表 + 索引（幂等）"""
        conn = self._get_conn()
        for table_name, ddl in SCHEMA.items():
            conn.execute(ddl)
        for idx in INDEXES:
            conn.execute(idx)
        conn.commit()
        logger.info("SqliteRepository: schema ready at %s", self._db_path)

    # ── Repository 接口 ──────────────────────────────────

    def save(self, record_id: str, data: Dict[str, Any]) -> None:
        """保存或更新一条记录（自动判断 INSERT vs UPDATE）"""
        conn = self._get_conn()
        # 将复杂字段序列化为 JSON 字符串
        row = dict(data)
        for k, v in row.items():
            if isinstance(v, (list, dict)):
                row[k] = json.dumps(v, ensure_ascii=False, default=str)
        row["record_id"] = record_id

        columns = list(row.keys())
        placeholders = [f":{c}" for c in columns]
        updates = [f"{c}=excluded.{c}" for c in columns if c != "record_id"]

        sql = f"INSERT INTO registry ({','.join(columns)}) VALUES ({','.join(placeholders)}) ON CONFLICT(record_id) DO UPDATE SET {','.join(updates)}, updated_at=datetime('now')"
        conn.execute(sql, row)
        conn.commit()

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM registry WHERE record_id=?", (record_id,)).fetchone()
        return dict(row) if row else None

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM registry ORDER BY detected_at DESC LIMIT ? OFFSET ?",
            (limit, offset)).fetchall()
        return [dict(r) for r in rows]

    # Whitelist of allowed query columns (prevents SQL injection via filter keys)
    _ALLOWED_COLUMNS = {
        "id", "record_id", "file_path", "display_name", "detected_at",
        "file_exists", "communication_count", "first_seen_ip", "alerted",
        "marked_false_positive", "quarantine_id", "deleted_at",
        "detection_source", "status", "source", "ip", "blocked_by",
        "broadcast_status",
    }

    def query(self, filters: Dict[str, Any],
              limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        where = []
        params = []
        for k, v in filters.items():
            if k not in self._ALLOWED_COLUMNS:
                raise ValueError(f"Invalid filter column: {k}")
            where.append(f"{k}=?")
            params.append(v)
        sql = "SELECT * FROM registry"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY detected_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def delete(self, record_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.execute("DELETE FROM registry WHERE record_id=?", (record_id,))
        conn.commit()
        return cur.rowcount > 0

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        conn = self._get_conn()
        if filters:
            where = " WHERE " + " AND ".join(f"{k}=?" for k in filters)
            params = list(filters.values())
            row = conn.execute(f"SELECT COUNT(*) FROM registry{where}", params).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM registry").fetchone()
        return row[0] if row else 0

    # ── EventRepository 接口 ─────────────────────────────

    def append(self, event: Dict[str, Any]) -> None:
        """追加 WAL 事件"""
        conn = self._get_conn()
        row = {
            "event_type": event.get("event_type", "unknown"),
            "timestamp": event.get("timestamp", ""),
            "source": event.get("source", ""),
            "payload": json.dumps(event.get("payload", {}), ensure_ascii=False, default=str),
        }
        conn.execute(
            "INSERT INTO wal_events (event_type, timestamp, source, payload) VALUES (:event_type, :timestamp, :source, :payload)",
            row)
        conn.commit()

    def replay(self, since: Optional[float] = None) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        if since:
            rows = conn.execute(
                "SELECT * FROM wal_events WHERE timestamp > ? ORDER BY timestamp",
                (since,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM wal_events ORDER BY timestamp").fetchall()
        return [dict(r) for r in rows]

    # ── 扩展方法 ─────────────────────────────────────────

    def save_quarantine(self, qid: str, data: Dict[str, Any]) -> None:
        conn = self._get_conn()
        row = dict(data)
        for k, v in row.items():
            if isinstance(v, (list, dict)):
                row[k] = json.dumps(v, ensure_ascii=False, default=str)
        row["quarantine_id"] = qid
        columns = list(row.keys())
        ph = [f":{c}" for c in columns]
        ups = [f"{c}=excluded.{c}" for c in columns if c != "quarantine_id"]
        conn.execute(
            f"INSERT INTO quarantine ({','.join(columns)}) VALUES ({','.join(ph)}) ON CONFLICT(quarantine_id) DO UPDATE SET {','.join(ups)}",
            row)
        conn.commit()

    def save_ledger(self, ip: str, data: Dict[str, Any]) -> None:
        conn = self._get_conn()
        row = dict(data)
        for k, v in row.items():
            if isinstance(v, (list, dict)):
                row[k] = json.dumps(v, ensure_ascii=False, default=str)
        row["ip"] = ip
        columns = list(row.keys())
        ph = [f":{c}" for c in columns]
        ups = [f"{c}=excluded.{c}" for c in columns if c != "ip"]
        conn.execute(
            f"INSERT INTO block_ledger ({','.join(columns)}) VALUES ({','.join(ph)}) ON CONFLICT(ip) DO UPDATE SET {','.join(ups)}, updated_at=datetime('now')",
            row)
        conn.commit()

    def get_ledger(self, limit: int = 100, offset: int = 0,
                   source_filter: str = "all", search: str = "") -> tuple:
        """分页查询台账 (entries, total)"""
        conn = self._get_conn()
        where = []
        params = []
        if source_filter != "all":
            where.append("source=?")
            params.append(source_filter)
        if search:
            where.append("(ip LIKE ? OR reason LIKE ? OR notes LIKE ?)")
            s = f"%{search}%"
            params.extend([s, s, s])
        sql = "SELECT * FROM block_ledger"
        if where:
            sql += " WHERE " + " AND ".join(where)
        count_sql = sql.replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_sql, params).fetchone()[0]
        rows = conn.execute(
            sql + " ORDER BY blocked_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]).fetchall()
        entries = []
        for r in rows:
            d = dict(r)
            for field in ["broadcast_devices"]:
                if d.get(field) and isinstance(d[field], str):
                    try:
                        d[field] = json.loads(d[field])
                    except json.JSONDecodeError:
                        pass
            entries.append(d)
        return entries, total

    def save_scan(self, scan_id: str, data: Dict[str, Any]) -> None:
        conn = self._get_conn()
        row = dict(data)
        for k, v in row.items():
            if isinstance(v, (list, dict)):
                row[k] = json.dumps(v, ensure_ascii=False, default=str)
        row["scan_id"] = scan_id
        columns = list(row.keys())
        ph = [f":{c}" for c in columns]
        conn.execute(
            f"INSERT OR REPLACE INTO scan_history ({','.join(columns)}) VALUES ({','.join(ph)})",
            row)
        conn.commit()

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM scan_history WHERE scan_id=?", (scan_id,)).fetchone()
        if row:
            d = dict(row)
            if d.get("findings") and isinstance(d["findings"], str):
                try:
                    d["findings"] = json.loads(d["findings"])
                except json.JSONDecodeError:
                    pass
            return d
        return None

    def get_scans(self, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM scan_history ORDER BY start_time DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        conn = self._get_conn()
        try:
            yield
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# ── 双写适配器 ──────────────────────────────────────────

class DualWriteRepository:
    """同时写入 JSON 和 SQLite，读取优先 SQLite。

    用法：
        from core.repositories.json_repository import JsonRepository
        json_repo = JsonRepository(Path("data/registry.json"), key_field="file_path")
        sql_repo = SqliteRepository("data/trident.db")
        repo = DualWriteRepository(json_repo, sql_repo)
    """

    def __init__(self, json_repo, sql_repo):
        self._json = json_repo
        self._sql = sql_repo

    def save(self, record_id: str, data: Dict[str, Any]) -> None:
        self._json.save(record_id, data)
        try:
            self._sql.save(record_id, data)
        except Exception as e:
            logger.warning("DualWrite: SQLite save failed for %s: %s", record_id, e)

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        try:
            r = self._sql.get(record_id)
            if r:
                return r
        except Exception:
            pass
        return self._json.get(record_id)

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            return self._sql.list_all(limit, offset)
        except Exception:
            return self._json.list_all(limit, offset)

    def query(self, filters: Dict[str, Any],
              limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            return self._sql.query(filters, limit, offset)
        except Exception:
            return self._json.query(filters, limit, offset)

    def delete(self, record_id: str) -> bool:
        ok = self._json.delete(record_id)
        try:
            self._sql.delete(record_id)
        except Exception:
            pass
        return ok

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        try:
            return self._sql.count(filters)
        except Exception:
            return self._json.count(filters)
