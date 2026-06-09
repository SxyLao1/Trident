# -*- coding: utf-8 -*-
"""
@Time: 1/7/2026 3:56 PM
@Auth: SxyLao1
@File: replay_wal.py
@IDE: PyCharm
@Motto: HACK THE REAL
手动WAL重放工具
用法: python tools/replay_wal.py
"""
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.suspicious_registry import replay_wal_manually

if __name__ == "__main__":
    print("=" * 60)
    print("WAL手动重放工具")
    print("=" * 60)

    recovered = replay_wal_manually()

    print(f"\n重放完成！恢复 {recovered} 条记录")
    print("=" * 60)