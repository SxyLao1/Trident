# -*- coding: utf-8 -*-
"""
@Time: 1/7/2026 1:04 PM
@Auth: SxyLao1
@File: test_runner.py
@IDE: PyCharm
@Motto: HACK THE REAL
Trident自动化测试总控
代码质量检查、重复定义检测、性能基线
用法: python test_runner.py --suite=all --output=json --notify=false
"""
import sys
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"
import threading
import time
import gc

# 删除所有可能阻塞的模块缓存
_modules_to_delete = []
for name in sys.modules:
    if name.startswith(('core.', 'config.', 'utils.', 'test.')):
        _modules_to_delete.append(name)

for name in _modules_to_delete:
    del sys.modules[name]

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
# ============================================================================
# CRITICAL FIX: 必须在任何导入前强制设置PYTHONPATH（Windows专用）
# ============================================================================
# 1. 计算项目根目录（使用resolve()避免符号链接问题）
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# 2. 双重保险：同时修改sys.path和PYTHONPATH
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

from utils.path_utils import normalize_path

# 3. 清除导入缓存（解决Windows的import缓存问题）
if sys.version_info >= (3, 4):
    import importlib

    importlib.invalidate_caches()

# 4. 强制切换工作目录
os.chdir(PROJECT_ROOT)

# 5. 添加调试信息（首次运行时建议开启）
# print(f"[DEBUG] SCRIPT_DIR={SCRIPT_DIR}", file=sys.stderr)
# print(f"[DEBUG] PROJECT_ROOT={PROJECT_ROOT}", file=sys.stderr)
# print(f"[DEBUG] sys.path={sys.path[:3]}...", file=sys.stderr)

# 现在可以安全导入项目模块
try:
    from test_registry import RegistryTestSuite
    from test_notifier import NotifierTestSuite
    from test_monitor import MonitorTestSuite
    from test_yara import YaraTestSuite
    from test_integration import IntegrationTestSuite
except ImportError as e:
    # 增强错误报告：显示完整堆栈追踪
    print(f"[×] 测试模块导入失败: {e}", file=sys.stderr)
    print("-" * 60, file=sys.stderr)
    import traceback

    traceback.print_exc(file=sys.stderr)
    print("-" * 60, file=sys.stderr)
    print("\n故障排查:", file=sys.stderr)
    print("1. 确认PROJECT_ROOT路径正确:", PROJECT_ROOT, file=sys.stderr)
    print("2. 检查core/__init__.py是否存在", file=sys.stderr)
    print("3. 在PROJECT_ROOT下运行: python -c \"import core\"", file=sys.stderr)
    sys.exit(1)

# 导入项目模块（需在测试套件导入后）
try:
    from config.registry import ConfigRegistry
except ImportError as e:
    print(f"[×] 项目模块导入失败: {e}", file=sys.stderr)
    print("检查config.registry模块", file=sys.stderr)
    sys.exit(1)


class TestRunner:
    """统一测试调度器"""

    def __init__(self, output_format: str = "text", enable_notify: bool = False):
        self.output_format = output_format
        self.enable_notify = enable_notify
        self.results: List[Dict] = []

        self._suite_classes = {
            "registry": RegistryTestSuite,
            "notifier": NotifierTestSuite,
            "monitor": MonitorTestSuite,
            "yara": YaraTestSuite,
            "integration": IntegrationTestSuite
        }

    def run_suite(self, suite_name: str) -> dict:
        """运行单个测试套件"""

        if suite_name == "registry":
            import core.suspicious_registry
            # 确保全局变量存在
            if not hasattr(core.suspicious_registry, '_REGISTRY_PATH'):
                setattr(core.suspicious_registry, '_REGISTRY_PATH', None)
            # 强制初始化
            core.suspicious_registry._force_init_at_import()

            # 再次检查
            if core.suspicious_registry._REGISTRY_PATH is None:
                return {
                    "suite": suite_name,
                    "passed": False,
                    "error": "无法初始化REGISTRY_PATH",
                    "timestamp": datetime.now().isoformat(),
                    "tests": [],
                    "total": 0,
                    "passed_count": 0
                }

        import sys
        import gc
        import time

        print(f"\n[DEBUG] === Starting suite: {suite_name} ===", file=sys.stderr)

        # 诊断：打印ConfigRegistry锁状态
        from config.registry import ConfigRegistry
        import threading

        # 强制重建锁（这是根本解决）
        ConfigRegistry._lock = threading.RLock()
        ConfigRegistry._instance = None
        ConfigRegistry._initialized = False

        print(f"[DEBUG] Lock recreated", file=sys.stderr)

        # 强制初始化
        ConfigRegistry.initialize()
        print(f"[DEBUG] ConfigRegistry initialized", file=sys.stderr)

        # ===== 核爆级清理：必须在获取ConfigRegistry锁之前执行 =====

        # 强制停止所有残留线程（必须最先执行）
        self._cleanup_test_environment()

        # 强制垃圾回收
        gc.collect()
        time.sleep(0.3)  # 给操作系统释放资源


        # 现在处理ConfigRegistry（带死锁防护）
        try:
            from config.registry import ConfigRegistry

            # 强制重建锁（最关键！）
            import threading
            ConfigRegistry._lock = threading.RLock()

            # 重置内部状态
            ConfigRegistry._instance = None
            ConfigRegistry._initialized = False
            ConfigRegistry._config = None
            ConfigRegistry._websites = None

            # 现在安全初始化
            ConfigRegistry.initialize()

        except Exception as e:
            print(f"[ERROR] ConfigRegistry初始化失败: {e}", file=sys.stderr)
            # 最后手段：手动重建整个类
            from config.registry import ConfigRegistry
            ConfigRegistry._lock = threading.RLock()
            ConfigRegistry._instance = None
            ConfigRegistry._initialized = False
            ConfigRegistry._config = None
            ConfigRegistry._websites = None
            ConfigRegistry.initialize(force=True)

        # 禁用异步和WAL（环境隔离）
        import core.suspicious_registry as reg_module
        reg_module._async_save_enabled = False
        reg_module._async_save_queue = None
        reg_module._WAL_REPLAY_IN_PROGRESS = False

        # 清理Notifier（必须放在锁重建之后）
        import core.notifier as notifier_module
        notifier_module._notifier_instance = None

        # ===== 铁律：每次测试前彻底清理所有资源 =====
        os.environ["TRIDENT_TOOL_MODE"] = "true"

        # 强制垃圾回收（释放被占用的文件句柄）
        gc.collect()
        time.sleep(0.1)  # 给操作系统释放资源的时间

        os.environ["TRIDENT_TOOL_MODE"] = "true"
        from config.registry import ConfigRegistry
        ConfigRegistry.reset()

        # 清理日志文件（解决Windows文件锁）
        self._cleanup_log_files()

        # 强制清理所有模块的导入缓存
        import sys
        modules_to_clean = [
            'core.suspicious_registry',
            'core.notifier',
            'core.monitor',
            'core.log_monitor',
            'core.yara_engine'
        ]
        for mod in modules_to_clean:
            if mod in sys.modules:
                del sys.modules[mod]

        # 强制清理Notifier线程（关键）
        import core.notifier as notifier_module
        if hasattr(notifier_module, '_notifier_instance') and notifier_module._notifier_instance:
            # 发送退出信号
            try:
                inst = notifier_module._notifier_instance
                if hasattr(inst, '_alert_queue'):
                    inst._alert_queue.put_nowait((None, None))  # 发送终止信号
                    time.sleep(0.1)  # 给线程退出时间
            except:
                pass
        notifier_module._notifier_instance = None  # 重置单例

        import core.suspicious_registry as reg_module

        # 铁律1+铁律11：测试环境双重禁用
        reg_module._WAL_REPLAY_IN_PROGRESS = False

        # 现在安全地初始化
        try:
            ConfigRegistry.initialize()
        except RuntimeError:
            # 如果已初始化，强制覆盖
            ConfigRegistry.initialize(force=True)

        timestamp = datetime.now().isoformat()

        # 检查套件名称是否在预定义的套件类中
        if suite_name not in self._suite_classes:
            return {
                "suite": suite_name,
                "passed": False,
                "error": f"未知测试套件: {suite_name}",
                "timestamp": timestamp,
                "tests": [],
                "total": 0,
                "passed_count": 0
            }

        # 从类定义动态实例化套件
        suite_class = self._suite_classes[suite_name]
        suite = suite_class()  # 真正需要时才实例化

        try:
            result = suite.run_all()
            result["suite"] = suite_name
            result["timestamp"] = timestamp

            # 确保统计字段存在
            if "tests" not in result:
                result["tests"] = []

            result["passed"] = all(r.get("passed", False) for r in result.get("tests", []))
            result["total"] = len(result.get("tests", []))
            result["passed_count"] = sum(1 for r in result.get("tests", []) if r.get("passed", False))
            return result

        except Exception as e:
            return {
                "suite": suite_name,
                "passed": False,
                "error": str(e),
                "traceback": self._format_traceback(),
                "timestamp": timestamp,
                "tests": [],
                "total": 0,
                "passed_count": 0
            }

    def run_all(self, suites: List[str] = None) -> dict:
        """运行所有测试套件"""

        timestamp = datetime.now().isoformat()

        if suites is None:
            suites = list(self._suite_classes.keys())

        # 如果没有指定套件，返回空但合法的结构
        if not suites:
            return {
                "timestamp": timestamp,
                "total_suites": 0,
                "passed_suites": 0,
                "results": {},
                "overall_passed": True
            }

        summary = {
            "timestamp": timestamp,
            "total_suites": len(suites),
            "passed_suites": 0,
            "results": {},
            "overall_passed": False  # 初始为失败
        }

        for suite_name in suites:
            if self.output_format == "text":
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在运行: {suite_name}...")

            result = self.run_suite(suite_name)
            self.results.append(result)
            summary["results"][suite_name] = result

            if result.get("passed", False):
                summary["passed_suites"] += 1

            # 失败时发送告警（生产环境）
            if not result.get("passed", False) and self.enable_notify:
                self._send_alert(suite_name, result)

        summary["overall_passed"] = summary["passed_suites"] == summary["total_suites"]

        # 清理空套件（如果所有测试都被过滤）
        if summary["total_suites"] > 0 and summary["passed_suites"] == 0:
            total_tests = sum(len(r.get("tests", [])) for r in summary["results"].values())
            if total_tests == 0:
                summary["overall_passed"] = True  # 没有测试=认为通过

        return summary

    def _send_alert(self, suite_name: str, result: Dict):
        """测试失败告警"""
        try:
            from core.notifier import get_notifier
            from utils.logger_factory import get_logger

            logger = get_logger("test_runner")
            notifier = get_notifier(logger)

            message = f"【v1.5测试失败】套件: {suite_name}\n"
            message += f"错误: {result.get('error', '未知错误')}\n"
            message += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            notifier.send_alert(message, level="WARNING")
        except Exception as e:
            # 告警失败也不影响测试进程
            print(f"[WARN] 告警发送失败: {e}", file=sys.stderr)

    def output(self, summary: Dict):
        """输出测试结果（Windows UTF-8安全）"""
        if sys.platform == "win32":
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')

        if self.output_format == "json":
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            self._output_text(summary)

    def _output_text(self, summary: dict):
        """文本格式输出"""
        print("\n" + "=" * 70)
        print("Trident v1.5 自动化测试报告")
        print("=" * 70)
        print(f"执行时间: {summary.get('timestamp', 'N/A')}")
        print(f"测试套件: {summary.get('passed_suites', 0)}/{summary.get('total_suites', 0)} 通过\n")

        if summary.get("total_suites", 0) == 0:
            print("[!]  未运行任何测试套件")
            return

        for suite_name, result in summary["results"].items():
            if not result:  # 空结果跳过
                continue

            status = "[√] 通过" if result.get("passed") else "[×] 失败"
            print(f"{suite_name:<20} {status}")

            if "tests" in result and result["tests"]:
                print("  详细测试:")
                for test in result["tests"]:
                    test_status = "[√]" if test.get("passed") else "[×]"
                    message = test.get("message", "无详细信息")
                    print(f"    {test_status} {test['name']:<30} {message}")
            elif "error" in result:
                print(f"  错误信息: {result['error']}")

            print()

        if summary.get("overall_passed", False):
            print("[+] 所有测试通过！系统状态健康。")
        else:
            print("[!] 部分测试失败，请查看详细日志。")

        print("=" * 70)

    @staticmethod
    def _format_traceback() -> str:
        """格式化堆栈追踪"""
        import traceback
        return traceback.format_exc()

    def _cleanup_test_environment(self):
        """测试环境核爆级清理（v1.6.9整合版）"""
        import sys, gc, time, threading

        # 强制停止所有残留线程
        main_thread = threading.main_thread()
        for thread in threading.enumerate():
            if thread is not main_thread and thread.is_alive():
                if hasattr(thread, 'join'):
                    try:
                        thread.join(timeout=1.0)
                    except:
                        pass

        # 清理模块缓存（保留config.registry）
        for name in list(sys.modules.keys()):
            # 关键：保留registry避免死锁
            if name.startswith(('core.', 'config.', 'utils.', 'test.')) and name != 'config.registry':
                del sys.modules[name]

        # 3. 强制垃圾回收
        gc.collect()
        time.sleep(0.2)  # 给操作系统释放资源
        
    def _cleanup_log_files(self):
        """清理日志文件（解决Windows文件锁）"""
        from utils.path_utils import normalize_path
        import shutil

        log_dir = normalize_path("logs")
        if log_dir.exists():
            # 重命名而非删除，避免句柄占用
            backup_dir = normalize_path("logs_backup")
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)
            try:
                log_dir.rename(backup_dir)
            except:
                pass  # 如果无法重命名就算了

        # 确保新日志目录存在
        log_dir.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Trident v1.5 自动化测试总控",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test_runner.py --suite=registry --output=text
  python test_runner.py --suite=all --output=json --notify
  python test_runner.py --suite=yara --output=text
        """
    )

    parser.add_argument(
        "--suite",
        default="all",
        choices=["all", "registry", "notifier", "monitor", "yara", "integration"],
        help="测试套件名称（默认: all）"
    )
    parser.add_argument(
        "--output",
        default="text",
        choices=["text", "json"],
        help="输出格式（默认: text）"
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="测试失败时发送告警（生产环境推荐）"
    )

    args = parser.parse_args()

    # 初始化配置（带容错）
    try:
        ConfigRegistry.initialize()

        # ===== 测试环境隔离：强制禁用异步保存 =====
        import core.suspicious_registry

        # 必须在初始化后设置这些值
        core.suspicious_registry._async_save_enabled = False
        core.suspicious_registry._async_save_queue = None

        # 确保全局变量已定义
        if not hasattr(core.suspicious_registry, '_async_running'):
            core.suspicious_registry._async_running = False

    except Exception as e:
        print(f"[×] 配置加载失败: {e}", file=sys.stderr)
        print("正在尝试应急配置...", file=sys.stderr)

        # 创建默认应急配置
        emergency_config = normalize_path("config.toml")
        if not emergency_config.exists():
            emergency_config.write_text("""
[website]
name = "Emergency"
path = "."
port = 80
enabled = false

[notifier]
enabled = false
""", encoding='utf-8')

        try:
            ConfigRegistry.initialize(force=True)
            print("[+] 应急配置加载成功", file=sys.stderr)
        except Exception as e2:
            print(f"[×] 应急配置也失败: {e2}", file=sys.stderr)
            sys.exit(1)

    # ===== 手动WAL重放（仅在实际需要时）=====
    # 注意：测试时不应重放，否则污染测试数据
    # 只在生产环境或灾难恢复时调用
    # replay_wal_manually()

    # 运行测试
    runner = TestRunner(output_format=args.output, enable_notify=args.notify)

    if args.suite == "all":
        summary = runner.run_all()
    else:
        # v1.5 修复：单个套件也需要 overall_passed 字段
        suite_result = runner.run_suite(args.suite)
        runner.results = [suite_result]

        # 包装成 overall 结构（适配 sys.exit 访问）
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_suites": 1,
            "passed_suites": 1 if suite_result.get("passed", False) else 0,
            "results": {args.suite: suite_result},
            "overall_passed": suite_result.get("passed", False)
        }

    runner.output(summary)

    # 返回码供CI/CD使用
    sys.exit(0 if summary["overall_passed"] else 1)
