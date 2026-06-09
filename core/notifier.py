# -*- coding: utf-8 -*-
"""
@Time: 1/5/2026 5:35 PM
@Auth: SxyLao1
@File: notifier.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.0重构：迁移所有硬编码到config.toml
"""
import logging
import os
import queue
import smtplib
import sys
import threading

import requests
import json
from pathlib import Path
from typing import Dict, Any, Optional
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

from config.registry import ConfigRegistry
from core.metrics import get_metrics
from utils.path_utils import normalize_path

class Notifier:
    """告警通知器：支持邮件、微信、Webhook三渠道"""

    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.enabled = config.get("enabled", False)
        self._wechat_failure_count = 0

        # v1.7.0重构：从配置读取熔断阈值
        self._circuit_threshold = config.get("circuit_breaker_threshold", 10)
        self._wechat_circuit_enabled = True

        # v1.7.0重构：从配置读取队列容量
        queue_config = config.get("queue", {})
        maxsize = queue_config.get("maxsize", 0)  # 0=无限制

        # 测试环境强制限制，生产环境读取配置
        if os.environ.get("TRIDENT_TOOL_MODE") == "true":
            maxsize = 100  # 铁律1：测试环境必须限制

        self._alert_queue = queue.Queue(maxsize=maxsize)
        self._alert_thread = None
        self._overflow_count = 0

        normalize_path("data").mkdir(parents=True, exist_ok=True)

        # 初始化各渠道配置
        self.channels = {
            "email": self._init_email(),
            "wechat": self._init_wechat(),
            "webhook": self._init_webhook()
        }

        # 立即启动工作线程
        if self.enabled:
            self._start_alert_worker()

    def _start_alert_worker(self):
        """启动告警工作线程（仅一次）"""
        if self._alert_thread is not None and self._alert_thread.is_alive():
            return

        def _worker():
            self.logger.info("[ALERT][WORKER] 线程启动")
            while True:
                try:
                    message, level = self._alert_queue.get(timeout=1)
                    if message is None:  # 退出信号
                        break

                    # 处理告警
                    self.logger.info(f"[ALERT][WORKER] 处理: {level}")

                    try:
                        self.send_alert(message, level=level)
                    except Exception as e:
                        self.logger.error(f"[ALERT][WORKER] 发送失败: {e}", exc_info=True)
                except queue.Empty:
                    continue
                except Exception as e:
                    self.logger.critical(f"[ALERT][WORKER] 致命错误: {e}", exc_info=True)
                    break

        self._alert_thread = threading.Thread(target=_worker, daemon=True, name="AlertWorker")
        self._alert_thread.start()
        self.logger.info("[ALERT] 告警工作线程已启动")

    def _safe_notify(self, message: str, level: str = "CRITICAL"):
        """
        异步通知（唯一入口）
        - 正常：写入队列
        - 溢出：立即持久化到磁盘
        - 异常：双保险持久化
        """
        try:
            # 尝试入队（非阻塞）
            self._alert_queue.put_nowait((message, level))
        except queue.Full:
            # 队列满：立即持久化
            self._persist_overflow(message, level)
            self._overflow_count += 1
            # log_with_symbol("error_notifier_queue", "critical", f"告警队列溢出，持久化: {message[:50]}", self.logger)
            self.logger.critical(
                f"[ALERT][OVERFLOW] 队列已满({self._alert_queue.qsize()}), "
                f"已持久化: {message[:50]}..."
            )
        except Exception as e:
            # 任何异常都触发持久化（最后防线）
            self.logger.error(f"[ALERT][QUEUE] 入队失败: {e}", exc_info=True)
            self._persist_overflow(message, level)

    def _persist_overflow(self, message: str, level: str):
        """溢出持久化（内联简化版）"""
        overflow_file = normalize_path("data/alert_overflow.json")
        overflow_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(overflow_file, "a", encoding='utf-8', buffering=1) as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "level": level,
                    "message": message
                }) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"[ALERT][FATAL] 磁盘失败: {e}", file=sys.stderr, flush=True)

    def _init_email(self) -> Dict[str, Any]:
        """初始化SMTP配置"""
        email_cfg = self.config.get("email", {})

        # v1.7.0重构：从配置读取超时
        base_timeout = email_cfg.get("timeout", 10)

        return {
            "enabled": email_cfg.get("enabled", False),
            "smtp_host": email_cfg.get("smtp_host", ""),
            "smtp_port": email_cfg.get("smtp_port", 587),
            "username": email_cfg.get("username", ""),
            "password": email_cfg.get("password", ""),
            "from_addr": email_cfg.get("from_addr", ""),
            "to_addrs": email_cfg.get("to_addrs", []),
            "use_tls": email_cfg.get("use_tls", True),
            "use_ssl": email_cfg.get("use_ssl", False),
            "timeout": base_timeout
        }

    def _init_wechat(self) -> Dict[str, Any]:
        """初始化Server酱配置"""
        wechat_cfg = self.config.get("wechat", {})

        # 从配置读取超时和阈值
        base_timeout = wechat_cfg.get("timeout", 10)

        return {
            "enabled": wechat_cfg.get("enabled", False),
            "send_key": wechat_cfg.get("send_key", ""),
            "timeout": base_timeout,
            "channel": wechat_cfg.get("channel", "9"),
            "noip": wechat_cfg.get("noip", False)
        }

    def _init_webhook(self) -> Dict[str, Any]:
        """初始化Webhook配置"""
        webhook_cfg = self.config.get("webhook", {})
        return {
            "enabled": webhook_cfg.get("enabled", False),
            "url": webhook_cfg.get("url", ""),
            "headers": webhook_cfg.get("headers", {}),
            "timeout": webhook_cfg.get("timeout", 10)
        }

    def send_alert(self, message: str, level: str = "CRITICAL", analysis: Optional[Dict[str, Any]] = None):
        """
        发送告警（主入口）

        Args:
            message: 告警主体消息
            level: 告警级别 INFO/WARNING/CRITICAL
            analysis: 可选的日志分析结果
        """
        if not self.enabled:
            self.logger.debug("[NOTIFIER] 告警功能未启用")
            return

        # 必须在调用发送方法前完成消息增强
        enhanced_message = message
        if analysis:
            suspicious_ips = analysis.get("suspicious_ips", {})
            if suspicious_ips:
                enhanced_message += f"\n\n攻击溯源分析:\n"
                enhanced_message += f"时间窗口: {analysis.get('create_time', '未知')}\n"
                enhanced_message += f"可疑IP访问统计:\n"
                for ip, count in suspicious_ips.items():
                    enhanced_message += f"   {ip}: {count}次\n"
                enhanced_message += f"日志文件: {analysis.get('log_path', '未知')}"

        # 必须传递参数，微信失败不影响邮件
        # 通道1：微信（可能熔断）
        if self.channels["wechat"]["enabled"] and self._wechat_circuit_enabled:
            try:
                self._send_wechat(enhanced_message, level)  # ← 必须传参数
            except Exception as e:
                self.logger.error(f"[NOTIFIER][WECHAT] 调用异常: {e}")  # 确保异常不向上抛

        # 通道2：邮件（高可靠性，永不熔断）
        if self.channels["email"]["enabled"]:
            try:
                self._send_email(enhanced_message, level)  # ← 必须传参数
            except Exception as e:
                self.logger.error(f"[NOTIFIER][EMAIL] 调用异常: {e}")

        # 通道3：Webhook（可选）
        if self.channels["webhook"]["enabled"]:
            try:
                self._send_webhook(enhanced_message, level)
            except Exception as e:
                self.logger.error(f"[NOTIFIER][WEBHOOK] 调用异常: {e}")

        # 日志输出必须在所有通道尝试后，避免重复
        # 提取核心消息（第一行）用于日志，保持日志简洁
        core_message = enhanced_message.split('\n')[0].strip()
        self.logger.critical(f"[NOTIFIER][ALERT][{level}] {core_message}")

    def _send_email(self, message: str, level: str):
        """发送邮件告警"""
        try:
            cfg = self.channels["email"]
            msg = MIMEText(message, "plain", "utf-8")
            msg["Subject"] = Header(f"[WebShell警报-{level}]", "utf-8")
            msg["From"] = cfg["from_addr"]
            msg["To"] = ", ".join(cfg["to_addrs"])

            # 修复：根据端口选择SMTP或SMTP_SSL
            port = cfg["smtp_port"]
            timeout = cfg.get("timeout", 10)

            if cfg.get("use_ssl", False) or port == 465:
                # SSL加密端口（465）
                self.logger.debug(f"[NOTIFIER][EMAIL] 使用SSL连接: {cfg['smtp_host']}:{port}")
                server = smtplib.SMTP_SSL(cfg["smtp_host"], port, timeout=timeout)
            else:
                # TLS加密端口（587/25）
                self.logger.debug(f"[NOTIFIER][EMAIL] 使用TLS连接: {cfg['smtp_host']}:{port}")
                server = smtplib.SMTP(cfg["smtp_host"], port, timeout=timeout)
                if cfg.get("use_tls", True):
                    server.starttls()

            server.login(cfg["username"], cfg["password"])
            server.send_message(msg)
            server.quit()

            self.logger.info(f"[NOTIFIER][EMAIL] 发送成功 -> {cfg['to_addrs']}")

        except Exception as e:
            self.logger.error(f"[NOTIFIER][EMAIL] 发送失败: {e}", exc_info=True)

    def _send_wechat(self, message: str, level: str):
        """发送微信告警（Server酱）- 熔断降级版【必须完整替换】"""

        if not self._wechat_circuit_enabled:
            self.logger.warning("[NOTIFIER][WECHAT] 熔断中，跳过发送")
            return

        try:
            cfg = self.channels["wechat"]
            send_key = cfg["send_key"]
            if not send_key:
                self.logger.warning("[NOTIFIER][WECHAT] SendKey未配置，推送已跳过")
                return

            # VPN/代理环境优化
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            url = f"https://sctapi.ftqq.com/{send_key}.send"
            title = f"[WebShell-{level}]"[:32]

            payload = {
                "title": title,
                "desp": message,
                "channel": cfg["channel"],
                "noip": cfg["noip"]
            }

            session = requests.Session()
            session.verify = False

            if os.environ.get("HTTPS_PROXY"):
                self.logger.debug(f"[NOTIFIER][WECHAT] 检测到系统代理: {os.environ['HTTPS_PROXY']}")

            self.logger.debug(f"[NOTIFIER][WECHAT] 正在发送请求至: {url}")

            # 设置超时和重试
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            retry_strategy = Retry(
                total=3,  # 最多3次重试
                backoff_factor=0.5,  # 间隔0.5秒递增
                status_forcelist=[500, 502, 503, 504]
            )
            session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

            response = session.post(
                url,
                json=payload,
                timeout=cfg["timeout"],
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0:
                pushid = result.get("data", {}).get("pushid")
                self.logger.info(f"[NOTIFIER][WECHAT] 发送成功 (pushid: {pushid})")
            else:
                error_msg = result.get("message", "未知错误")
                raise RuntimeError(f"Server酱API返回错误: {error_msg}")

            # 成功：重置熔断计数
            self._wechat_failure_count = 0
            self.logger.debug("[NOTIFIER][WECHAT] 发送成功")

        # 异常处理：所有路径统一增加熔断计数
        except ValueError as e:
            self._wechat_failure_count += 1
            if "check_hostname requires server_hostname" in str(e):
                self.logger.error("[NOTIFIER][WECHAT] SSL代理配置错误")
            else:
                self.logger.error(f"[NOTIFIER][WECHAT] 参数错误: {e}")

        except requests.exceptions.ProxyError as e:
            self._wechat_failure_count += 1
            self.logger.error(f"[NOTIFIER][WECHAT] 代理连接失败: {e}")

        except requests.exceptions.ConnectionError as e:
            self._wechat_failure_count += 1
            self.logger.error(f"[NOTIFIER][WECHAT] 网络连接失败: {e}")

        except Exception as e:
            self._wechat_failure_count += 1
            self.logger.error(f"[NOTIFIER][WECHAT] 未知错误: {e}")

        # 熔断判断
        finally:
            if self._wechat_failure_count >= self._circuit_threshold:
                self._wechat_circuit_enabled = False
                self.logger.critical("[NOTIFIER][WECHAT] 熔断器触发，降级为仅邮件")

                # 发送熔断通知到邮件
                fallback_msg = f"微信推送熔断已触发！失败次数: {self._wechat_failure_count}"
                try:
                    self._send_email(fallback_msg, "CRITICAL")
                except Exception as mail_e:
                    self.logger.critical(f"[NOTIFIER][FUSE] 邮件通知也失败: {mail_e}")

    def _send_webhook(self, message: str, level: str):
        """发送Webhook告警（钉钉/企微）"""
        try:
            cfg = self.channels["webhook"]

            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"[WebShell-{level}]\n\n{message}"
                }
            }

            headers = {"Content-Type": "application/json"}
            headers.update(cfg["headers"])

            response = requests.post(
                cfg["url"],
                json=payload,
                headers=headers,
                timeout=cfg["timeout"]
            )
            response.raise_for_status()

            self.logger.info(f"[NOTIFIER][WEBHOOK] 发送成功")

        except Exception as e:
            self.logger.error(f"[NOTIFIER][WEBHOOK] 发送失败: {e}", exc_info=True)

    def _stop_alert_worker(self):
        """停止告警工作线程"""
        if self._alert_thread and self._alert_thread.is_alive():
            # 发送退出信号
            try:
                self._alert_queue.put_nowait((None, None))  # None作为退出信号
            except queue.Full:
                pass

            # 等待线程退出（最大5秒）
            self._alert_thread.join(timeout=5.0)

            if self._alert_thread.is_alive():
                self.logger.warning("[NOTIFIER] 工作线程未能正常退出")
            else:
                self.logger.info("[NOTIFIER] 工作线程已停止")

# 全局单例实例
_notifier_instance: Optional[Notifier] = None


def get_notifier(logger: logging.Logger) -> Notifier:
    """获取通知器单例"""
    global _notifier_instance
    if _notifier_instance is None:
        config = ConfigRegistry.get_raw_config().get("notifier", {})
        _notifier_instance = Notifier(config, logger)
    return _notifier_instance

def reset_notifier():
    """重置notifier单例（配置热加载后调用，重置熔断器状态）"""
    global _notifier_instance
    _notifier_instance = None
    logging.getLogger("webshell.notifier").info("[NOTIFIER] 实例已重置（熔断器状态清除）")

    # 清理函数
def shutdown_notifier():
    """全局清理函数（测试用）"""
    global _notifier_instance
    if _notifier_instance:
        _notifier_instance._stop_alert_worker()
        _notifier_instance = None