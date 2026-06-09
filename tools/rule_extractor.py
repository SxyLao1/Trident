# -*- coding: utf-8 -*-
"""
@Time: 1/6/2026 2:48 PM
@Auth: SxyLao1
@File: rule_extractor.py
@IDE: PyCharm
@Motto: HACK THE REAL
从样本中提取特征生成YARA规则（实时语法验证）
"""
import os
os.environ["TRIDENT_TOOL_MODE"] = "true"
from utils.path_utils import normalize_path
import re
from pathlib import Path
from collections import Counter
import yara  # 引入YARA库验证语法

TOOLS_DIR = Path(__file__).parent
PROJECT_ROOT = TOOLS_DIR.parent
SAMPLES_DIR = PROJECT_ROOT / "temp" / "webshell"
OUTPUT_DIR = PROJECT_ROOT / "rules" / "webshell"


def extract_patterns_from_samples():
    """从样本中提取特征并生成有效YARA规则"""
    if not SAMPLES_DIR.exists():
        print("[-] 错误：temp/webshell/ 不存在")
        print("[-] 错误：请将您要提取的Webshell样本目录移动至temp目录下")
        return

    # ===== 暴力匹配模式（确保能命中样本）=====
    patterns = {
        'php_eval': Counter(),
        'php_system': Counter(),
        'php_exec': Counter(),
        'php_base64': Counter(),
    }

    # PHP模式（匹配所有eval/system/exec调用）
    php_patterns = [
        (r'eval\s*\(', 'php_eval'),  # 匹配所有 eval(
        (r'system\s*\(', 'php_system'),  # 匹配所有 system(
        (r'exec\s*\(', 'php_exec'),  # 匹配所有 exec(
        (r'base64_decode\s*\(.*eval', 'php_base64'),  # 匹配 base64_decode(...eval
    ]

    # ASP模式
    asp_patterns = [
        (r'eval\s*\(\s*request\.form', 'asp_eval'),
        (r'eval\s*\(\s*request\.item', 'asp_eval'),
    ]

    # JSP模式
    jsp_patterns = [
        (r'Runtime\.getRuntime\(\)\.exec', 'jsp_exec'),
        (r'eval\s*\(.*request\.getParameter', 'jsp_eval'),
    ]

    print("[+] 开始扫描样本库...")

    def scan_files(patterns_list, files, counter, label):
        print(f"  [INFO] 扫描 {len(files)} 个 {label} 样本...")
        for i, sample in enumerate(files):
            if i % 100 == 0 and i > 0:
                print(f"  [PROGRESS] 已处理 {i}/{len(files)}")
            try:
                content = sample.read_text(errors='ignore', encoding='utf-8')
                for pattern, category in patterns_list:
                    # 统计匹配次数
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        counter[category][pattern] += len(matches)
            except:
                continue

    # 扫描所有样本
    php_files = list(SAMPLES_DIR.rglob("*.php"))
    asp_files = list(SAMPLES_DIR.rglob("*.asp*"))
    jsp_files = list(SAMPLES_DIR.rglob("*.jsp*"))

    scan_files(php_patterns, php_files, patterns, "PHP")
    scan_files(asp_patterns, asp_files, patterns, "ASP")
    scan_files(jsp_patterns, jsp_files, patterns, "JSP")

    # 生成规则
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_count = 0

    for category, counter in patterns.items():
        if not counter:
            print(f"  [SKIP] {category}: 无匹配模式")
            continue

        # 取前20个最频繁的模式
        frequent_patterns = [p for p, c in counter.most_common(20)]

        rule_name = f"Custom_WebShell_{category.replace('_', ' ').title().replace(' ', '')}"
        rule_path = OUTPUT_DIR / f"{category}.yar"

        # 构建规则
        rule_content = f'''rule {rule_name} {{
  meta:
    description = "Custom rule for {category} (extracted from samples)"
    author = "AutoGenerator"
    date = "{int(normalize_path(__file__).stat().st_mtime)}"
    severity = "high"

  strings:'''

        for i, pat in enumerate(frequent_patterns, 1):
            # 转义特殊字符
            escaped_pat = pat.replace('\\', '\\\\').replace('"', '\\"')
            rule_content += f'\n    ${i} = "{escaped_pat}"'

        rule_content += f"\n\n  condition:\n    any of them\n}}\n"

        # 验证语法
        try:
            yara.compile(source=rule_content)
            rule_path.write_text(rule_content, encoding='utf-8')
            print(f"  [✓] 生成: {rule_path.name} ({len(frequent_patterns)} 条模式)")
            generated_count += 1
        except Exception as e:
            print(f"  [✗] 规则验证失败: {e}")
            # 保存调试版本
            (OUTPUT_DIR / f"{category}_debug.yar").write_text(rule_content, encoding='utf-8')

    print(f"\n[+] 完成！成功生成 {generated_count} 个规则文件")


if __name__ == '__main__':
    extract_patterns_from_samples()
