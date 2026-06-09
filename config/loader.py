# -*- coding: utf-8 -*-
"""
@Time: 1/3/2026 8:48 PM
@Auth: SxyLao1
@File: loader.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.3-Final-Patch5：移除配置同步，由ConfigRegistry统一管理
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any


def load_toml_config(config_path: str = "config.toml") -> Dict[str, Any]:
    """
    加载TOML配置文件（简化版）

    设计原则：
    1. 仅负责加载和解析TOML文件
    2. 不进行任何配置同步操作
    3. 所有配置状态管理由ConfigRegistry统一负责
    """
    # 计算绝对路径
    config_file = Path(config_path).resolve()

    if not config_file.exists():
        project_root = Path(__file__).resolve().parent.parent
        config_file = project_root / "config.toml"

        if not config_file.exists():
            raise FileNotFoundError(
                f"[CONFIG FATAL] 配置文件不存在:\n"
                f"  尝试路径1: {Path(config_path).resolve()}\n"
                f"  尝试路径2: {config_file}\n"
                f"  当前工作目录: {Path.cwd()}"
            )

    try:
        # 读取并解析配置
        if sys.version_info >= (3, 11):
            import tomllib
            with open(config_file, "rb") as f:
                config = tomllib.load(f)
        else:
            import tomli
            with open(config_file, "rb") as f:
                config = tomli.load(f)

        if not config:
            raise ValueError("TOML解析返回空配置")

        return config

    except Exception as e:
        print(f"\n{'=' * 60}", file=sys.stderr)
        print(f"[CONFIG FATAL] TOML解析失败: {config_file}", file=sys.stderr)
        print(f"错误类型: {type(e).__name__}", file=sys.stderr)
        print(f"错误信息: {str(e)}", file=sys.stderr)
        print(f"{'=' * 60}\n", file=sys.stderr)
        raise

# API 兼容别名 (v1.7.8 CI/CD 测试兼容)
load_config = load_toml_config
