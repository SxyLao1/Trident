# -*- coding: utf-8 -*-
"""
@Time: 1/6/2026 12:29 AM
@Auth: SxyLao1
@File: config_watcher.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.4增强：配置热加载后自动更新LogAnalyzer.log_path
"""
import time
from pathlib import Path
from typing import Dict, List

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from tools.config_watcher_logger import get_config_watcher_logger
from config.registry import ConfigRegistry
from utils.path_utils import normalize_path
# v1.7.4新增：导入符号化日志接口
from utils.logger_factory import log_with_symbol


class ConfigReloadHandler(FileSystemEventHandler):
    def __init__(self, registry_class, logger):
        self.registry_class = registry_class
        self.logger = logger
        self._last_reload = 0

        # v1.7.0重构：从配置读取延迟时间
        config = ConfigRegistry.get_raw_config()
        timeouts_cfg = config.get("timeouts", {})
        self._reload_delay = timeouts_cfg.get("config_reload_delay", 10)

    def on_modified(self, event):
        src_path = normalize_path(event.src_path)

        if src_path.name == "config.toml" and src_path.parent == normalize_path("."):
            now = time.time()
            if now - self._last_reload > self._reload_delay:
                self._last_reload = now
                log_with_symbol("warning_config_reload", "warning",
                                f"检测到config.toml变更，等待{self._reload_delay}秒...", self.logger)
                time.sleep(self._reload_delay)

                try:
                    start_time = time.time()

                    # 记录变更前的配置摘要
                    old_config = ConfigRegistry.get_raw_config()

                    # 重置并重新加载配置
                    self.registry_class.reset()
                    self.registry_class.initialize(force=True)

                    # 计算变更的键
                    new_config = ConfigRegistry.get_raw_config()
                    changed_keys = self._get_changed_keys(old_config, new_config)

                    # 记录到历史持久化文件
                    duration_ms = (time.time() - start_time) * 1000
                    get_config_watcher_logger().log_reload(
                        new_config, changed_keys, duration_ms
                    )

                    log_with_symbol("success", "info", "配置热加载成功", self.logger)

                except Exception as e:
                    log_with_symbol("error_config_reload", "error", f"配置热加载失败: {e}", self.logger)

        # YARA规则热重载（保持不变）
        elif src_path.suffix in (".yar", ".yara"):
            log_with_symbol("notice", "info", f"规则文件变更: {src_path.name}", self.logger)
            try:
                from core.yara_engine import get_yara_engine
                engine = get_yara_engine(self.logger)
                if hasattr(engine, '_load_rules'):
                    engine._load_rules()
                    log_with_symbol("success", "info", "规则重载成功", self.logger)
            except Exception as e:
                log_with_symbol("error_config_reload", "error", f"规则重载失败: {e}", self.logger)

    def _get_changed_keys(self, old_config: Dict, new_config: Dict) -> List[str]:
        """对比配置，获取变更的键路径"""
        changed = []
        try:
            # 简化对比：只对比顶层键
            old_keys = set(old_config.keys())
            new_keys = set(new_config.keys())

            # 新增的键
            for key in new_keys - old_keys:
                changed.append(f"+{key}")

            # 删除的键
            for key in old_keys - old_keys:
                changed.append(f"-{key}")

            # 修改的键（简单对比）
            for key in old_keys & new_keys:
                if old_config[key] != new_config[key]:
                    changed.append(f"~{key}")

        except Exception as e:
            self.logger.warning(f"[CONFIG] 对比配置变更失败: {e}")
            changed.append("unknown")

        return changed[:10]  # 最多返回10个变更


def start_config_watcher(registry_class, logger):
    """启动监控"""
    handler = ConfigReloadHandler(registry_class, logger)
    observer = Observer()
    observer.schedule(handler, str(normalize_path("config.toml").parent), recursive=False)
    observer.start()
    log_with_symbol("success", "info", "配置热加载监控已启动", logger)
    return observer