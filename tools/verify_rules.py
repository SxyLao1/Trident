# -*- coding: utf-8 -*-
"""
@Time: 1/6/2026 2:53 PM
@Auth: SxyLao1
@File: verify_rules.py
@IDE: PyCharm
@Motto: HACK THE REAL
"""

# Ensure project root is in path BEFORE any project imports
import sys
import os
from pathlib import Path
TOOLS_DIR = Path(__file__).parent
PROJECT_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

"""
快速验证YARA规则是否正确加载（增强版）
"""
os.environ["TRIDENT_TOOL_MODE"] = "true"
import logging
from config.registry import ConfigRegistry
from core.yara_engine import get_yara_engine

from pathlib import Path
from config.registry import ConfigRegistry
from core.yara_engine import get_yara_engine



from core.yara_engine import get_yara_engine
import logging

def main():
    ConfigRegistry.initialize()

    logger = logging.getLogger("verify")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

    print("=" * 60)
    print("YARA规则验证工具")
    print("=" * 60)

    engine = get_yara_engine(logger)

    if not hasattr(engine, 'compiled_rules') or engine.compiled_rules is None:
        print("[-] 规则未加载成功")
        return

    # 统计规则
    stats = engine.get_rule_stats()
    total = sum(stats.values())
    print(f"[+] 总计规则数: {total}")
    for lang, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {lang}: {count} 条")

    # ============================================================================
    # 测试样本扫描（使用更严格的测试文件）
    # ============================================================================
    print("\n测试样本扫描:")

    # 使用内存数据而非磁盘文件
    test_content = b'<?php eval($_POST["cmd"]); ?>'
    matches = engine.compiled_rules.match(data=test_content)  # 直接匹配数据

    if matches:
        print(f"[✓] 命中 {len(matches)} 条规则:")
        for m in matches[:3]:
            print(f"  - {m.rule} (high)")
    else:
        print("[✗] 未命中任何规则")
        print("[提示] 检查自定义规则是否包含: eval($_POST")
        # 显示自定义规则内容
        custom_files = list(PROJECT_ROOT.glob("rules/webshell/Custom_*.yar"))
        if custom_files:
            print("\n自定义规则预览:")
            for f in custom_files:
                print(f"\n--- {f.name} ---")
                print(f.read_text(encoding='utf-8')[:200])

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
