import sys
import os

# Ensure project root is in path when running standalone
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# -*- coding: utf-8 -*-
"""
@Time: 1/16/2026 9:15 PM
@Auth: SxyLao1
@File: strong_passwd.py
@IDE: PyCharm
@Motto: HACK THE REAL
"""
from werkzeug.security import generate_password_hash
import secrets


def generate_strong_passwd():
    """生成高强度密码和哈希"""
    # 生成16位随机密码
    password = secrets.token_urlsafe(16)
    hash_value = generate_password_hash(password, method='scrypt:32768:8:1')

    print(f"密码: {password}")
    print(f"哈希: {hash_value}")
    print("\n请复制哈希到 config.toml 的 password_hash 字段")
    print("密码请妥善保管，仅显示一次！")


if __name__ == "__main__":
    generate_strong_passwd()