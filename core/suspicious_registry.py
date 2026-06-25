# -*- coding: utf-8 -*-
"""
@Time: 1/5/2026 9:40 PM
@Auth: SxyLao1
@File: suspicious_registry.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.6修复：remove()函数触发SSE更新
"""
import json
import logging
import threading
import queue
import time
import atexit
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from config.registry import ConfigRegistry

# 强制初始化（解决循环导入和时序问题）
try:
    ConfigRegistry.initialize()
except RuntimeError:
    pass  # 已初始化则忽略
from utils.path_utils import path_to_key, normalize_path
# v1.7.3：导入统一日志接口
from utils.logger_factory import log_with_symbol
from core import wal_manager

# ============================================================================
# FIX v1.7.3: 工具脚本模式检测（静默运行）
# ============================================================================
def _is_tool_script() -> bool:
    """检测是否为工具脚本运行模式（测试环境也视为工具模式）"""
    return os.environ.get("TRIDENT_TOOL_MODE", "false") == "true"
# ============================================================================

_logger_instance = None

# ============================================================================
# v1.7.0重构：从配置读取所有路径和阈值
# ============================================================================
def _get_registry_paths():
    """获取Registry相关路径（增强版：确保返回有效Path对象）"""
    try:
        config = ConfigRegistry.get_raw_config()
        paths = config.get("paths", {})
        data_dir_str = paths.get("data_dir", "data")

        # 确保字符串不为None
        if data_dir_str is None:
            raise ValueError("data_dir配置为None")

        data_dir = normalize_path(data_dir_str)

        # 确保创建目录（防止后续操作失败）
        data_dir.mkdir(parents=True, exist_ok=True)

    except Exception as e:
        # 所有异常都使用硬编码默认值
        logger = logging.getLogger("monitor.suspicious_registry")
        logger.error(f"[REGISTRY] 配置加载失败: {e}，使用默认值 'data/'")
        data_dir = normalize_path("data")
        data_dir.mkdir(parents=True, exist_ok=True)

    # 确保返回的每个Path都有效（不为None）
    registry_path = data_dir / "suspicious_registry.json"
    backup_path = data_dir / "suspicious_registry.json.bak"

    # 终极检查：如果任一路径为None，抛出错误
    if any(p is None for p in [registry_path, backup_path]):
        raise RuntimeError(f"[REGISTRY] 路径初始化失败: registry={registry_path}")

    return {
        "registry": registry_path,
        "backup": backup_path
    }

# 延迟初始化路径（避免模块导入时ConfigRegistry未初始化）
_REGISTRY_PATH = None
_REGISTRY_BACKUP_PATH = None

# ============================================================================
# v1.7.0重构：补充缺失的异步保存全局变量
# ============================================================================
# 全局异步保存队列和线程（必须保留这些全局变量）
_async_save_queue: Optional[queue.Queue] = None
_async_save_thread: Optional[threading.Thread] = None
_async_save_enabled = False
_async_save_interval = 60
_async_running = False
_async_lock = threading.Lock()
_last_registry_snapshot: Optional[List[Dict]] = None  # 数据快照

_save_lock = threading.Lock()  # 文件写入锁

_registry_update_timer = None  # 防抖定时器
_registry_update_lock = threading.Lock()
_REGISTRY_UPDATE_DEBOUNCE_SECONDS = 2.0  # 防抖延迟（可调整）

def _ensure_initialized():
    """v1.7.0新增：确保所有必要组件已初始化（公共函数入口调用）"""
    global _REGISTRY_PATH, _REGISTRY_BACKUP_PATH, _async_save_enabled

    # v1.7.3重构：统一处理工具脚本模式（包含测试和工具脚本）
    if _is_tool_script():
        # 工具模式：完全禁用异步保存
        _async_save_enabled = False

        # 如果是测试环境，使用测试专用路径
        if os.environ.get("PYTEST_CURRENT_TEST") or "test" in sys.argv[0].lower():
            if _REGISTRY_PATH is None:
                test_dir = normalize_path("temp/registry_test_isolated/data")
                test_dir.mkdir(parents=True, exist_ok=True)
                _REGISTRY_PATH = test_dir / "test_registry.json"
                _REGISTRY_BACKUP_PATH = _REGISTRY_PATH.with_suffix('.json.bak')

    _init_paths()
    _enable_async_save()

def _init_paths():
    """初始化路径（第一次使用时）"""
    global _REGISTRY_PATH, _REGISTRY_BACKUP_PATH
    if _REGISTRY_PATH is None:
        paths = _get_registry_paths()
        _REGISTRY_PATH = paths["registry"]
        _REGISTRY_BACKUP_PATH = paths["backup"]


def _get_logger():
    """获取或创建带时间戳的logger（使用monitor命名空间）"""
    global _logger_instance
    if _logger_instance is None:
        # v1.7.3修复：使用monitor命名空间，确保日志写入monitor.log
        _logger_instance = logging.getLogger("monitor.suspicious_registry")
    return _logger_instance


def _enable_async_save():
    """从配置启用异步保存"""
    global _async_save_enabled, _async_save_interval, _async_save_queue, _async_save_thread, _async_running

    if _is_tool_script():
        _async_save_enabled = False
        return

    # 如果已经初始化，跳过
    if _async_save_queue is not None:
        return

    try:
        config = ConfigRegistry.get_raw_config()
        registry_cfg = config.get("registry", {})

        _async_save_enabled = registry_cfg.get("async_save_enabled", False)
        # v1.7.0重构：从配置读取间隔时间
        _async_save_interval = registry_cfg.get("async_save_interval_seconds", 60)

        if _async_save_enabled:
            log_with_symbol("notice", "info", f"启用异步保存，间隔: {_async_save_interval}秒")

            _async_save_queue = queue.Queue(maxsize=0)
            _async_running = True
            _async_save_thread = threading.Thread(
                target=_async_save_worker,
                name="RegistryAsyncSaver",
                daemon=True
            )
            _async_save_thread.start()

            atexit.register(_shutdown_async_saver)

    except Exception as e:
        log_with_symbol("warning", "warning", f"配置加载失败，使用同步模式: {e}")
        _async_save_enabled = False



def _add_record_direct(registry_data: List[Dict], file_path: Path, features: List[str]):
    """直接操作registry数据（不经过WAL，用于重放）"""
    abs_path = path_to_key(file_path)

    for item in registry_data:
        if item["file_path"] == abs_path:
            item.update({
                "file_exists": True,
                "deleted_at": None,
                "alerted": False,
                "communication_count": 0,
                "first_seen_ip": None,
                "detected_at": datetime.now().isoformat(),
                "features": features,
                # v1.7.2新增：误报标记字段
                "marked_false_positive": False,
                "false_positive_reason": "",
                "false_positive_at": None
            })
            return  # 找到即更新

    # 不存在则添加
    registry_data.append({
        "file_path": abs_path,
        "detected_at": datetime.now().isoformat(),
        "features": features,
        "alerted": False,
        "file_exists": True,
        "first_seen_ip": None,
        "communication_count": 0,
        "deleted_at": None,
        # v1.7.2新增：误报标记字段
        "marked_false_positive": False,
        "false_positive_reason": "",
        "false_positive_at": None
    })

def replay_wal_manually():
    """手动触发WAL重放（测试或灾难恢复时调用）- v1.8.4: 使用 wal_manager"""

    entries = wal_manager.read_entries()
    if not entries:
        print("WAL文件不存在或为空")
        return 0

    logger = logging.getLogger("monitor.suspicious_registry.wal")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('[%(asctime)s] [REGISTRY][WAL] %(message)s'))
        logger.addHandler(handler)

    logger.info("发现事务日志，正在重放...")

    recovered = 0
    registry = _load_registry()

    for entry in entries:
        try:
            operation = entry["operation"]
            file_path = normalize_path(entry["file_path"])
            features = entry.get("features", [])
            ip = entry.get("ip")

            if operation == "ADD":
                _add_record_direct(registry, file_path, features)
                recovered += 1
            elif operation == "INCREMENT" and ip:
                _increment_access_direct(registry, file_path, ip)
                recovered += 1
            elif operation == "REMOVE":
                _remove_record_direct(registry, file_path)
                recovered += 1
            elif operation == "ALERTED":
                _mark_alerted_direct(registry, file_path)
                recovered += 1
            else:
                logger.warning(f"未知操作: {operation}")
        except Exception as e:
            logger.error(f"重放行失败: {e}", exc_info=True)

    _save_registry_sync(registry)
    logger.info(f"重放完成，恢复 {recovered} 条记录")

    # 归档 WAL
    wal_manager.archive_current_wal()
    return recovered

def _increment_access_direct(registry_data: List[Dict], file_path: Path, ip: str):
    """直接递增访问计数（用于WAL重放）"""
    abs_path = path_to_key(file_path)
    for item in registry_data:
        if item["file_path"] == abs_path:
            item["communication_count"] = item.get("communication_count", 0) + 1
            if not item.get("first_seen_ip"):
                item["first_seen_ip"] = ip
            return

def _remove_record_direct(registry_data: List[Dict], file_path: Path):
    """直接标记删除（用于WAL重放）"""
    abs_path = path_to_key(file_path)
    for item in registry_data:
        if item["file_path"] == abs_path:
            item["file_exists"] = False
            item["deleted_at"] = datetime.now().isoformat()

def _mark_alerted_direct(registry_data: List[Dict], file_path: Path):
    """直接标记已告警（用于WAL重放）"""
    abs_path = path_to_key(file_path)
    for item in registry_data:
        if item["file_path"] == abs_path:
            item["alerted"] = True

def _shutdown_async_saver():
    """优雅关闭异步保存器"""
    global _async_running, _async_save_thread, _async_save_queue

    if _is_tool_script():
        return

    try:
        logger = _get_logger()
    except:
        logger = logging.getLogger("monitor.suspicious_registry")

    log_with_symbol("notice", "info", "正在关闭异步保存器...", logger)

    with _async_lock:
        _async_running = False

        if _async_save_queue:
            try:
                _async_save_queue.put(None)
            except:
                pass

        if _async_save_thread and _async_save_thread.is_alive():
            _async_save_thread.join(timeout=5.0)

        if _async_save_thread and _async_save_thread.is_alive():
            logger.warning("[REGISTRY][ASYNC] 线程未能在5秒内关闭")

    log_with_symbol("notice", "info", "异步保存器已关闭", logger)

def _async_save_worker():
    """后台保存工作线程"""
    global _async_running

    try:
        logger = _get_logger()
    except:
        logger = logging.getLogger("monitor.suspicious_registry")

    log_with_symbol("notice", "info", "工作线程已启动", logger)

    while _async_running:
        try:
            try:
                registry_data = _async_save_queue.get(timeout=_async_save_interval)
            except queue.Empty:
                if _last_registry_snapshot:
                    _save_registry_sync(_last_registry_snapshot)
                continue

            if registry_data is None:
                break  # 退出信号

            _save_registry_sync(registry_data)
            log_with_symbol("notice", "debug", f"保存 {len(registry_data)} 条记录", logger)

        except Exception as e:
            log_with_symbol("error_async", "error", f"工作线程错误: {e}", logger)

    log_with_symbol("notice", "info", "工作线程已退出", logger)

def _queue_async_save(registry_data: List[Dict]):
    """将序列化后的registry数据加入队列"""
    global _async_save_queue

    if not _async_save_queue:
        return

    try:
        _async_save_queue.put(registry_data)
    except queue.Full:
        logger = _get_logger()
        logger.error("[REGISTRY][ASYNC] 队列已满，保存操作丢失！")

def _flush_sync():
    """同步刷新内存数据到磁盘（立即执行）"""
    try:
        data = _load_registry()
        _save_registry_sync(data)
        _get_logger().debug("[REGISTRY][ASYNC] 同步刷新完成")
    except Exception as e:
        _get_logger().error(f"[REGISTRY][ASYNC] 同步刷新失败: {e}", exc_info=True)


def _load_registry() -> List[Dict]:
    """加载注册表（确保路径已初始化）"""
    _init_paths()

    if _REGISTRY_PATH and _REGISTRY_PATH.exists():
        try:
            content = _REGISTRY_PATH.read_text(encoding='utf-8')
            if content.strip():
                data = json.loads(content)
                logger = logging.getLogger("monitor.suspicious_registry")
                logger.debug(f"[REGISTRY] 加载主文件成功: {len(data)} 条记录")
                return data
        except (json.JSONDecodeError, OSError) as e:
            _logger_warning(f"[REGISTRY] 主文件损坏或无法读取: {e}")

    if _REGISTRY_BACKUP_PATH and _REGISTRY_BACKUP_PATH.exists():
        try:
            content = _REGISTRY_BACKUP_PATH.read_text(encoding='utf-8')
            if content.strip():
                data = json.loads(content)
                try:
                    _REGISTRY_PATH.write_text(json.dumps(data, indent=2), encoding='utf-8')
                    _logger_info("[REGISTRY] 已从备份恢复主文件")
                except:
                    _logger_warning("[REGISTRY] 无法恢复主文件，继续使用备份")
                return data
        except (json.JSONDecodeError, OSError):
            _logger_warning("[REGISTRY] 备份文件也损坏")

    return []


def _save_registry_sync(data: List[Dict]):
    """同步保存注册表（Windows终极版：关闭所有句柄后替换）"""
    global _save_lock

    with _save_lock:
        try:
            _init_paths()
            # 获取路径（确保已初始化）
            registry_path = _REGISTRY_PATH
            backup_path = _REGISTRY_BACKUP_PATH

            if not registry_path:
                raise RuntimeError("REGISTRY_PATH未初始化")

            # 确保目录存在
            registry_path.parent.mkdir(parents=True, exist_ok=True)

            # 序列化数据
            json_content = json.dumps(data, indent=2, ensure_ascii=False)

            # Windows特殊处理：先关闭所有可能打开的句柄
            if sys.platform == "win32":
                # 重置全局快照（释放内存引用）
                global _last_registry_snapshot
                _last_registry_snapshot = None

                # 强制垃圾回收（关闭文件句柄）
                import gc
                gc.collect()
                time.sleep(0.1)  # 给操作系统释放时间

            # 原子写入策略 - 保持原有逻辑但优化Windows处理
            temp_path = registry_path.with_suffix('.tmp')

            # 写入临时文件（确保关闭）
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
                f.flush()
                if sys.platform != "win32":
                    os.fsync(f.fileno())

            # 关闭文件句柄后，在Windows上增加额外等待确保句柄完全释放
            if sys.platform == "win32":
                time.sleep(0.05)  # 额外等待50ms确保句柄释放

            # 执行原子替换
            if sys.platform == "win32":
                # Windows：尝试重命名，如果失败则直接写入
                try:
                    # 如果目标文件存在，先删除
                    if registry_path.exists():
                        registry_path.unlink()
                    temp_path.rename(registry_path)
                except (PermissionError, OSError):
                    # 文件被占用，回退到直接写入
                    registry_path.write_text(json_content, encoding='utf-8')
                    if temp_path.exists():
                        temp_path.unlink()
            else:
                # Linux：原子替换
                temp_path.replace(registry_path)

            # 更新备份
            backup_path.write_text(json_content, encoding='utf-8')

            _get_logger().debug(f"[REGISTRY][SAVE] 保存 {len(data)} 条记录")

        except PermissionError:
            logger.warning(f"Registry file permission denied: {registry_path}, using in-memory mode")
            return
        except Exception as e:
            logger = logging.getLogger("monitor.suspicious_registry")
            logger.error(f"[REGISTRY][SAVE] 失败: {e}", exc_info=True)

            # 最后手段：写入紧急备份
            try:
                fallback_path = registry_path.parent / "registry_emergency_backup.json"
                fallback_path.write_text(json.dumps(data, indent=2), encoding='utf-8')
                logger.critical(f"[REGISTRY][FALLBACK] 已写入紧急备份: {fallback_path}")
            except:
                pass

def _save_registry(data: List[Dict]):
    """保存注册表（根据配置自动选择同步或异步）"""
    global _last_registry_snapshot

    _last_registry_snapshot = data

    if _async_save_enabled:
        _queue_async_save(data)
    else:
        _save_registry_sync(data)




def add(file_path: Path, features: List[str]):
    """添加可疑文件（线程安全版）"""
    _ensure_initialized()

    try:
        with _async_lock:
            global _last_registry_snapshot

            # FIX: 强制使用path_to_key确保路径格式一致
            abs_path = path_to_key(file_path)

            # 加载当前数据
            if _last_registry_snapshot is not None:
                registry = _last_registry_snapshot.copy()
            else:
                registry = _load_registry()

            # 查找或更新记录
            updated = False
            for item in registry:
                if item["file_path"] == abs_path:
                    # 更新现有记录
                    item.update({
                        "file_exists": True,
                        "deleted_at": None,
                        "alerted": False,
                        "communication_count": 0,
                        "first_seen_ip": None,
                        "detected_at": datetime.now().isoformat(),
                        "features": features
                    })
                    updated = True
                    break

            if not updated:
                # 添加新记录
                registry.append({
                    "file_path": abs_path,  # FIX: 使用path_to_key生成的键
                    "detected_at": datetime.now().isoformat(),
                    "features": features,
                    "alerted": False,
                    "file_exists": True,
                    "first_seen_ip": None,
                    "communication_count": 0,
                    "deleted_at": None
                })

            _last_registry_snapshot = registry
            _save_registry(registry)

            try:
                trigger_registry_update_debounced()
                _get_logger().debug("[REGISTRY] SSE防抖推送已触发")
            except Exception as e:
                _get_logger().warning(f"[REGISTRY] SSE推送失败: {e}")

            log_with_symbol("registry_add", "info", f"{file_path.name} | 特征: {', '.join(features[:3])}")

    except Exception as e:
        log_with_symbol("error_registry_add", "error", f"异常: {e}")

def get_all(include_deleted: bool = False, include_false_positive: bool = False) -> List[Dict]:
    """
    v1.7.7: 默认不显示已删除文件，保持清单整洁
    include_deleted: 审计视图专用参数
    """
    _ensure_initialized()

    registry = _load_registry()

    # 第一层过滤：删除状态（默认False）
    if include_deleted:
        base_filtered = registry  # 审计视图：显示所有
    else:
        base_filtered = [item for item in registry if item.get("file_exists", True)]

    # 第二层过滤：误报标记
    if include_false_positive:
        filtered = base_filtered
    else:
        filtered = [item for item in base_filtered if not item.get("marked_false_positive", False)]

    filtered.sort(key=lambda x: x.get("detected_at", ""), reverse=True)
    return filtered

def mark_alerted(file_path: Path):
    """标记已告警"""
    _ensure_initialized()  # 确保初始化

    try:
        registry = _load_registry()
        abs_path = path_to_key(file_path)

        for item in registry:
            if item["file_path"] == abs_path:
                item["alerted"] = True
                _save_registry(registry)
                log_with_symbol("notice", "debug", f"标记已告警: {file_path.name}")
                break
    except Exception as e:
        log_with_symbol("error_mark_alerted", "error", f"异常: {e}")

def increment_access(file_path: Path, ip: str):
    """增加访问计数 - v1.7.7-Patch11: 使用防抖SSE推送"""
    _ensure_initialized()

    try:
        registry = _load_registry()
        abs_path = path_to_key(file_path)

        # 查找记录
        for item in registry:
            if item["file_path"] == abs_path:
                old = item.get("communication_count", 0)
                new_count = old + 1
                item["communication_count"] = new_count
                if item.get("first_seen_ip") is None:
                    item["first_seen_ip"] = ip

                # v1.7.7-Patch11: 记录日志（每次都有），但SSE推送防抖
                log_with_symbol(
                    "notice",
                    "info",
                    f"{file_path.name} 通信次数: {old} → {new_count} | IP: {ip}",
                    _get_logger()
                )
                break
        else:
            # 记录不存在：直接创建
            registry.append({
                "file_path": abs_path,
                "detected_at": datetime.now().isoformat(),
                "features": ["AUTO_CREATED_BY_ACCESS"],
                "alerted": False,
                "file_exists": True,
                "first_seen_ip": ip,
                "communication_count": 1,
                "deleted_at": None
            })
            log_with_symbol("warning", "warning", f"记录不存在，自动创建: {file_path.name}", _get_logger())

        # 保存更改
        _save_registry(registry)

        # v1.7.7-Patch11: 使用防抖推送（关键修复）
        # - 高频访问时，只会每2秒推送一次
        # - 最后一次更新后2秒，前端最终状态一定正确
        trigger_registry_update_debounced()

    except Exception as e:
        log_with_symbol("error_increment", "error", f"异常: {e}", _get_logger())

def remove(file_path: Union[Path, str]) -> bool:
    """
    v1.7.6-Patch1: 软删除（标记file_exists=False），不是物理删除
    与误报标记区分：此操作由文件删除事件触发
    """
    _ensure_initialized()
    logger = logging.getLogger("monitor.suspicious_registry")

    # 区分输入类型
    if isinstance(file_path, str):
        abs_path = file_path  # 来自前端的已标准化键
    elif isinstance(file_path, Path):
        abs_path = path_to_key(file_path)  # 来自监控事件的Path
    else:
        log_with_symbol("error", "error", f"无效路径类型: {type(file_path)}", logger)
        return False

    try:
        registry = _load_registry()
        found = False

        for item in registry:
            if item["file_path"] == abs_path:
                # v1.7.6-Patch1: 软删除（标记file_exists=False）
                item["file_exists"] = False
                item["deleted_at"] = datetime.now().isoformat()
                found = True
                logger.info(f"[REGISTRY][MARK_DELETED] 标记删除: {abs_path}")
                break

        if not found:
            log_with_symbol("notice", "info", f"记录不存在: {abs_path[:50]}...", logger)
            return False

        # 保存更改
        _save_registry_sync(registry)
        _flush_sync()

        log_with_symbol("registry_remove", "info", f"标记删除成功: {abs_path}", logger)

        # 触发SSE更新
        try:
            trigger_registry_update_debounced()
            logger.debug("[REGISTRY] SSE防抖推送已触发")
        except Exception as e:
            logger.warning(f"[REGISTRY] SSE推送失败: {e}")

        return True

    except Exception as e:
        log_with_symbol("error_registry_remove", "error", f"删除异常: {e}", logger)
        return False

def _trigger_registry_update_event():
    """触发Registry更新事件（通过日志触发SSE）"""
    logger = logging.getLogger("monitor.webshell.registry")
    log_with_symbol("notice", "info", "Registry已更新，触发前端刷新", logger)
    # 同时写入一个标记文件，让SSE检测到变化
    try:
        marker = normalize_path("data/registry_update.marker")
        marker.write_text(str(time.time()))
    except:
        pass

def get(path: Path) -> Optional[Dict]:
    """获取单条记录"""
    _ensure_initialized()  # 确保初始化

    try:
        abs_path = str(path.resolve())
        for item in get_all(include_deleted=True):
            if item["file_path"] == abs_path:
                return item
    except Exception as e:
        log_with_symbol("error", "error", f"异常: {e}")
    return None


def is_suspicious(path: Path) -> bool:
    """检查是否在清单中"""
    return get(path) is not None

def compact_registry():
    """压缩注册表"""
    _ensure_initialized()
    try:
        _init_paths()

        config = ConfigRegistry.get_raw_config()
        filesizes_cfg = config.get("filesizes", {})
        compact_days = filesizes_cfg.get("registry_compact_days", 30)

        data = _load_registry()
        original_count = len(data)

        cutoff = datetime.now() - timedelta(days=compact_days)
        compacted = [
            r for r in data
            if r["file_exists"] or datetime.fromisoformat(r["detected_at"]) > cutoff
        ]

        cleaned_count = original_count - len(compacted)

        # 增强日志反馈
        if cleaned_count > 0:
            _save_registry(compacted)
            log_with_symbol("notice", "info", f"清理 {cleaned_count} 条过期记录")
        else:
            # 新增：明确告知用户无记录可清理
            log_with_symbol("notice", "info",
                            f"扫描 {original_count} 条记录，无过期记录需要清理（阈值: {compact_days}天）")

        return {
            "total": original_count,
            "cleaned": cleaned_count,
            "remaining": len(compacted)
        }
    except Exception as e:
        log_with_symbol("error", "error", f"Registry压缩失败: {e}")
        return {"error": str(e)}

def _auto_compact_worker():
    """自动压缩工作线程"""
    time.sleep(3600)
    while _async_running:
        compact_registry()
        time.sleep(86400)

def trigger_registry_update_debounced():
    """
    v1.7.7-Patch11: 防抖版Registry更新触发器
    - 最后一次更新后2秒才会真正推送
    - 避免高频访问时SSE过载
    """
    global _registry_update_timer, _registry_update_lock

    with _registry_update_lock:
        # 如果已有待触发的定时器，取消它（重置倒计时）
        if _registry_update_timer is not None:
            _registry_update_timer.cancel()

        # 创建新的定时器
        _registry_update_timer = threading.Timer(
            _REGISTRY_UPDATE_DEBOUNCE_SECONDS,
            _do_trigger_registry_update
        )
        _registry_update_timer.daemon = True
        _registry_update_timer.start()


def _do_trigger_registry_update():
    """实际执行Registry更新推送"""
    global _registry_update_timer, _registry_update_lock

    try:
        # 调用sse_manager中的原始函数
        from utils.sse_manager import trigger_registry_update
        trigger_registry_update()
        _get_logger().debug("[REGISTRY][SSE] 防抖推送已执行")
    except Exception as e:
        _get_logger().warning(f"[REGISTRY][SSE] 推送失败: {e}")
    finally:
        with _registry_update_lock:
            _registry_update_timer = None


def _clear_memory_cache():
    """v1.7.6-Patch18: 清空内存缓存，强制下次从磁盘加载"""
    global _last_registry_snapshot
    logger = logging.getLogger("monitor.suspicious_registry")

    with _async_lock:
        if _last_registry_snapshot is not None:
            old_count = len(_last_registry_snapshot)
            _last_registry_snapshot = None
            logger.info(f"[REGISTRY] 内存缓存已清空（原记录数: {old_count}）")
        else:
            logger.debug("[REGISTRY] 内存缓存已为空")

# 优雅关闭注册
atexit.register(_shutdown_async_saver)


def _force_init_at_import():
    """在模块导入时强制初始化（修复None问题）- v1.7.6-Patch2"""
    global _REGISTRY_PATH, _REGISTRY_BACKUP_PATH

    # 如果已经初始化且不为None，跳过
    if _REGISTRY_PATH is not None:
        return

    logger = logging.getLogger("monitor.suspicious_registry")
    logger.debug("[REGISTRY] 强制初始化开始...")

    # ============================================
    # 核心修复：处理 ConfigRegistry 未就绪的情况
    # ============================================
    try:
        # 尝试从配置读取
        from config.registry import ConfigRegistry

        # 确保ConfigRegistry已初始化（带重试）
        for attempt in range(3):
            try:
                if not ConfigRegistry._initialized:
                    ConfigRegistry.initialize()
                config = ConfigRegistry.get_raw_config()
                paths = config.get("paths", {})
                data_dir = normalize_path(paths.get("data_dir", "data"))
                break
            except Exception as e:
                logger.warning(f"[REGISTRY] 配置读取尝试{attempt + 1}/3失败: {e}")
                if attempt == 2:
                    raise
                time.sleep(0.1)
    except Exception as e:
        # 配置未就绪，使用硬编码默认值（避免None）
        logger.warning(
            f"[REGISTRY] 配置初始化失败: {e}，使用硬编码默认值"
        )
        data_dir = normalize_path("data")

    # 确保目录存在
    data_dir.mkdir(parents=True, exist_ok=True)

    # 设置全局路径（确保不是None）
    _REGISTRY_PATH = data_dir / "suspicious_registry.json"
    _REGISTRY_BACKUP_PATH = _REGISTRY_PATH.with_suffix('.json.bak')

    # ============================================
    # 核心修复：验证路径对象创建成功
    # ============================================
    if _REGISTRY_PATH is None:
        logger.critical("[REGISTRY] 致命错误: _REGISTRY_PATH 初始化失败为 None")
        raise RuntimeError("_REGISTRY_PATH 初始化失败")

    logger.debug(
        f"[REGISTRY] 初始化完成:"
        f"\n  - Registry: {_REGISTRY_PATH}"
        f"\n  - Backup: {_REGISTRY_BACKUP_PATH}"
    )

# 模块导入时立即执行
_force_init_at_import()


# 辅助函数：避免在函数内重复写logger
def _logger_debug(msg: str):
    logging.getLogger("monitor.suspicious_registry").debug(msg)

def _logger_info(msg: str):
    logging.getLogger("monitor.suspicious_registry").info(msg)

def _logger_warning(msg: str):
    logging.getLogger("monitor.suspicious_registry").warning(msg)

def _logger_error(msg: str):
    logging.getLogger("monitor.suspicious_registry").error(msg)