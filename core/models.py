# -*- coding: utf-8 -*-
"""
@Time: 1/5/2026 1:26 PM
@Auth: SxyLao1
@File: models.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.4增强：ScanOptions支持access_log_path配置
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from utils.path_utils import normalize_path


@dataclass
class ScanOptions:
    """扫描策略配置"""
    monitor_extensions: List[str] = field(default_factory=lambda: [".php"])
    exclude_dirs: List[str] = field(default_factory=list)
    exclude_files: List[str] = field(default_factory=list)
    max_file_size: str = "10MB"
    debug_mode: bool = False
    # v1.7.4新增：access_log_path支持（用于通配符配置）
    access_log_path: Optional[str] = None  # 新增字段

    @property
    def max_size_bytes(self) -> int:
        """将文件大小字符串转换为字节"""
        size_str = self.max_file_size.upper()
        multipliers = {'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        for unit, multiplier in multipliers.items():
            if size_str.endswith(unit):
                return int(size_str.replace(unit, '')) * multiplier
        return int(size_str)

@dataclass
class ScanResult:
    """扫描结果对象"""
    file_path: Path
    is_suspicious: bool
    features: List[str]
    score: float = 0.0
    engine: str = "static"
    error: Optional[str] = None
    analysis_data: Optional[dict] = None

@dataclass
class Website:
    """网站配置对象"""
    name: str
    path: Path
    port: int
    enabled: bool = False
    scan_options: ScanOptions = field(default_factory=ScanOptions)

    def __post_init__(self):
        """对象创建后的自动验证"""
        # 确保path是Path对象
        if isinstance(self.path, str):
            self.path = normalize_path(self.path)
        # 端口范围验证
        if not (1 <= self.port <= 65535):
            raise ValueError(f"端口 {self.port} 超出范围(1-65535)")

    def is_reachable(self) -> bool:
        """检查端口是否可达"""
        from core.scanner import check_port
        return check_port("127.0.0.1", self.port)

    def __str__(self):
        """用于友好打印"""
        return f"Website(name='{self.name}', path={self.path}, port={self.port}, enabled={self.enabled})"
