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
@File: test_notifier.py
@IDE: PyCharm
@Motto: HACK THE REAL
Notifier可靠性测试套件
测试目标：队列溢出处理、通道故障转移、异步可靠性
"""
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"
import queue
import sys
from pathlib import Path
from utils.path_utils import normalize_path
import time
import threading
from unittest.mock import patch, MagicMock
from core.notifier import get_notifier
from utils.logger_factory import get_logger

class NotifierTestSuite:
    """Notifier测试套件"""

    def __init__(self):
        self.test_mode = True

    def run_all(self) -> dict:
        # 所有导入都在这里进行
        try:
            from config.registry import ConfigRegistry
            ConfigRegistry.initialize()
        except RuntimeError:
            pass

        # v1.7.0重构：从配置读取测试参数
        config = ConfigRegistry.get_raw_config()
        notifier_cfg = config.get("notifier", {})
        queue_cfg = notifier_cfg.get("queue", {})
        test_maxsize = queue_cfg.get("maxsize", 100)  # 测试环境默认值

        # 禁用实例化的_notifier，使用测试配置
        import core.notifier as notifier_module
        notifier_module._notifier_instance = None

        return {
            "tests": [
                self.test_queue_overflow_handling(test_maxsize),
                self.test_channel_failover(),
                self.test_async_reliability(),
                self.test_overflow_persistence(test_maxsize)
            ]
        }

    def test_queue_overflow_handling(self, test_maxsize: int) -> dict:
        """测试队列溢出处理"""
        logger = get_logger("test_notifier")
        notifier = get_notifier(logger)

        # 禁用工作线程消费（模拟队列积压）
        notifier._alert_thread = None
        notifier._alert_queue = queue.Queue(maxsize=test_maxsize)  # 使用配置值

        # 关键：调用_safe_notify而不是直接操作队列
        overflow_detected = False
        # v1.7.0重构：根据配置值调整测试数量
        test_count = test_maxsize + 20

        for i in range(test_count):
            try:
                notifier._safe_notify(f"溢出测试消息 {i}", "CRITICAL")
            except Exception as e:
                overflow_detected = True

        # 等待文件写入完成
        time.sleep(0.5)

        # 检查溢出文件
        overflow_file = normalize_path("data/alert_overflow.json")
        has_persistence = overflow_file.exists() and overflow_file.stat().st_size > 0

        return {
            "name": "队列溢出处理",
            "passed": has_persistence,
            "message": f"溢出检测: {overflow_detected}, 文件生成: {has_persistence}, 大小: {overflow_file.stat().st_size if has_persistence else 0}"
        }

    def test_channel_failover(self) -> dict:
        """测试通道故障隔离（Mock版）"""
        logger = get_logger("test_notifier")
        notifier = get_notifier(logger)

        # Mock邮件成功，微信失败
        with patch.object(notifier, '_send_email', return_value=True), \
                patch.object(notifier, '_send_wechat', side_effect=Exception("微信故障")), \
                patch.object(notifier, '_send_webhook', return_value=True):

            try:
                notifier.send_alert("故障转移测试", "INFO")
                # 如果无异常抛出，说明故障被隔离
                success = True
            except:
                success = False

            return {
                "name": "通道故障隔离",
                "passed": success,
                "message": "邮件成功，微信故障被隔离"
            }

        notifier._wechat_failure_count = 0
        notifier._wechat_circuit_enabled = True

    def test_async_reliability(self) -> dict:
        """测试异步可靠性（Mock版）"""
        logger = get_logger("test_async")
        notifier = get_notifier(logger)

        # Mock所有发送方法
        with patch.object(notifier, '_send_email', return_value=True), \
                patch.object(notifier, '_send_wechat', return_value=True), \
                patch.object(notifier, '_send_webhook', return_value=True):
            start_time = time.time()
            # 发送50条告警（应该瞬间返回）
            for i in range(50):
                notifier.send_alert(f"异步测试 {i}", "INFO")
            elapsed = time.time() - start_time

            return {
                "name": "异步非阻塞",
                "passed": elapsed < 1.0,
                "message": f"50条告警入队耗时: {elapsed:.3f}s (应<1.0s)"
            }

    def test_overflow_persistence(self, test_maxsize: int) -> dict:
        """测试溢出持久化文件生成"""
        overflow_file = normalize_path("data/alert_overflow.json")
        if overflow_file.exists():
            overflow_file.unlink()

        logger = get_logger("test_overflow")
        notifier = get_notifier(logger)
        notifier._alert_thread = None  # 禁用消费

        # v1.7.0重构：根据配置值调整测试数量
        test_count = test_maxsize + 50

        # 关键：调用业务方法，不是直接操作队列
        for i in range(test_count):
            notifier._safe_notify(f"强制溢出 {i}", "CRITICAL")

        time.sleep(0.5)  # 等待写入

        has_file = overflow_file.exists() and overflow_file.stat().st_size > 0

        return {
            "name": "溢出持久化文件",
            "passed": has_file,
            "message": f"文件生成: {has_file}, 路径: {overflow_file.absolute() if has_file else 'N/A'}"
        }