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
@File: test_integration.py
@IDE: PyCharm
@Motto: HACK THE REAL
集成测试套件
模拟真实攻击场景：上传Webshell → 触发监控 → 告警 → 日志溯源
"""
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"
import sys
from pathlib import Path
from utils.path_utils import normalize_path

import time
import tempfile
from core.monitor import WebsiteMonitor
from core.log_analyzer import LogAnalyzer
from core.suspicious_registry import add, get_all
from core.models import Website, ScanOptions
from utils.logger_factory import get_logger

class IntegrationTestSuite:
    """集成测试套件"""

    def __init__(self):
        # v1.7.0添加：初始化测试目录
        from utils.path_utils import normalize_path
        import shutil

        self.test_dir = normalize_path("temp/integration_test")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def run_all(self) -> dict:

        try:
            from config.registry import ConfigRegistry
            ConfigRegistry.initialize()
        except RuntimeError:
            pass

        return {
            "tests": [
                self.test_full_detection_flow(),
                self.test_alert_flow(),
                self.test_log_traceability(),
                self.test_registry_monitor_integration()
            ]
        }

    def test_full_detection_flow(self) -> dict:
        """完整检测流程测试"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = normalize_path(tmpdir)
            logger = get_logger("integration")

            # 创建监控器
            website = Website(
                name="test_site",
                path=base_path,
                port=80,
                enabled=True,
                scan_options=ScanOptions(monitor_extensions=[".php"])
            )

            detected_files = []

            def mock_scan(path, opts, logger):
                detected_files.append(path.name)
                return None

            monitor = WebsiteMonitor(website, mock_scan, logger)
            monitor.start()

            # 创建Webshell文件
            shell_file = base_path / "shell.php"
            shell_file.write_text("<?php eval($_POST['x']); ?>")

            time.sleep(0.5)  # 等待监控响应
            monitor.stop()

            return {
                "name": "完整检测流程",
                "passed": "shell.php" in detected_files,
                "message": f"检测到文件: {detected_files}"
            }

    def test_alert_flow(self) -> dict:
        """测试告警流程（从Registry到Notifier）"""
        # 创建测试Webshell
        test_file = normalize_path("temp/alert_flow_test.php")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("<?php system(1); ?>")

        # 添加到Registry
        add(test_file, ["alert_test"])

        # 检查Registry记录
        records = get_all()
        record = next((r for r in records if "alert_test" in r.get("features", [])), None)

        # 模拟访问（增加通信计数）
        if record:
            from core.suspicious_registry import increment_access
            increment_access(test_file, "192.168.1.100")

        # 验证告警标记
        has_record = record is not None
        alerted = record.get("alerted", False) if record else False

        return {
            "name": "告警流程集成",
            "passed": has_record,
            "message": f"Registry记录: {has_record}, 告警状态: {alerted}"
        }

    def test_log_traceability(self) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            log_file = temp_path / "mock_access.log"
            log_content = """192.168.1.100 - - [07/Jan/2026:10:00:00 +0800] "GET /temp/shell.php?cmd=whoami HTTP/1.1" 200 512
    192.168.1.101 - - [07/Jan/2026:10:00:01 +0800] "POST /temp/shell.php HTTP/1.1" 200 256
    """
            log_file.write_text(log_content, encoding='utf-8')
            shell_path = temp_path / "shell.php"
            shell_path.write_text("<?php eval(1); ?>")
            add(shell_path, ["log_test"])

            # 关键修复：在ScanOptions中显式配置access_log_path
            website = Website(
                name="test",
                path=temp_path,
                port=80,
                enabled=True,
                scan_options=ScanOptions(
                    access_log_path=str(log_file)  # 显式配置路径
                )
            )
            analyzer = LogAnalyzer(website, get_logger("integration"))
            # 移除 analyzer.log_path = log_file  # 不再需要直接赋值

            result = analyzer.analyze_shell_access(shell_path)

            has_ips = result and len(result.get("suspicious_ips", {})) > 0

            return {
                "name": "日志溯源能力",
                "passed": has_ips,
                "message": f"发现可疑IP: {len(result.get('suspicious_ips', {})) if result else 0}个"
            }

    def test_registry_monitor_integration(self) -> dict:
        """测试Registry与Monitor的联动（文件删除后Registry标记）"""
        # v1.7.0修复：使用绝对路径并确保目录同步
        test_file = self.test_dir / "reg_monitor_test.php"

        # 确保目录存在
        test_file.parent.mkdir(parents=True, exist_ok=True)

        # 写入测试内容
        test_file.write_text("<?php eval(1); ?>")

        # 验证文件确实创建了
        if not test_file.exists():
            return {
                "name": "Registry-Monitor联动",
                "passed": False,
                "message": f"测试文件创建失败: {test_file}"
            }

        # 添加到Registry
        from core.suspicious_registry import add, get_all
        add(test_file, ["integration_test"])

        # 等待数据写入完成
        time.sleep(0.2)

        # 验证Registry中有记录
        records_before = get_all(include_deleted=True)
        before_delete = any("integration_test" in r.get("features", []) for r in records_before)

        if not before_delete:
            # 如果找不到，可能是路径键不匹配，打印调试信息
            return {
                "name": "Registry-Monitor联动",
                "passed": False,
                "message": f"添加失败，Registry中未找到记录。记录数: {len(records_before)}, 路径: {test_file}"
            }

        # 删除文件
        if test_file.exists():
            test_file.unlink()

        # 模拟Monitor的删除事件处理
        from core.suspicious_registry import remove
        removed = remove(test_file)

        # 等待删除操作完成
        time.sleep(0.1)

        # 验证Registry已标记删除
        records_after = get_all(include_deleted=True)
        after_delete = not any(
            r.get("file_exists", True) for r in records_after
            if "integration_test" in r.get("features", [])
        )

        return {
            "name": "Registry-Monitor联动",
            "passed": before_delete and removed and after_delete,
            "message": f"删除前存在: {before_delete}, 删除成功: {removed}, 删除后标记: {after_delete}"
        }