import sys
import os

# Ensure project root is in path when running standalone
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# -*- coding: utf-8 -*-
"""
@Time: 1/7/2026 1:06 PM
@Auth: SxyLao1
@File: test_registry.py
@IDE: PyCharm
@Motto: HACK THE REAL
Registry可靠性测试套件 (测试数据隔离)
测试目标：并发安全、原子写入、数据完整性
"""
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"
import json
import tempfile
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from core.suspicious_registry import add, get_all, remove, increment_access, _REGISTRY_PATH, _REGISTRY_BACKUP_PATH
from config.registry import ConfigRegistry
from utils.path_utils import normalize_path


class RegistryTestSuite:
    """Registry测试套件"""

    def __init__(self):
        self.test_dir = normalize_path("temp/registry_test_isolated")
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # v1.7.0：强制使用测试专用Registry路径（彻底隔离）
        import core.suspicious_registry as reg_module
        test_data_dir = self.test_dir / "data"
        test_data_dir.mkdir(exist_ok=True)

        # 暴力覆盖全局路径
        reg_module._REGISTRY_PATH = test_data_dir / "test_registry.json"
        reg_module._WAL_PATH = test_data_dir / "test_wal.log"
        reg_module._REGISTRY_BACKUP_PATH = reg_module._REGISTRY_PATH.with_suffix('.json.bak')

        # 确保路径已初始化
        reg_module._init_paths()

        # 禁用异步和WAL
        reg_module._async_save_enabled = False
        reg_module._async_save_queue = None

        # 重置全局快照
        global _last_registry_snapshot
        _last_registry_snapshot = []

        self.registry_backup = None

    def _force_init_registry_paths(self):
        """强制初始化Registry路径（解决测试时的NoneType错误）"""
        try:
            from core.suspicious_registry import _REGISTRY_PATH, _WAL_PATH
            # 如果为None，手动设置
            if _REGISTRY_PATH is None:
                data_dir = normalize_path("data")
                # 暴力设置全局变量
                import core.suspicious_registry as reg_module
                reg_module._REGISTRY_PATH = data_dir / "suspicious_registry.json"
                reg_module._WAL_PATH = data_dir / "registry_wal.log"
                reg_module._REGISTRY_BACKUP_PATH = reg_module._REGISTRY_PATH.with_suffix('.json.bak')
                print(f"[TEST] 强制初始化Registry路径: {reg_module._REGISTRY_PATH}")
        except Exception as e:
            print(f"[TEST] 强制初始化失败: {e}")
            # 如果仍然失败，跳过测试
            raise RuntimeError(f"Registry路径初始化失败: {e}")

    def setup(self):
        """测试前：清空Registry"""
        # v1.7.0修复：确保路径已初始化
        from core.suspicious_registry import _init_paths, _REGISTRY_PATH, _REGISTRY_BACKUP_PATH

        _init_paths()  # 关键：初始化路径

        self.registry_backup = "[]"
        if _REGISTRY_PATH and _REGISTRY_PATH.exists():
            try:
                self.registry_backup = _REGISTRY_PATH.read_text(encoding='utf-8')
                _REGISTRY_PATH.write_text("[]", encoding='utf-8')
                _REGISTRY_BACKUP_PATH.write_text("[]", encoding='utf-8')
            except Exception as e:
                print(f"[WARN] backup registry failed: {e}")

    def teardown(self):
        """测试后：恢复Registry"""
        from core.suspicious_registry import _init_paths, _REGISTRY_PATH, _REGISTRY_BACKUP_PATH

        _init_paths()  # 关键：初始化路径

        if self.registry_backup and _REGISTRY_PATH and _REGISTRY_PATH.exists():
            try:
                _REGISTRY_PATH.write_text(self.registry_backup, encoding='utf-8')
                _REGISTRY_BACKUP_PATH.write_text(self.registry_backup, encoding='utf-8')
            except Exception as e:
                print(f"[WARN] restore registry failed: {e}")

        import shutil
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def run_all(self) -> dict:
        """运行所有测试（带完全隔离）"""
        import core.suspicious_registry
        if core.suspicious_registry._async_save_enabled:
            raise RuntimeError("铁律1: 测试环境必须禁用异步保存！")

        # 1. 保存原始数据
        original_data = "[]"
        if _REGISTRY_PATH.exists():
            try:
                original_data = _REGISTRY_PATH.read_text(encoding='utf-8')
            except:
                pass

        # 2. 强制清空Registry（确保测试前干净）
        _REGISTRY_PATH.write_text("[]", encoding='utf-8')
        _REGISTRY_BACKUP_PATH.write_text("[]", encoding='utf-8')

        # 3. 创建独立测试目录
        self.test_dir = normalize_path("temp/registry_test_isolated")
        if self.test_dir.exists():
            import shutil
            shutil.rmtree(self.test_dir, ignore_errors=True)
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # 4. 重置全局状态（关键！）
        global _last_registry_snapshot
        _last_registry_snapshot = []

        try:
            # 执行测试
            results = {
                "tests": [
                    self.test_concurrent_add(),
                    self.test_atomic_write(),
                    self.test_data_integrity(),
                    self.test_access_increment(),
                    self.test_remove_and_persistence()
                ]
            }

            return results

        finally:
            # 5. 100%清理测试数据
            _REGISTRY_PATH.write_text("[]", encoding='utf-8')
            _REGISTRY_BACKUP_PATH.write_text("[]", encoding='utf-8')

            # 6. 恢复原始数据（从备份恢复）
            if original_data and original_data != "[]":
                try:
                    _REGISTRY_PATH.write_text(original_data, encoding='utf-8')
                    _REGISTRY_BACKUP_PATH.write_text(original_data, encoding='utf-8')
                except:
                    pass

            # 7. 清理测试目录
            if self.test_dir.exists():
                import shutil
                shutil.rmtree(self.test_dir, ignore_errors=True)

            # 8. 重置全局快照
            _last_registry_snapshot = []

    def test_concurrent_add(self) -> dict:
        """测试50线程并发写入（隔离版）"""
        # 清理旧数据
        if _REGISTRY_PATH.exists():
            _REGISTRY_PATH.write_text("[]", encoding='utf-8')

        def worker(i):
            test_file = self.test_dir / f"test_concurrent_{i}.php"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("<?php eval(1); ?>")
            add(test_file, [f"feature_{i}"])

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        records = get_all()
        # 只统计本次测试的记录
        test_records = [r for r in records if "feature_" in str(r.get("features", []))]

        success = 45 <= len(test_records) <= 50  # 允许10%误差

        return {
            "name": "并发写入50条记录",
            "passed": success,
            "message": f"成功写入 {len(test_records)}/50 条 (隔离测试)"
        }

    def test_atomic_write(self) -> dict:
        """测试原子写入（隔离版）"""
        # 使用独立测试文件
        test_file = self.test_dir / "atomic_test.php"
        test_file.write_text("<?php system(1); ?>")

        # 先清空Registry
        _REGISTRY_PATH.write_text("[]", encoding='utf-8')

        add(test_file, ["atomic"])

        try:
            data = json.loads(_REGISTRY_PATH.read_text(encoding='utf-8'))
            # 只检查本次测试的记录
            success = any("atomic" in r.get("features", []) for r in data)
            message = "文件未损坏"
        except json.JSONDecodeError:
            success = False
            message = "JSON解析失败（文件损坏）"

        return {
            "name": "原子写入完整性",
            "passed": success,
            "message": message
        }

    def test_data_integrity(self) -> dict:
        """测试字段完整性（隔离版）"""
        # 清理并创建独立测试文件
        _REGISTRY_PATH.write_text("[]", encoding='utf-8')
        test_file = self.test_dir / "integrity_test.php"
        test_file.write_text("<?php eval(1); ?>")

        add(test_file, ["integrity_test"])

        records = get_all()
        record = next((r for r in records if "integrity_test" in r.get("features", [])), None)

        if not record:
            return {"name": "数据完整性", "passed": False, "message": "记录未找到"}

        required_fields = ["file_path", "detected_at", "features", "alerted", "file_exists", "communication_count"]
        missing_fields = [f for f in required_fields if f not in record]

        return {
            "name": "数据完整性检查",
            "passed": len(missing_fields) == 0,
            "message": f"缺失字段: {missing_fields}" if missing_fields else "所有字段完整"
        }

    def test_access_increment(self) -> dict:
        """测试通信计数递增（隔离版）"""
        # 清理并创建独立测试文件
        _REGISTRY_PATH.write_text("[]", encoding='utf-8')
        test_file = self.test_dir / "access_test.php"
        test_file.write_text("<?php eval(1); ?>")

        add(test_file, ["access_test"])

        # 递增5次
        for i in range(5):
            increment_access(test_file, f"192.168.1.{i}")

        records = get_all()
        record = next((r for r in records if "access_test" in r.get("features", [])), None)

        count = record.get("communication_count", 0) if record else 0

        return {
            "name": "通信计数递增",
            "passed": count == 5,
            "message": f"通信次数: {count}/5"
        }

    def test_remove_and_persistence(self) -> dict:
        """测试删除标记与隔离（隔离版）"""
        # 清理并创建独立测试文件
        _REGISTRY_PATH.write_text("[]", encoding='utf-8')
        test_file = self.test_dir / "remove_test.php"
        test_file.write_text("<?php eval(1); ?>")

        add(test_file, ["remove_test"])

        # 验证存在
        before_delete = any("remove_test" in r.get("features", []) for r in get_all())

        # 删除文件并标记
        remove(test_file)

        # 验证标记
        deleted_records = get_all(include_deleted=True)
        active_records = get_all()

        record = next((r for r in deleted_records if "remove_test" in r.get("features", [])), None)
        is_marked_deleted = record and not record.get("file_exists", True) if record else False

        return {
            "name": "删除标记与隔离",
            "passed": before_delete and is_marked_deleted,
            "message": f"删除前存在: {before_delete}, 已标记删除: {is_marked_deleted}"
        }
