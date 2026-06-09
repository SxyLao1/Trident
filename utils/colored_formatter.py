# -*- coding: utf-8 -*-
"""
@Time: 1/5/2026 10:49 PM
@Auth: SxyLao1
@File: colored_formatter.py
@IDE: PyCharm
@Motto: HACK THE REAL
"""
import logging

try:
    from colorama import init, Fore, Style

    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class ColoredFormatter(logging.Formatter):
    """根据日志标记和内容着色"""

    def format(self, record):
        msg = super().format(record)

        if not COLORAMA_AVAILABLE:
            return msg

        red_indicators = [
            "[ALERT]", "[CRITICAL]", "[SUSPICIOUS]", "[PERM]", "[ERROR]",
            "WEBSHELL被访问告警",
            "=" * 50,  # 分隔线
            "文件路径:", "攻击IP:", "访问时间:", "原生日志:",
        ]

        for indicator in red_indicators:
            if indicator in msg:
                return Fore.LIGHTRED_EX + Style.BRIGHT + msg

        # 亮蓝色：监控相关
        if "[LOG_MONITOR]" in msg:
            return Fore.LIGHTBLUE_EX + Style.BRIGHT + msg

        # 黄色：文件系统操作
        if any(tag in msg for tag in
               ["[CREATE]", "[DELETE]", "[MODIFY]", "[MOVE]", "[RENAME]", "[SECURITY]", "[SCRIPT]"]):
            return Fore.YELLOW + msg

        # 青色：配置和系统信息
        if any(tag in msg for tag in ["[CONFIG]", "[INFO]", "[START]", "[STOP]", "[SYSTEM]"]):
            return Fore.CYAN + msg

        # 绿色：安全/跳过
        if any(tag in msg for tag in ["[SAFE]", "[SKIP]", "[OK]", "[RETRY_SUCCESS]"]):
            return Fore.GREEN + msg

        # 默认白色
        return Fore.WHITE + msg
