"""Trident 版本管理器 - 单一真实来源 (Single Source of Truth)
v1.7.7: 从 config.toml [system] 读取版本号，运行时全局可用
"""
import os
import sys

_TRIDENT_VERSION = None
_TRIDENT_RELEASE_DATE = None

def _load_version():
    """启动时从 config.toml 加载版本信息"""
    global _TRIDENT_VERSION, _TRIDENT_RELEASE_DATE
    if _TRIDENT_VERSION is not None:
        return

    try:
        # 兼容 Python 3.11+ 的 tomllib 和旧版本的 tomli
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib

        # 查找 config.toml（从项目根目录）
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, 'config.toml')

        with open(config_path, 'rb') as f:
            cfg = tomllib.load(f)

        system = cfg.get('system', {})
        _TRIDENT_VERSION = system.get('version', 'unknown')
        _TRIDENT_RELEASE_DATE = system.get('release_date', 'unknown')

    except Exception as e:
        # 降级处理：如果读取失败，使用硬编码默认值
        _TRIDENT_VERSION = '1.7.8'
        _TRIDENT_RELEASE_DATE = '2026-05-27'
        print(f"[VERSION] Warning: Failed to load from config.toml: {e}", file=sys.stderr)

def get_version():
    """获取当前 Trident 版本号"""
    _load_version()
    return _TRIDENT_VERSION

def get_release_date():
    """获取当前版本发布日期"""
    _load_version()
    return _TRIDENT_RELEASE_DATE

# 启动时立即加载（模块导入时）
_load_version()

# 向后兼容的常量导出
TRIDENT_VERSION = _TRIDENT_VERSION
TRIDENT_RELEASE_DATE = _TRIDENT_RELEASE_DATE
