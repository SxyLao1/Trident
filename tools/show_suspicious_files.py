# -*- coding: utf-8 -*-
"""
@Time: 1/6/2026 5:01 PM
@Auth: SxyLao1
@File: show_suspicious_files.py
@IDE: PyCharm
@Motto: HACK THE REAL
显示可疑文件清单
"""
import sys
from pathlib import Path
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')

from utils.project_init import init_project_path
PROJECT_ROOT = init_project_path()

TOOLS_DIR = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)

from core.suspicious_registry import get_all
import json
from utils.path_utils import normalize_path


def show_suspicious_files():
    """显示可疑文件清单"""
    print("=" * 80)
    print("可疑文件清单诊断")
    print("=" * 80)

    try:
        records = get_all(include_deleted=True)
        print(f"[DIAG] 记录总数: {len(records)}")

        if not records:
            print("\n[×] 未发现任何记录")

            # 检查JSON文件
            json_path = normalize_path("data/suspicious_registry.json")
            print(f"\n[DIAG] JSON文件路径: {json_path}")
            print(f"[DIAG] 文件存在: {json_path.exists()}")

            if json_path.exists():
                print(f"[DIAG] 文件大小: {json_path.stat().st_size} bytes")
                try:
                    content = json_path.read_text(encoding='utf-8')
                    print(f"[DIAG] 内容长度: {len(content)}")
                    data = json.loads(content)
                    print(f"[DIAG] 解析成功: {len(data)} 条")
                    print(f"[DIAG] 第一条: {data[0] if data else 'N/A'}")
                except Exception as e:
                    print(f"[DIAG] 解析失败: {e}")
            return

        print(f"\n[√] 发现 {len(records)} 个文件:")
        for i, r in enumerate(records, 1):
            file_path = normalize_path(r["file_path"])
            status = "[✗] 已删除" if not r["file_exists"] else "[✓] 活跃"
            alerted = "[!] 已告警" if r["alerted"] else "[-] 未告警"

            print(f"\n{i}. {status} | {alerted}")
            print(f"   路径: {file_path.name}")
            print(f"   通信数: {r.get('communication_count', 0)} 次")
            print(f"   特征: {r['features']}")

    except Exception as e:
        import traceback
        print(f"[×] 获取清单失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    show_suspicious_files()
