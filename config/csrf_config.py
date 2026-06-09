# -*- coding: utf-8 -*-
"""
@Time: 1/12/2026 2:53 PM
@Auth: SxyLao1
@File: csrf_config.py
@IDE: PyCharm
@Motto: HACK THE REAL
"""
import secrets
from pathlib import Path
from config.registry import ConfigRegistry
from utils.path_utils import normalize_path


def generate_csrf_secret() -> str:
    """生成CSRF密钥并保存"""
    secret_file = normalize_path("data/csrf_secret.key")

    if secret_file.exists():
        return secret_file.read_text(encoding='utf-8').strip()

    secret = secrets.token_urlsafe(32)
    secret_file.write_text(secret, encoding='utf-8')
    return secret


# 供Flask-WTF使用
WTF_CSRF_SECRET_KEY = generate_csrf_secret()
WTF_CSRF_TIME_LIMIT = 3600  # 1小时有效期