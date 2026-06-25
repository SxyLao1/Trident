#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trident v1.7.9: WebShell 递归扫描器
用途:
    1. 递归扫描目录下所有可疑后缀文件
    2. 调用 YARA 引擎进行批量检测
    3. 支持中文路径、特殊字符文件名
    4. 输出 JSON 报告供 Records 导入

用法:
    python tools/recursive_webshell_scan.py E:\Software\phpstudy_pro\WWW\Test\webshell
    python tools/recursive_webshell_scan.py /var/www/html --output report.json
"""
import sys
import os
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.registry import ConfigRegistry
from core.yara_engine import get_yara_engine
from utils.path_utils import normalize_path
from utils.logger_factory import log_with_symbol

# v1.7.9: 扩展后缀列表（与 config.toml 同步）
WEBSHELL_EXTENSIONS = {
    # PHP 家族
    '.php', '.php3', '.php4', '.php5', '.phtml', '.phar', '.inc', '.hphp',
    # ASP 家族
    '.asp', '.asa', '.cer', '.cdx', '.htr',
    # ASPX 家族
    '.aspx', '.ashx', '.asmx', '.axd',
    # JSP 家族
    '.jsp', '.jspx', '.jsw', '.jsv', '.jspf', '.war',
    # 脚本/其他
    '.sh', '.pl', '.py', '.cgi', '.bak', '.swf',
    # HTML 内嵌
    '.html', '.htm', '.shtml',
    # 无后缀/可疑
    '.txt', '.dat', '.tmp'
}


def collect_files(root_path: Path, extensions: set = None, max_size_mb: int = 5):
    """递归收集目标文件"""
    if extensions is None:
        extensions = WEBSHELL_EXTENSIONS

    files = []
    skipped = 0
    size_limit = max_size_mb * 1024 * 1024

    for item in root_path.rglob('*'):
        if not item.is_file():
            continue

        # 检查后缀
        if item.suffix.lower() not in extensions:
            continue

        # 检查大小
        try:
            if item.stat().st_size > size_limit:
                skipped += 1
                continue
            if item.stat().st_size == 0:
                continue
        except OSError:
            continue

        files.append(item)

    return files, skipped


def scan_file(yara_engine, file_path: Path):
    """扫描单个文件，返回命中结果"""
    try:
        matches = yara_engine.scan(file_path)
        return matches
    except Exception as e:
        print(f"  [ERROR] 扫描失败: {file_path.name} | {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='Trident WebShell 递归扫描器')
    parser.add_argument('path', help='要扫描的根目录')
    parser.add_argument('--output', '-o', default=None, help='输出 JSON 报告路径')
    parser.add_argument('--max-size', type=int, default=5, help='最大文件大小(MB)，默认5')
    parser.add_argument('--import-registry', action='store_true', help='将结果导入 Registry')
    parser.add_argument('--quarantine', action='store_true', help='命中后自动隔离')
    args = parser.parse_args()

    root = normalize_path(args.path)
    if not root.exists():
        print(f"[ERROR] 目录不存在: {root}")
        sys.exit(1)

    print(f"[INFO] Trident v1.7.9 递归扫描器")
    print(f"[INFO] 目标目录: {root}")
    print(f"[INFO] 扫描后缀: {', '.join(sorted(WEBSHELL_EXTENSIONS))}")
    print(f"[INFO] 大小限制: {args.max_size} MB")
    print()

    # 初始化配置
    try:
        ConfigRegistry.initialize()
    except RuntimeError:
        pass

    # 初始化 YARA 引擎
    print("[INFO] 正在加载 YARA 规则...")
    yara_engine = get_yara_engine()
    if yara_engine.compiled_rules is None:
        print("[WARN] YARA 引擎未加载，将只收集文件列表")
    else:
        stats = yara_engine.get_rule_stats()
        print(f"[INFO] YARA 规则加载完成: {stats.get('rule_count', 0)} 条规则")
    print()

    # 收集文件
    print("[STEP 1] 递归收集文件...")
    files, skipped = collect_files(root, max_size_mb=args.max_size)
    print(f"[INFO] 收集到 {len(files)} 个文件，跳过 {skipped} 个超大文件")
    print()

    if not files:
        print("[INFO] 没有文件需要扫描，退出")
        return

    # 扫描
    print("[STEP 2] 开始 YARA 扫描...")
    results = []
    hit_count = 0
    start_time = time.time()

    for i, file_path in enumerate(files, 1):
        # 进度显示
        if i % 100 == 0 or i == len(files):
            print(f"  进度: {i}/{len(files)} ({i*100//len(files)}%) | 命中: {hit_count}", end='')

        matches = scan_file(yara_engine, file_path)

        if matches:
            hit_count += 1
            result = {
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "matches": [
                    {
                        "rule": m.rule_name,
                        "severity": m.severity,
                        "namespace": m.namespace
                    }
                    for m in matches
                ]
            }
            results.append(result)

            # 实时显示命中
            print(f"
  [HIT] {file_path.name}")
            for m in matches:
                print(f"        └─ {m.rule_name} ({m.severity})")

    elapsed = time.time() - start_time
    print(f"
[INFO] 扫描完成: {len(files)} 文件, {hit_count} 命中, 耗时 {elapsed:.1f}s")
    print()

    # 导入 Registry（可选）
    if args.import_registry and results:
        print("[STEP 3] 导入 Registry...")
        from core.suspicious_registry import add
        for r in results:
            add(
                file_path=r["file_path"],
                features=[f"YARA:{m['rule']}({m['severity']})" for m in r["matches"]],
                ip=None
            )
        print(f"[INFO] 已导入 {len(results)} 条记录到 Registry")
        print()

    # 自动隔离（可选）
    if args.quarantine and results:
        print("[STEP 4] 自动隔离命中文件...")
        from core.quarantine import quarantine_file
        for r in results:
            try:
                top_match = r["matches"][0]
                quarantine_file(
                    file_path=r["file_path"],
                    rule_name=top_match["rule"],
                    features=[f"YARA:{m['rule']}" for m in r["matches"]]
                )
                print(f"  [QUARANTINE] {r['file_name']}")
            except Exception as e:
                print(f"  [ERROR] 隔离失败: {r['file_name']} | {e}")
        print()

    # 输出报告
    if args.output:
        report = {
            "scan_time": datetime.now().isoformat(),
            "target_directory": str(root),
            "total_files": len(files),
            "hit_count": hit_count,
            "skipped_large": skipped,
            "elapsed_seconds": round(elapsed, 2),
            "hits": results
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 报告已保存: {args.output}")
    else:
        # 控制台摘要
        print("=" * 60)
        print(f"扫描摘要")
        print("=" * 60)
        print(f"总文件数:    {len(files)}")
        print(f"命中数:      {hit_count}")
        print(f"命中率:      {hit_count/len(files)*100:.1f}%")
        print(f"跳过大文件:  {skipped}")
        print(f"耗时:        {elapsed:.1f}s")
        print(f"平均速度:    {len(files)/elapsed:.0f} 文件/秒")
        print("=" * 60)

        if results:
            print("
命中文件列表:")
            for r in results:
                print(f"  • {r['file_name']}")
                for m in r["matches"]:
                    print(f"    - {m['rule']} [{m['severity']}]")


if __name__ == '__main__':
    main()
