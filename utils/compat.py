# -*- coding: utf-8 -*-
"""
@Time: 1/10/2026 8:33 PM
@Auth: SxyLao1
@File: compat.py
@IDE: PyCharm
@Motto: HACK THE REAL
Python 3.8兼容性补丁
"""
def removeprefix(s: str, prefix: str) -> str:
    """Python 3.8兼容的removeprefix"""
    return s[len(prefix):] if s.startswith(prefix) else s

def removesuffix(s: str, suffix: str) -> str:
    """Python 3.8兼容的removesuffix"""
    return s[:-len(suffix)] if s.endswith(suffix) else s