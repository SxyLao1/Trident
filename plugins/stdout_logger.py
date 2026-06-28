# -*- coding: utf-8 -*-
"""
v1.9.3: Stdout Logger Plugin — POC 内置插件

实现 Plugin + Notifier 接口。
将所有告警事件以彩色格式输出到终端。
"""
import json
import logging
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any

from core.interfaces.plugin import Plugin, DomainEvent
from core.interfaces.notifier import Notifier, AlertMessage, AlertLevel

logger = logging.getLogger(__name__)

# 终端颜色
_COLORS = {
    AlertLevel.CRITICAL: "\033[1;31m",  # 红色加粗
    AlertLevel.HIGH:     "\033[0;31m",  # 红色
    AlertLevel.MEDIUM:   "\033[0;33m",  # 黄色
    AlertLevel.LOW:      "\033[0;36m",  # 青色
    AlertLevel.INFO:     "\033[0;37m",  # 白色
    "reset":             "\033[0m",
}


class StdoutLoggerPlugin(Plugin, Notifier):
    """终端输出插件 — 将告警彩色输出到 stdout"""

    @property
    def name(self) -> str:
        return "stdout_logger"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_events(self) -> List[str]:
        return ["alert.sent", "scan.completed", "block.executed", "quarantine.action"]

    def activate(self, config: Dict[str, Any]) -> None:
        self._color = config.get("color", True)
        self._verbose = config.get("verbose", False)
        logger.info("StdoutLogger: 已激活 (color=%s, verbose=%s)", self._color, self._verbose)

    def deactivate(self) -> None:
        logger.info("StdoutLogger: 已停用")

    def on_event(self, event: DomainEvent) -> Optional[List[DomainEvent]]:
        if self._verbose:
            ts = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
            payload_str = json.dumps(event.payload, ensure_ascii=False, default=str)[:200]
            print(f"[PLUGIN][{ts}] {event.event_type} ← {event.source}: {payload_str}")
        return None

    def send(self, message: AlertMessage) -> bool:
        color = _COLORS.get(message.level, "")
        reset = _COLORS["reset"] if self._color else ""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{color}[ALERT][{ts}] {message.level.value.upper():8s} {message.title}{reset}"
        # 确保输出到 stdout（非 stderr），避免与日志混淆
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        return True
