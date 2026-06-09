# -*- coding: utf-8 -*-
"""
@Time: 1/7/2026 10:19 PM
@Auth: SxyLao1
@File: false_positive.py
@IDE: PyCharm
@Motto: HACK THE REAL
用户发现误报后，可从Registry移除，避免持续告警
"""
import sys
import os
from pathlib import Path
os.environ["TRIDENT_TOOL_MODE"] = "true"
from utils.path_utils import normalize_path

from utils.project_init import init_project_path
PROJECT_ROOT = init_project_path()

from core.suspicious_registry import remove

def mark_false_positive(file_path: str):
    """标记文件为误报并移除"""
    path = normalize_path(file_path).resolve()
    removed = remove(path)  # 复用现有remove逻辑
    if removed:
        print(f"[√] 已移除: {path.name}")
        print(f"[提示] 建议将文件加入 scan_options.exclude_files")
    else:
        print(f"[×] 文件不在清单中: {path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python tools/false_positive.py <文件路径>")
        sys.exit(1)
    mark_false_positive(sys.argv[1])
