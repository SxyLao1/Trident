"""Anteumbra version manager — reads from config.toml [system]"""
import os
import sys

_ANTEUMBRA_VERSION = None
_ANTEUMBRA_RELEASE_DATE = None


def _find_config():
    """Find config.toml. Try: cwd, then project root, then relative to this file."""
    # When running as installed package, config.toml is in cwd
    cwd_config = os.path.join(os.getcwd(), "config.toml")
    if os.path.exists(cwd_config):
        return cwd_config
    # When running from source, go up to project root (4 levels from this file)
    file_dir = os.path.dirname(os.path.abspath(__file__))
    root_config = os.path.join(file_dir, "..", "..", "..", "..", "config.toml")
    root_config = os.path.normpath(root_config)
    if os.path.exists(root_config):
        return root_config
    return None


def _load_version():
    global _ANTEUMBRA_VERSION, _ANTEUMBRA_RELEASE_DATE
    if _ANTEUMBRA_VERSION is not None:
        return
    try:
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        config_path = _find_config()
        if config_path is None:
            raise FileNotFoundError("config.toml not found")
        with open(config_path, "rb") as f:
            cfg = tomllib.load(f)
        system = cfg.get("system", {})
        _ANTEUMBRA_VERSION = system.get("version", "1.0.1")
        _ANTEUMBRA_RELEASE_DATE = system.get("release_date", "TBD")
    except Exception as e:
        _ANTEUMBRA_VERSION = "unknown"
        _ANTEUMBRA_RELEASE_DATE = "unknown"
        print(f"[VERSION] Warning: {e}", file=sys.stderr)


def get_version():
    _load_version()
    return _ANTEUMBRA_VERSION


def get_release_date():
    _load_version()
    return _ANTEUMBRA_RELEASE_DATE


_load_version()
ANTEUMBRA_VERSION = _ANTEUMBRA_VERSION
ANTEUMBRA_RELEASE_DATE = _ANTEUMBRA_RELEASE_DATE
