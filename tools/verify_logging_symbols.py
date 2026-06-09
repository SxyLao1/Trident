# -*- coding: utf-8 -*-
"""
@Time: 1/13/2026 11:07 PM
@Auth: SxyLao1
@File: verify_logging_symbols.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.4修复版：强制重置ConfigRegistry单例状态
"""
import os
import sys
from pathlib import Path
import time
import logging

# ============================================================================
# 关键修复：强制重置环境，确保ConfigRegistry状态干净
# ============================================================================
# 删除所有可能的干扰标志
for key in list(os.environ.keys()):
    if key.startswith("TRIDENT_"):
        del os.environ[key]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 在导入ConfigRegistry前，强制重置其内部状态
from config.registry import ConfigRegistry

# 核爆级重置：重建锁、清空实例、强制重新初始化
import threading

ConfigRegistry._lock = threading.RLock()
ConfigRegistry._instance = None
ConfigRegistry._initialized = False
ConfigRegistry._config = None
ConfigRegistry._websites = None
ConfigRegistry._init_attempts = 0

# 现在安全初始化
ConfigRegistry.initialize(force=True)

# 之后导入log_with_symbol（确保它看到的是干净的ConfigRegistry）
from utils.logger_factory import log_with_symbol


def verify_logging_symbols():
    """验证符号配置和日志级别过滤"""
    print("=" * 70)
    print("Trident v1.7.4 日志符号与级别验证（修复版）")
    print("=" * 70)

    # ============================================================================
    # 核心修复：直接使用ConfigRegistry._config，绕过可能污染的方法
    # ============================================================================
    try:
        # 验证配置直接访问
        config = ConfigRegistry._config
        if config is None:
            raise RuntimeError("ConfigRegistry._config 为 None")

        logging_cfg = config.get("logging", {})
        level = logging_cfg.get("level", "INFO")
        symbols_cfg = logging_cfg.get("symbols", {})

        print(f"\n[1] config.toml配置级别: {level}")
        print(f"    Python logging对应: {getattr(logging, level.upper())}")
        print(f"\n[2] 符号配置数量: {len(symbols_cfg)}")

        if len(symbols_cfg) == 0:
            raise ValueError("symbols配置为空")

        # 显示前10个符号
        print("    前10个符号:")
        for i, (key, value) in enumerate(list(symbols_cfg.items())[:10], 1):
            print(f"    {i}. {key} = {value}")

    except Exception as e:
        print(f"[CONFIG] ✗ 配置加载失败: {e}", file=sys.stderr)
        return

    # ============================================================================
    # 测试 log_with_symbol 函数（使用真实ConfigRegistry状态）
    # ============================================================================
    print("\n[3] 测试 log_with_symbol 函数:")
    print("-" * 50)

    # 创建临时logger
    logger = logging.getLogger("test_symbols")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.propagate = False

    # 测试用例（从config.toml中选取真实存在的符号）
    test_cases = [
        ("success", "info", "成功事件"),
        ("scan_hit", "critical", "严重告警"),
        ("warning_wal_fail", "warning", "警告事件"),
        ("error_scan_fail", "error", "错误事件"),
    ]

    unknown_count = 0
    for symbol_key, level_name, desc in test_cases:
        log_with_symbol(symbol_key, level_name, f"测试: {desc}", logger)

        # 验证是否回退到UNKNOWN
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            log_with_symbol(symbol_key, level_name, f"验证: {desc}", logger)

        output = f.getvalue()
        if "[UNKNOWN]" in output:
            unknown_count += 1
            print(f"    ✗ {symbol_key} 回退到硬编码", file=sys.stderr)

    print("\n" + "=" * 70)
    if unknown_count == 0:
        print("[√] 所有符号均正确加载，无UNKNOWN回退！")
        print("[√] ConfigRegistry单例状态正常")
    else:
        print(f"[✗] 发现 {unknown_count} 个符号回退到硬编码")
        print("[✗] 需要检查ConfigRegistry初始化时序")
    print("=" * 70)


if __name__ == "__main__":
    verify_logging_symbols()