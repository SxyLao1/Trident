# -*- coding: utf-8 -*-
"""
@Time: 1/13/2026 10:42 PM
@Auth: SxyLao1
@File: verify_log_separation.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.3日志分离验证工具（修复版）
修复: 移除 TRIDENT_TOOL_MODE 干扰，强制加载真实配置
"""
# ============================================================================
# 关键修复：在脚本开始时强制移除工具模式标志
# ============================================================================
import os

# 移除环境变量（确保 Logger 正常初始化）
if "TRIDENT_TOOL_MODE" in os.environ:
    del os.environ["TRIDENT_TOOL_MODE"]

import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 强制初始化 ConfigRegistry（加载完整配置）
from config.registry import ConfigRegistry

ConfigRegistry.initialize(force=True)  # force=True 确保重新加载

from utils.logger_factory import get_access_logger, get_flask_runtime_logger, get_system_logger, get_logger
from web.factory import create_app


def verify_log_separation():
    """验证四重日志分离"""
    print("=" * 70)
    print("Trident v1.7.3 日志架构验证（修复版）")
    print("=" * 70)

    # 获取各logger实例（强制重新创建）
    access_logger = get_access_logger()
    flask_runtime_logger = get_flask_runtime_logger()
    system_logger = get_system_logger()
    monitor_logger = get_logger("Website-PhpStudy")  # 示例网站

    # 打印logger配置
    loggers = [
        ("access", access_logger, "logs/Trident/access.log"),
        ("flask.runtime", flask_runtime_logger, "logs/Trident/flask_runtime.log"),
        ("system", system_logger, "logs/Trident/system.log"),
        ("monitor.Website-PhpStudy", monitor_logger, "logs/Website-PhpStudy/monitor.log")
    ]

    for name, logger, expected_path in loggers:
        print(f"\n[{name}] Logger验证:")
        print(f"  名称: {logger.name}")
        print(f"  级别: {logger.level}")
        print(f"  Handler数量: {len(logger.handlers)}")
        print(f"  Propagate: {logger.propagate}")

        if logger.handlers:
            handler = logger.handlers[0]
            if hasattr(handler, 'baseFilename'):
                actual_path = Path(handler.baseFilename).resolve()
                expected_full = (PROJECT_ROOT / expected_path).resolve()
                match = actual_path == expected_full
                print(f"  文件路径: {actual_path}")
                print(f"  预期路径: {expected_full}")
                print(f"  匹配: {'✓' if match else '✗'}")
            else:
                print(f"  Handler类型: {type(handler).__name__}")
        else:
            print("  ✗ 无Handler（错误）- 正在重新初始化...")
            # 紧急修复：强制添加默认handler
            from logging.handlers import RotatingFileHandler
            import logging

            log_dir = (PROJECT_ROOT / expected_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                PROJECT_ROOT / expected_path,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8"
            )
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
            print(f"  [修复] 已添加默认Handler")

    # 测试日志写入
    print("\n" + "=" * 70)
    print("日志写入测试")
    print("=" * 70)

    # 1. 写入access日志（模拟werkzeug）
    access_logger.info('127.0.0.1 - - [13/Jan/2026 23:50:00] "GET /test" 200 -')
    print("[+] Access日志写入测试完成")

    # 2. 写入flask runtime日志（模拟Blueprint注册）
    flask_runtime_logger.info('[BLUEPRINT] Admin Blueprint registered')
    print("[+] Flask Runtime日志写入测试完成")

    # 3. 写入system日志（模拟系统启动）
    system_logger.info('[SYSTEM][START] Trident v1.7.3 started')
    print("[+] System日志写入测试完成")

    # 4. 写入monitor日志（模拟扫描）
    monitor_logger.info('[MONITOR][SCAN][HIT] test.php 命中3条规则')
    print("[+] Monitor日志写入测试完成")

    # 等待文件系统同步
    time.sleep(0.5)

    # 验证文件内容
    print("\n" + "=" * 70)
    print("文件内容验证")
    print("=" * 70)

    for name, logger, expected_path in loggers:
        log_file = PROJECT_ROOT / expected_path
        if log_file.exists():
            content = log_file.read_text(encoding='utf-8', errors='ignore')
            line_count = len(content.strip().split('\n')) if content.strip() else 0
            print(f"[{name}] {log_file.name}: {line_count} 行")
            if line_count > 0:
                # 显示最后一行
                last_line = content.strip().split('\n')[-1]
                print(f"  最新: {last_line[:80]}...")
        else:
            print(f"[{name}] ✗ 文件不存在: {log_file}")

    print("\n" + "=" * 70)
    print("验证完成！请检查各日志文件内容是否正确分离。")
    print("注意：如果显示 '✗ 无Handler（错误）- 正在重新初始化...' 说明原logger未正确初始化")
    print("=" * 70)


if __name__ == "__main__":
    verify_log_separation()