# -*- coding: utf-8 -*-
"""
@Time: 1/11/2026 9:49 PM
@Auth: SxyLao1
@File: factory.py
@IDE: PyCharm
@Motto: HACK THE REAL
Flask应用工厂：v1.7.3分离access.log与monitor.log
"""
import logging
import secrets
from datetime import timedelta

from flask import Flask
from typing import Optional
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from config.registry import ConfigRegistry
from utils.path_utils import normalize_path
from flask_wtf.csrf import generate_csrf

# 全局应用实例
_app_instance: Optional[Flask] = None


def create_app() -> Flask:
    """创建Flask应用实例"""
    global _app_instance

    if _app_instance is not None:
        return _app_instance

    # 先静默werkzeug横幅
    from utils.logger_factory import silence_werkzeug
    silence_werkzeug()

    # 创建主应用
    app = Flask(__name__)

    # v1.7.7: 注入版本号到所有模板全局上下文（0硬编码设计哲学）
    from config.version import get_version, get_release_date
    @app.context_processor
    def inject_version():
        return {
            'trident_version': get_version(),
            'trident_release_date': get_release_date()
        }
    app.config['SECRET_KEY'] = secrets.token_urlsafe(32)  # 改为随机生成
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # === 新增Session配置 ===
    app.config['SESSION_TYPE'] = ConfigRegistry.get_raw_config().get("web_admin", {}).get("session_type", "filesystem")
    app.config['SESSION_FILE_DIR'] = normalize_path(
        ConfigRegistry.get_raw_config().get("web_admin", {}).get("session_dir", "data/sessions")
    )
    app.config['SESSION_PERMANENT'] = ConfigRegistry.get_raw_config().get("web_admin", {}).get("session_permanent",
                                                                                               False)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
        seconds=ConfigRegistry.get_raw_config().get("web_admin", {}).get("session_lifetime", 3600)
    )

    # 初始化Session
    Session(app)

    # v1.7.3关键修复：获取access logger并挂载到werkzeug
    from utils.logger_factory import get_access_logger, get_flask_runtime_logger
    access_logger = get_access_logger()
    flask_runtime_logger = get_flask_runtime_logger()

    # 配置werkzeug logger将访问日志写入access.log
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers = access_logger.handlers
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.propagate = False

    # v1.7.3修复：Flask应用日志（app.logger）写入flask_runtime.log，不污染monitor.log
    app.logger.handlers = flask_runtime_logger.handlers
    app.logger.setLevel(logging.DEBUG)
    app.logger.propagate = False

    # 禁用CSRF保护
    _csrf = CSRFProtect()
    _csrf.init_app(app)

    # v1.7.9: V-005修复 — WSGI中间件级隐藏服务器指纹
    # Werkzeug开发服务器在Flask after_request之后才加Server头，必须在WSGI层拦截
    class _RemoveServerHeaderMiddleware:
        def __init__(self, wsgi_app):
            self.wsgi_app = wsgi_app
        def __call__(self, environ, start_response):
            def _start_response(status, headers, exc_info=None):
                headers = [(k, v) for k, v in headers if k.lower() != 'server']
                return start_response(status, headers, exc_info)
            return self.wsgi_app(environ, _start_response)
    app.wsgi_app = _RemoveServerHeaderMiddleware(app.wsgi_app)

    @app.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    # 注册Blueprint
    from web.blueprints import register_blueprints
    register_blueprints(app)

    _app_instance = app
    return app

    @app.context_processor
    def inject_csrf():
        return dict(csrf_token=generate_csrf)


def get_app() -> Flask:
    """获取已创建的应用实例"""
    global _app_instance
    if _app_instance is None:
        raise RuntimeError("Flask app not initialized. Call create_app() first.")
    return _app_instance


def run_app(host: str = "127.0.0.1", port: int = 8080, threaded: bool = True):
    """统一启动Flask应用"""
    app = create_app()
    # v1.7.9: V-005修复 — 禁掉Werkzeug开发服务器的版本信息输出
    # Werkzeug在底层BaseHTTPRequestHandler里硬编码了server_version和sys_version，
    # 不关掉的话每个响应都会带 Server: Werkzeug/x.x.x Python/x.x.x
    try:
        from werkzeug.serving import WSGIRequestHandler
        WSGIRequestHandler.server_version = ""    # 清掉 Werkzeug 版本
        WSGIRequestHandler.sys_version = ""       # 清掉 Python 版本
    except Exception:
        pass
    app.run(host=host, port=port, threaded=threaded, debug=False)
