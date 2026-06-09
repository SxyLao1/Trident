# -*- coding: utf-8 -*-
"""
@Time: 1/12/2026 12:27 AM
@Auth: SxyLao1
@File: check_registry_paths.py
@IDE: PyCharm
@Motto: HACK THE REAL
Registry路径自检工具
"""
import os
import sys
from pathlib import Path
os.environ["TRIDENT_TOOL_MODE"] = "true"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.registry import ConfigRegistry
from core.suspicious_registry import _REGISTRY_PATH, _REGISTRY_BACKUP_PATH
from core.wal_manager import get_wal_path


def check_paths():
    """检查Registry路径状态"""
    print("=" * 70)
    print("Registry路径自检")
    print("=" * 70)

    # 初始化ConfigRegistry
    try:
        ConfigRegistry.initialize()
    except RuntimeError:
        pass

    print(f"REGISTRY_PATH: {_REGISTRY_PATH}")
    wal_path = get_wal_path()
    print(f"WAL_PATH: {wal_path}")
    print(f"BACKUP_PATH: {_REGISTRY_BACKUP_PATH}")

    for path, name in [
        (_REGISTRY_PATH, "主文件"),
        (wal_path, "WAL文件"),
        (_REGISTRY_BACKUP_PATH, "备份文件")
    ]:
        if path:
            print(f"\n{name}:")
            print(f"  路径: {path.absolute()}")
            print(f"  存在: {path.exists()}")
            if path.exists():
                print(f"  大小: {path.stat().st_size} bytes")
        else:
            print(f"\n{name}: None（未初始化）")

    # 测试基本操作
    print("\n=== 测试基本操作 ===")
    try:
        from core.suspicious_registry import add, get_all, remove
        from utils.path_utils import normalize_path

        test_file = normalize_path("temp/test_path.php")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("<?php eval(1); ?>")

        print("1. 添加记录...")
        add(test_file, ['path_test'])
        print("   ✓ 添加成功")

        print("2. 查询记录...")
        records = get_all()
        print(f"   ✓ 查询成功，共{len(records)}条")

        print("3. 删除记录...")
        remove(test_file)
        print("   ✓ 删除成功")

        test_file.unlink()
        print("\n[✓] 所有Registry操作正常")

    except Exception as e:
        print(f"\n[✗] Registry操作失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_paths()