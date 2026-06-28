# -*- coding: utf-8 -*-
"""
Trident v1.9.2: 数据仓库实现层

提供 JSON 和 SQLite 两种 Repository 实现。
通过 config.toml [storage] backend 切换：
  - "json"   (默认，向后兼容)
  - "sqlite"  (高性能，WAL 模式)
  - "both"    (双写并行，SQLite 读优先)
"""

from anteumbra.infrastructure.persistence.json_repository import JsonRepository
from anteumbra.infrastructure.persistence.sqlite_repository import SqliteRepository, DualWriteRepository

__all__ = ["JsonRepository", "SqliteRepository", "DualWriteRepository"]
