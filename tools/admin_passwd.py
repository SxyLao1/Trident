# -*- coding: utf-8 -*-
"""
import sys
import os
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


@Time: 1/9/2026 7:53 PM
@Auth: SxyLao1
@File: admin_passwd.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.6: CLI密码管理工具（调用 utils/password_utils）
"""

import sys
import os
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

import os
import sys
from pathlib import Path
from getpass import getpass
from werkzeug.security import generate_password_hash
from config.registry import ConfigRegistry
from utils.path_utils import normalize_path
from utils.project_init import init_project_path

# 设置工具模式（确保ConfigRegistry使用同步保存）
os.environ["TRIDENT_TOOL_MODE"] = "true"

PROJECT_ROOT = init_project_path()

# 导入核心库
from utils.password_utils import check_password_strength, update_password_hash_in_config


def show_banner():
    """显示命令行横幅"""
    print("=" * 60)
    from config.version import get_version
    print(f"Trident WebShell Detector v{get_version()}")
    print("管理员密码管理工具")
    print("=" * 60)


def show_current_config():
    """显示当前配置（脱敏）"""
    try:
        config = ConfigRegistry.get_raw_config()
        web_admin_cfg = config.get("web_admin", {})

        print("\n当前Admin配置:")
        print(f"  启用状态: {web_admin_cfg.get('enabled', False)}")
        print(f"  监听地址: {web_admin_cfg.get('host', '127.0.0.1')}:{web_admin_cfg.get('port', 8080)}")
        print(f"  用户名: {web_admin_cfg.get('username', 'admin')}")

        hash_value = web_admin_cfg.get('password_hash', '')
        if hash_value:
            masked_hash = f"{hash_value[:20]}...{hash_value[-10:]}" if len(hash_value) > 30 else hash_value
            print(f"  密码哈希: {masked_hash}")
        else:
            print("  密码哈希: 未设置")
    except Exception as e:
        print(f"\n[!]  无法读取配置: {e}")


def interactive_password_change():
    """交互式密码修改"""
    show_current_config()

    print("\n" + "-" * 60)
    print("密码强度要求:")
    print("  • 长度8-64位")
    print("  • 禁止使用弱口令（top1000.txt）")
    print("  • 至少包含大写、小写、数字、符号中的三种")
    print("  • 禁止连续重复字符（如aaa）")
    print("  • 禁止键盘序（如qwerty）")
    print("-" * 60)

    # 输入新密码
    while True:
        password = getpass("请输入新密码: ")

        if not password:
            print("[!]  密码不能为空\n")
            continue

        # 调用核心验证
        is_strong, msg = check_password_strength(password)
        print(f"\n{msg}")

        if is_strong:
            # 二次确认
            confirm = getpass("\n请再次输入密码确认: ")

            if password == confirm:
                break
            else:
                print("[!]  两次输入不匹配，请重新输入\n")
        else:
            print("\n" + "=" * 60)
            print("请重新输入符合要求的密码")
            print("=" * 60 + "\n")

    # 生成哈希并更新
    print("\n生成密码哈希...")
    password_hash = generate_password_hash(password)

    print("更新配置文件...")
    success, msg = update_password_hash_in_config(password_hash)

    if success:
        print(f"\n[√] 密码更新成功！")
        print(f"[√] {msg}")
        print(f"\n[+] 提示:")
        print(f"   1. 重启 Trident 服务生效")
        print(f"   2. 新密码已符合生产级安全标准")
        print(f"   3. 原密码立即失效")
    else:
        print(f"\n[×] 更新失败: {msg}")
        sys.exit(1)


def main():
    """主入口"""
    show_banner()

    # 确保config.toml存在
    config_path = normalize_path("config.toml")
    if not config_path.exists():
        print("\n[×] 错误: 配置文件不存在")
        sys.exit(1)

    # 解析命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--show":
            show_current_config()
        elif sys.argv[1] == "--help":
            print("\n用法:")
            print("  python tools/admin_passwd.py        # 交互式修改密码")
            print("  python tools/admin_passwd.py --show # 查看当前配置")
        else:
            print(f"\n[×] 未知参数: {sys.argv[1]}")
            print("用法: admin_passwd.py [--show|--help]")
            sys.exit(1)
    else:
        interactive_password_change()


if __name__ == "__main__":
    main()