# -*- coding: utf-8 -*-
"""
v1.8.2: IP 封禁模块 — 多设备广播架构

设计参考：afoa0521 生产环境自动封禁工具
模式：单次 Block 请求 → 广播到所有已配置的安全设备

设备类型：
    - stdout: 仅日志输出（开发/测试）
    - http: 通用 HTTP POST 到防火墙/WAF API
    - mock: 内存黑名单（Mock 测试用）

配置 (config.toml):
    [ip_blocker]
    enabled = true
    auto_block_enabled = false   # 是否自动封禁（高危画像自动触发）
    auto_block_min_score = 0.8   # 自动封禁最低风险分

    [[ip_blocker.devices]]
    name = "Mock Firewall"
    type = "mock"

    [[ip_blocker.devices]]
    name = "Production WAF"
    type = "http"
    url = "https://waf.company.com/api/block"
    api_key = "${TRIDENT_WAF_API_KEY:-}"
"""

import json, logging, threading, time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from config.registry import ConfigRegistry

logger = logging.getLogger("monitor.ip_blocker")


# ═══════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════

@dataclass
class BlockDecision:
    """封禁决策"""
    ip: str
    reason: str
    profile_id: str = ""
    risk_score: float = 0.0
    duration_seconds: int = 86400  # 默认24小时
    permanent: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BlockResult:
    """封禁结果（每个设备返回一个）"""
    device_name: str
    success: bool
    message: str
    ip: str
    timestamp: datetime = field(default_factory=datetime.now)


# ═══════════════════════════════════════════════════════════════
# Device Interface
# ═══════════════════════════════════════════════════════════════

class BlockDevice(ABC):
    """安全设备抽象接口——WAF / FW / NGFW 都实现这个"""

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def block(self, decision: BlockDecision) -> BlockResult:
        """执行封禁"""
        pass

    @abstractmethod
    def unblock(self, ip: str) -> BlockResult:
        """解除封禁"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """设备是否在线"""
        pass


# ═══════════════════════════════════════════════════════════════
# Device Implementations
# ═══════════════════════════════════════════════════════════════

class StdoutDevice(BlockDevice):
    """仅日志输出——开发/演示用"""
    def __init__(self, name="stdout"):
        self.name = name
    def get_name(self): return self.name
    def is_available(self): return True
    def block(self, decision):
        logger.info(f"[BLOCK][{self.name}] Would block {decision.ip} | reason={decision.reason} | profile={decision.profile_id[:8]}")
        print(f"  [IP_BLOCKER] {self.name}: BLOCK {decision.ip} — {decision.reason}")
        return BlockResult(device_name=self.name, success=True, message="logged", ip=decision.ip)
    def unblock(self, ip):
        logger.info(f"[BLOCK][{self.name}] Would unblock {ip}")
        return BlockResult(device_name=self.name, success=True, message="logged", ip=ip)


class MockDevice(BlockDevice):
    """内存黑名单——Mock 测试用"""
    def __init__(self, name="mock"):
        self.name = name
        self._blocklist: set = set()
    def get_name(self): return self.name
    def is_available(self): return True
    def block(self, decision):
        self._blocklist.add(decision.ip)
        logger.info(f"[BLOCK][{self.name}] Blocked {decision.ip}")
        return BlockResult(device_name=self.name, success=True, message="blocked (mock)", ip=decision.ip)
    def unblock(self, ip):
        self._blocklist.discard(ip)
        return BlockResult(device_name=self.name, success=True, message="unblocked (mock)", ip=ip)
    def is_blocked(self, ip): return ip in self._blocklist
    def list_all(self): return sorted(self._blocklist)


class HTTPDevice(BlockDevice):
    """通用 HTTP POST 设备——对接 WAF/FW REST API"""
    def __init__(self, name, url, api_key=""):
        self.name = name
        self.url = url
        self.api_key = api_key

    def get_name(self): return self.name

    def is_available(self):
        try:
            import requests
            r = requests.get(self.url.rsplit('/', 1)[0] + '/ping', timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def block(self, decision):
        import requests
        try:
            payload = {
                "ip": decision.ip,
                "comment": f"Trident: {decision.reason} (profile: {decision.profile_id[:8]})",
                "permanent": decision.permanent,
                "duration": decision.duration_seconds,
                "risk_score": decision.risk_score,
            }
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            r = requests.post(self.url, json=payload, headers=headers, timeout=10)
            ok = r.status_code < 400
            return BlockResult(device_name=self.name, success=ok,
                message=r.text[:200] if not ok else "blocked", ip=decision.ip)
        except Exception as e:
            return BlockResult(device_name=self.name, success=False, message=str(e), ip=decision.ip)

    def unblock(self, ip):
        import requests
        try:
            url = self.url.replace('/block', '/unblock')
            r = requests.post(url, json={"ip": ip}, timeout=10)
            return BlockResult(device_name=self.name, success=r.status_code < 400,
                message="unblocked" if r.status_code < 400 else r.text[:200], ip=ip)
        except Exception as e:
            return BlockResult(device_name=self.name, success=False, message=str(e), ip=ip)


# ═══════════════════════════════════════════════════════════════
# IP Blocker Manager
# ═══════════════════════════════════════════════════════════════

class IPBlocker:
    """IP 封禁管理器——广播到所有设备"""

    def __init__(self):
        self.devices: List[BlockDevice] = []
        self._auto_block_enabled = False
        self._auto_block_min_score = 0.8
        self._history: List[BlockResult] = []
        self._lock = threading.Lock()

    def add_device(self, device: BlockDevice):
        self.devices.append(device)

    def configure(self, config: dict):
        """从 config.toml [ip_blocker] 加载配置"""
        self._auto_block_enabled = config.get("auto_block_enabled", False)
        self._auto_block_min_score = config.get("auto_block_min_score", 0.8)

        # Load devices from config
        devices_cfg = config.get("devices", [])
        for dcfg in devices_cfg:
            dtype = dcfg.get("type", "stdout")
            name = dcfg.get("name", dtype)
            if dtype == "mock":
                self.add_device(MockDevice(name))
            elif dtype == "http":
                url = dcfg.get("url", "")
                key = dcfg.get("api_key", "")
                if url:
                    self.add_device(HTTPDevice(name, url, key))
            elif dtype == "stdout":
                self.add_device(StdoutDevice(name))

        # Default: always add stdout device for logging
        if not self.devices:
            self.add_device(StdoutDevice())

    def block(self, ips: List[str], reason: str = "", profile_id: str = "",
              risk_score: float = 0.0, permanent: bool = False) -> List[BlockResult]:
        """封禁 IP 列表，广播到所有设备"""
        results = []
        with self._lock:
            for ip in ips:
                decision = BlockDecision(
                    ip=ip, reason=reason, profile_id=profile_id,
                    risk_score=risk_score, permanent=permanent)
                for device in self.devices:
                    try:
                        r = device.block(decision)
                        results.append(r)
                        self._history.append(r)
                    except Exception as e:
                        logger.warning(f"[BLOCK] {device.get_name()} failed: {e}")
                        results.append(BlockResult(
                            device_name=device.get_name(), success=False,
                            message=str(e), ip=ip))
        return results

    def unblock(self, ips: List[str]) -> List[BlockResult]:
        """解封 IP 列表"""
        results = []
        with self._lock:
            for ip in ips:
                for device in self.devices:
                    try:
                        r = device.unblock(ip)
                        results.append(r)
                    except Exception as e:
                        results.append(BlockResult(
                            device_name=device.get_name(), success=False,
                            message=str(e), ip=ip))
        return results

    def auto_block(self, profile_id: str, ips: List[str], risk_score: float, reason: str = ""):
        """自动封禁：仅当 auto_block_enabled 且分数达标时触发"""
        if not self._auto_block_enabled:
            return []
        if risk_score < self._auto_block_min_score:
            return []
        logger.info(f"[AUTO_BLOCK] Profile {profile_id[:8]}: {len(ips)} IPs, score={risk_score}")
        return self.block(ips, reason=reason, profile_id=profile_id, risk_score=risk_score)

    def get_blocklist(self) -> List[Dict]:
        """返回当前黑名单（仅 mock 设备）"""
        result = []
        for device in self.devices:
            if isinstance(device, MockDevice):
                for ip in device.list_all():
                    result.append({"ip": ip, "source": device.get_name()})
        return result

    def get_history(self, limit: int = 50) -> List[Dict]:
        """返回封禁历史"""
        return [{
            "device": r.device_name, "ip": r.ip, "success": r.success,
            "message": r.message, "time": r.timestamp.isoformat()
        } for r in self._history[-limit:]]


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_blocker: Optional[IPBlocker] = None


def get_ip_blocker() -> IPBlocker:
    global _blocker
    if _blocker is None:
        _blocker = IPBlocker()
        try:
            cfg = ConfigRegistry.get_raw_config().get("ip_blocker", {})
            if cfg.get("enabled", False):
                _blocker.configure(cfg)
                logger.info(f"[IP_BLOCKER] Initialized with {len(_blocker.devices)} device(s)")
        except Exception as e:
            logger.warning(f"[IP_BLOCKER] Config load failed: {e}")
            _blocker.add_device(StdoutDevice())
    return _blocker
