# -*- coding: utf-8 -*-
"""
@Time: 1/14/2026 2:15 PM
@Auth: SxyLao1
@File: verify_wildcard_support.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.4验证工具：通配符 `**/access.log` 完整递归支持验证
"""
import os
import sys
from pathlib import Path
import tempfile
import time

# 移除工具模式标志，加载真实配置
if "TRIDENT_TOOL_MODE" in os.environ:
    del os.environ["TRIDENT_TOOL_MODE"]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.registry import ConfigRegistry
from core.log_analyzer import LogAnalyzer
from core.models import Website, ScanOptions
from utils.logger_factory import get_logger, log_with_symbol


def setup_test_environment():
    """创建测试环境"""
    print("=" * 70)
    print("Trident v1.7.4 通配符 **/access.log 验证工具")
    print("=" * 70)

    # 创建临时测试目录结构（转换为绝对路径）
    test_base = (PROJECT_ROOT / "temp" / "wildcard_test").resolve()  # FIX: 绝对路径
    if test_base.exists():
        import shutil
        shutil.rmtree(test_base, ignore_errors=True)

    # 模拟复杂目录结构
    (test_base / "nginx" / "sites-available").mkdir(parents=True, exist_ok=True)
    (test_base / "apache2" / "sites-enabled" / "vhost1").mkdir(parents=True, exist_ok=True)
    (test_base / "phpstudy" / "Extensions" / "Nginx1.25.2" / "logs").mkdir(parents=True, exist_ok=True)

    # 创建多个access.log文件（不同修改时间）
    log1 = test_base / "nginx" / "access.log"
    log1.write_text("192.168.1.1 - - [14/Jan/2026:10:00:00 +0800] \"GET /test1.php HTTP/1.1\" 200 512\n")

    time.sleep(0.1)

    log2 = test_base / "apache2" / "sites-enabled" / "vhost1" / "access.log"
    log2.write_text("192.168.1.2 - - [14/Jan/2026:10:00:01 +0800] \"GET /test2.php HTTP/1.1\" 200 256\n")

    time.sleep(0.1)

    log3 = test_base / "phpstudy" / "Extensions" / "Nginx1.25.2" / "logs" / "access.log"
    log3.write_text("192.168.1.3 - - [14/Jan/2026:10:00:02 +0800] \"GET /shell.php HTTP/1.1\" 200 128\n")

    return test_base, [log1, log2, log3]


def test_wildcard_recursive():
    """测试 **/access.log 递归匹配"""
    print("\n[测试1] **/access.log 递归匹配")
    print("-" * 50)

    test_dir, created_logs = setup_test_environment()

    # 测试不同通配符模式
    test_patterns = [
        f"{test_dir}/**/access.log",
        f"{test_dir}/nginx/**/access.log",
        f"{test_dir}/**/sites-*/**/access.log"
    ]

    for pattern in test_patterns:
        print(f"\n测试模式: {pattern}")

        # 创建模拟配置
        website = Website(
            name="wildcard_test",
            path=test_dir,
            port=80,
            enabled=True,
            scan_options=ScanOptions(
                access_log_path=pattern
            )
        )

        analyzer = LogAnalyzer(website, get_logger("test_wildcard"))

        # 验证解析结果
        resolved_path = analyzer.log_path

        if resolved_path:
            # FIX: 使用绝对路径的relative_to
            print(f"  ✓ 解析成功: {resolved_path.relative_to(test_dir)}")
            print(f"  ✓ 文件存在: {resolved_path.exists()}")

            # 验证是否选择了最新文件
            all_matches = sorted(
                test_dir.glob("**/access.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if all_matches and resolved_path == all_matches[0]:
                print(f"  ✓ 正确选择最新文件")
            else:
                print(f"  ✗ 未选择最新文件")
        else:
            print(f"  ✗ 解析失败")


def test_wildcard_single_level():
    """测试单级通配符 * 匹配"""
    print("\n[测试2] */access.log 单级匹配")
    print("-" * 50)

    test_dir, _ = setup_test_environment()

    # 创建单级结构
    single_level = test_dir / "single_level"
    single_level.mkdir(exist_ok=True)
    (single_level / "access.log").write_text("test\n")

    pattern = f"{single_level}/*/access.log"  # 应该不匹配

    website = Website(
        name="single_level_test",
        path=test_dir,
        port=80,
        enabled=True,
        scan_options=ScanOptions(
            access_log_path=pattern
        )
    )

    analyzer = LogAnalyzer(website, get_logger("test_wildcard"))
    resolved_path = analyzer.log_path

    if resolved_path is None:
        print(f"  ✓ 正确识别无匹配: {pattern}")
    else:
        print(f"  ✗ 不应匹配到路径: {resolved_path}")


def test_fixed_path():
    """测试固定路径"""
    print("\n[测试3] 固定路径加载")
    print("-" * 50)

    test_dir, created_logs = setup_test_environment()
    fixed_log = created_logs[0]

    website = Website(
        name="fixed_path_test",
        path=test_dir,
        port=80,
        enabled=True,
        scan_options=ScanOptions(
            access_log_path=str(fixed_log)
        )
    )

    analyzer = LogAnalyzer(website, get_logger("test_wildcard"))
    resolved_path = analyzer.log_path

    if resolved_path and resolved_path == fixed_log:
        print(f"  ✓ 固定路径加载正确: {resolved_path.relative_to(test_dir)}")
    else:
        print(f"  ✗ 固定路径加载失败: {resolved_path}")


def test_no_match():
    """测试无匹配场景"""
    print("\n[测试4] 无匹配路径处理")
    print("-" * 50)

    test_dir, _ = setup_test_environment()

    website = Website(
        name="no_match_test",
        path=test_dir,
        port=80,
        enabled=True,
        scan_options=ScanOptions(
            access_log_path=f"{test_dir}/nonexistent/**/access.log"
        )
    )

    analyzer = LogAnalyzer(website, get_logger("test_wildcard"))
    resolved_path = analyzer.log_path

    if resolved_path is None:
        print(f"  ✓ 正确处理无匹配场景")
    else:
        print(f"  ✗ 无匹配时应返回None: {resolved_path}")


def test_log_analysis_with_wildcard():
    """测试通配符路径下的日志分析"""
    print("\n[测试5] 通配符路径日志分析")
    print("-" * 50)

    test_dir, created_logs = setup_test_environment()

    # 使用通配符配置
    website = Website(
        name="analysis_test",
        path=test_dir,
        port=80,
        enabled=True,
        scan_options=ScanOptions(
            access_log_path=f"{test_dir}/**/access.log"
        )
    )

    analyzer = LogAnalyzer(website, get_logger("test_wildcard"))

    # 创建测试Webshell
    shell_file = test_dir / "shell.php"
    shell_file.write_text("<?php eval($_POST['cmd']); ?>")

    # 执行分析
    result = analyzer.analyze_shell_access(shell_file)

    if result and len(result.get("suspicious_ips", {})) > 0:
        print(f"  ✓ 通配符路径下日志分析成功")
        print(f"  ✓ 发现 {len(result['suspicious_ips'])} 个可疑IP")
        for ip, count in result["suspicious_ips"].items():
            print(f"    - {ip}: {count}次")
    else:
        print(f"  ✗ 日志分析失败或未找到匹配")


def main():
    """主验证流程"""
    ConfigRegistry.initialize()

    try:
        test_wildcard_recursive()
        test_wildcard_single_level()
        test_fixed_path()
        test_no_match()
        test_log_analysis_with_wildcard()

        print("\n" + "=" * 70)
        print("[+] 所有通配符验证测试完成")
        print("=" * 70)

        # 清理测试环境
        test_dir = PROJECT_ROOT / "temp" / "wildcard_test"
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
            print("[*] 测试环境已清理")

    except Exception as e:
        print(f"\n[✗] 验证失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()