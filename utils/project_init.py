# -*- coding: utf-8 -*-
"""
@Time: 1/11/2026 5:44 PM
@Auth: SxyLao1
@File: project_init.py
@IDE: PyCharm
@Motto: HACK THE REAL
"""
import sys
from pathlib import Path

def init_project_path() -> Path:
    """统一初始化项目路径和配置"""
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    from config.registry import ConfigRegistry
    try:
        ConfigRegistry.initialize()
    except RuntimeError:
        pass
    return PROJECT_ROOT