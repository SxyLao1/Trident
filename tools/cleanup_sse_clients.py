# -*- coding: utf-8 -*-
"""
@Time: 1/18/2026 8:19 PM
@Auth: SxyLao1
@File: cleanup_sse_clients.py
@IDE: PyCharm
@Motto: HACK THE REAL
手动清理僵尸SSE客户端（用于紧急恢复）
"""
import os
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.blueprints.admin_bp import _sse_clients


def cleanup_zombie_clients():
    """清理所有SSE客户端（紧急恢复）"""
    print(f"[CLEANUP] 当前SSE客户端数: {len(_sse_clients)}")

    # 清空列表（强制断开所有连接）
    _sse_clients.clear()

    print(f"[CLEANUP] 清理后SSE客户端数: {len(_sse_clients)}")
    print("[CLEANUP] 所有僵尸连接已强制断开")


if __name__ == "__main__":
    cleanup_zombie_clients()