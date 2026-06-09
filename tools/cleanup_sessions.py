# -*- coding: utf-8 -*-
"""
@Time: 1/16/2026 9:15 PM
@Auth: SxyLao1
@File: cleanup_sessions.py
@IDE: PyCharm
@Motto: HACK THE REAL
Session清理工具
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import os

# 设置工具模式
os.environ["TRIDENT_TOOL_MODE"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.registry import ConfigRegistry
from utils.path_utils import normalize_path


def list_sessions(session_dir: Path):
    """
    列出所有Session文件（不判断过期，供前端显示用）
    """
    if not session_dir.exists():
        return []

    sessions = []
    for sess_file in session_dir.glob("*.sess"):
        try:
            stat = sess_file.stat()
            sessions.append({
                'name': sess_file.name,
                'size_kb': round(stat.st_size / 1024, 2),
                'mtime': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'path': sess_file
            })
        except Exception as e:
            print(f"跳过文件 {sess_file}: {e}", file=sys.stderr)
            continue

    return sessions


def cleanup_sessions(days: int = 7) -> int:
    """
    清理N天前的Session文件（保留函数供手动触发）
    """
    try:
        ConfigRegistry.initialize()
    except RuntimeError:
        pass

    config = ConfigRegistry.get_raw_config()
    session_dir = Path(config.get("web_admin", {}).get("session_dir", "data/sessions"))

    if not session_dir.exists():
        print(f"Session目录不存在: {session_dir}")
        return 0

    cutoff_time = datetime.now() - timedelta(days=days)
    deleted = 0

    for sess_file in session_dir.glob("*.sess"):
        try:
            mtime = datetime.fromtimestamp(sess_file.stat().st_mtime)
            if mtime < cutoff_time:
                sess_file.unlink()
                deleted += 1
                print(f"删除过期Session: {sess_file.name} (最后访问: {mtime})")
        except Exception as e:
            print(f"删除失败 {sess_file}: {e}", file=sys.stderr)
            continue

    # 清理Flask-Session缓存文件（tmp*.__wz_cache）
    for cache_file in session_dir.glob("tmp*.__wz_cache"):
        try:
            cache_file.unlink()
            deleted += 1
            print(f"删除缓存文件: {cache_file.name}")
        except:
            pass

    return deleted


def main():
    parser = argparse.ArgumentParser(description='清理过期Session文件')
    parser.add_argument('--days', type=int, default=7, help='清理N天前的Session')
    parser.add_argument('--list-only', action='store_true', help='仅列出Session文件')

    args = parser.parse_args()

    try:
        ConfigRegistry.initialize()
    except RuntimeError:
        pass

    config = ConfigRegistry.get_raw_config()
    session_dir = Path(config.get("web_admin", {}).get("session_dir", "data/sessions"))

    if args.list_only:
        sessions = list_sessions(session_dir)
        if sessions:
            print(f"当前Session文件 ({len(sessions)}个):")
            for sess in sessions:
                print(f"  - {sess['name']} ({sess['size_kb']}KB, 最后访问: {sess['mtime']})")
        else:
            print("暂无Session文件")
    else:
        deleted = cleanup_sessions(days=args.days)
        print(f"\n清理完成: 删除 {deleted} 个过期Session文件")


if __name__ == '__main__':
    main()