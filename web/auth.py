# -*- coding: utf-8 -*-
"""
Trident 公共认证模块
v1.7.9: 从 admin_bp 抽取 require_auth 和 get_admin_credentials，
        供 yara_bp 等蓝图复用，避免循环导入。
"""
from functools import wraps
from flask import request, session, redirect, url_for, make_response
from config.registry import ConfigRegistry


def get_admin_credentials():
    """从配置读取管理员凭证"""
    cfg = ConfigRegistry.get_raw_config().get("web_admin", {})
    username = cfg.get("username", "admin")
    password_hash = cfg.get("password_hash", "")
    allowed_ips = cfg.get("allowed_ips", ["127.0.0.1"])
    return username, password_hash, allowed_ips


def require_auth(f):
    """认证装饰器：检查 IP 白名单 + Session 登录状态"""
    @wraps(f)
    def decorated(*args, **kwargs):
        client_ip = request.remote_addr
        _, _, allowed_ips = get_admin_credentials()
        if client_ip not in allowed_ips:
            response = make_response(f'IP {client_ip} 被拒绝访问', 403)
            return response
        if not session.get('authenticated'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated
