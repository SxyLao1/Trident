# -*- coding: utf-8 -*-
"""
Trident v1.9.0: 抽象接口层
为 v2.0 显式 EDA + Clean Architecture 预埋接口契约。

所有新增功能应实现对应接口，通过 PluginManager 注册，
而非硬编码调用。现有功能保持向后兼容。
"""

from core.interfaces.plugin import Plugin, DomainEvent
from core.interfaces.detector import Detector, ScanRequest, ScanResult
from core.interfaces.repository import Repository
from core.interfaces.notifier import Notifier, AlertMessage
from core.interfaces.event_source import EventSource

__all__ = [
    "Plugin", "DomainEvent",
    "Detector", "ScanRequest", "ScanResult",
    "Repository",
    "Notifier", "AlertMessage",
    "EventSource",
]
