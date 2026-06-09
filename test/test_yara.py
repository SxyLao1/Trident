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
@File: test_yara.py
@IDE: PyCharm
@Motto: HACK THE REAL
YARA引擎测试套件
测试目标：规则加载、命中检测、性能基线
"""
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"
import sys
from pathlib import Path
from core.yara_engine import get_yara_engine
from utils.logger_factory import get_logger
from utils.path_utils import normalize_path
import time


class YaraTestSuite:
    """YARA测试套件"""

    def run_all(self) -> dict:
        # v1.7.0修复：延迟导入，避免模块级ConfigRegistry依赖
        try:
            from config.registry import ConfigRegistry
            ConfigRegistry.initialize()
        except RuntimeError:
            pass

        # 确保YARA已启用
        try:
            from config.registry import ConfigRegistry
            config = ConfigRegistry.get_raw_config()
            yara_enabled = config.get("scanner", {}).get("yara", {}).get("enabled", False)
            if not yara_enabled:
                return {
                    "tests": [{
                        "name": "YARA配置检查",
                        "passed": False,
                        "message": "YARA在config.toml中未启用"
                    }]
                }
        except:
            pass

        from core.yara_engine import get_yara_engine
        from utils.logger_factory import get_logger

        return {
            "tests": [
                self.test_rule_loading(),
                self.test_rule_matching(),
                self.test_performance_baseline(),
                self.test_rule_stats()
            ]
        }

    def test_rule_loading(self) -> dict:
        """测试规则加载"""
        logger = get_logger("test_yara")
        engine = get_yara_engine(logger)

        has_rules = engine.compiled_rules is not None
        rule_count = 0
        if has_rules:
            try:
                rule_count = sum(1 for _ in engine.compiled_rules)
            except:
                pass

        return {
            "name": "YARA规则加载",
            "passed": has_rules and rule_count > 0,
            "message": f"规则加载: {has_rules}, 数量: {rule_count}"
        }

    def test_rule_matching(self) -> dict:
        """测试规则命中"""
        logger = get_logger("test_yara")
        engine = get_yara_engine(logger)

        if not engine.compiled_rules:
            return {
                "name": "规则命中测试",
                "passed": False,
                "message": "规则未加载"
            }

        # 创建测试文件
        test_file = normalize_path("temp/yara_test.php")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("<?php eval($_POST['cmd']); ?>")

        matches = engine.scan(test_file)

        return {
            "name": "规则命中检测",
            "passed": len(matches) > 0,
            "message": f"命中规则数: {len(matches)}"
        }

    def test_performance_baseline(self) -> dict:
        """测试性能基线（扫描1000次）"""
        logger = get_logger("test_yara")
        engine = get_yara_engine(logger)

        if not engine.compiled_rules:
            return {
                "name": "性能基线测试",
                "passed": False,
                "message": "规则未加载"
            }

        # 准备测试文件
        test_file = normalize_path("temp/yara_perf.php")
        test_file.write_text("<?php eval($_POST['x']); ?>")

        # 预热
        engine.scan(test_file)

        # 正式测试
        start = time.perf_counter()
        for _ in range(100):
            engine.scan(test_file)
        elapsed = time.perf_counter() - start

        avg_time = (elapsed / 100) * 1000  # 转换为ms

        return {
            "name": "性能基线（100次扫描）",
            "passed": avg_time < 10.0,  # 平均每次<10ms
            "message": f"平均耗时: {avg_time:.2f}ms"
        }

    def test_rule_stats(self) -> dict:
        """测试规则统计"""
        logger = get_logger("test_yara")
        engine = get_yara_engine(logger)

        if not engine.compiled_rules:
            return {
                "name": "规则统计",
                "passed": False,
                "message": "规则未加载"
            }

        stats = engine.get_rule_stats()
        total = sum(stats.values())

        return {
            "name": "规则分类统计",
            "passed": total > 0,
            "message": f"总计: {total}条, 分类: {list(stats.keys())}"
        }

    def test_memory_leak_prevention(self):
        """验证YARA热加载无内存泄漏"""
        import psutil, gc
        p = psutil.Process()

        engine = get_yara_engine(get_logger('test'))
        initial_mem = p.memory_info().rss

        # 触发10次重载
        for _ in range(10):
            engine._load_rules()
            gc.collect()

        final_mem = p.memory_info().rss
        growth = (final_mem - initial_mem) / initial_mem * 100

        return {
            "name": "YARA内存泄漏防护",
            "passed": growth < 20,  # 增长不超过20%
            "message": f"内存增长: {growth:.1f}% (初始{initial_mem / 1024 / 1024:.1f}MB→最终{final_mem / 1024 / 1024:.1f}MB)"
        }
