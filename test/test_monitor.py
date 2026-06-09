import sys
import os

# Ensure project root is in path when running standalone
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# -*- coding: utf-8 -*-
"""
@Time: 1/7/2026 1:14 PM
@Auth: SxyLao1
@File: test_monitor.py
@IDE: PyCharm
@Motto: HACK THE REAL
Monitor文件监控测试套件
测试目标：事件捕获、去重、魔术头检测、目录缓存
"""
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"
from utils.path_utils import normalize_path
import time
import tempfile
from core.monitor import FileMonitorHandler
from core.models import ScanOptions
from utils.logger_factory import get_logger


class MonitorTestSuite:
    """Monitor测试套件"""

    def run_all(self) -> dict:
        try:
            from config.registry import ConfigRegistry
            ConfigRegistry.initialize()
        except RuntimeError:
            pass

        return {
            "tests": [
                self.test_file_create_detection(),
                self.test_duplicate_filtering(),
                self.test_magic_number_detection(),
                self.test_directory_cache()
            ]
        }

    def test_file_create_detection(self) -> dict:
        """测试文件创建事件捕获"""
        # 使用临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = normalize_path(tmpdir)
            detected_files = []

            def mock_scan(path, opts, logger):
                detected_files.append(path.name)
                return None

            handler = FileMonitorHandler(
                scan_callback=mock_scan,
                scan_options=ScanOptions(),
                base_path=base_path,
                logger=get_logger("test_monitor")
            )

            # 创建测试文件
            test_file = base_path / "test_create.php"
            test_file.write_text("<?php eval(1); ?>")

            # 模拟事件
            class MockEvent:
                def __init__(self, path):
                    self.src_path = str(path)
                    self.is_directory = False

            handler.on_created(MockEvent(test_file))
            time.sleep(0.1)  # 等待处理

            return {
                "name": "文件创建检测",
                "passed": "test_create.php" in detected_files,
                "message": f"检测到的文件: {detected_files}"
            }

    def test_duplicate_filtering(self) -> dict:
        """测试5秒去重窗口（生产值）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = normalize_path(tmpdir)
            call_count = [0]

            def mock_scan(path, opts, logger):
                call_count[0] += 1
                return None

            handler = FileMonitorHandler(
                scan_callback=mock_scan,
                scan_options=ScanOptions(),
                base_path=base_path,
                logger=get_logger("test_duplicate")
            )

            # 使用普通文本内容，避免触发_is_force_scan_file
            test_file = base_path / "test_dup.php"
            test_file.write_text("normal text content")  # ← 普通内容

            class MockEvent:
                def __init__(self, path):
                    self.src_path = str(path)
                    self.is_directory = False

            # 第一次事件：应触发扫描
            handler.on_created(MockEvent(test_file))

            # 第二次事件：在5秒窗口内，应被去重
            handler.on_modified(MockEvent(test_file))

            # 等待去重窗口过期（必须>5秒）
            time.sleep(5.1)  # ← 关键：超过5秒

            # 第三次事件：窗口过期后，应重新触发扫描
            handler.on_modified(MockEvent(test_file))

            return {
                "name": "事件去重过滤",
                "passed": call_count[0] == 2,  # ← 预期2次（创建1次 + 过期后修改1次）
                "message": f"扫描调用次数: {call_count[0]} (预期: 2次，第一次+过期后第三次)"
            }
    def test_magic_number_detection(self) -> dict:
        """测试PHP魔术头检测"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = normalize_path(tmpdir)

            # 创建无后缀但包含PHP代码的文件
            test_file = base_path / "shell"
            test_file.write_text("<?php eval($_POST['x']); ?>")

            handler = FileMonitorHandler(
                scan_callback=lambda p, o, l: None,
                scan_options=ScanOptions(),
                base_path=base_path,
                logger=get_logger("test_magic")
            )

            is_script = handler._is_force_scan_file(test_file)

            return {
                "name": "魔术头检测（无后缀）",
                "passed": is_script,
                "message": f"识别为脚本: {is_script}"
            }

    def test_directory_cache(self) -> dict:
        """测试目录缓存命中率"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = normalize_path(tmpdir)
            handler = FileMonitorHandler(
                scan_callback=lambda p, o, l: None,
                scan_options=ScanOptions(),
                base_path=base_path,
                logger=get_logger("test_cache")
            )

            # 记录目录
            subdir = base_path / "subdir"
            subdir.mkdir()
            handler._record_directory(subdir)

            # 检查缓存
            is_known = handler._is_known_directory(subdir)

            return {
                "name": "目录缓存",
                "passed": is_known,
                "message": f"缓存命中: {is_known}"
            }

    def test_path_normalization_cross_platform(self):
        """测试跨平台路径标准化"""
        from utils.path_utils import path_to_key

        paths = [
            "E:/WWW/test.php",
            "E:\\\\WWW\\\\test.php",
            "../WWW/test.php"  # 假设当前在E:/
        ]

        from utils.path_utils import path_to_key
        keys = [path_to_key(p) for p in paths]

        all_same = all(k == keys[0] for k in keys)

        return {
            "name": "跨平台路径标准化",
            "passed": all_same,
            "message": f"所有路径标准化结果一致: {all_same}"
        }
