# -*- coding: utf-8 -*-
"""
@Time: 1/3/2026 8:06 PM
@Auth: SxyLao1
@File: app.py
@IDE: PyCharm
@Motto: HACK THE REAL
v1.7.0主入口：统一Flask应用，解决8080端口冲突
"""
import base64
import os
import sys
import threading
import time
import platform
import datetime

from utils.path_utils import normalize_path
from config.registry import ConfigRegistry
from core.config_watcher import start_config_watcher
from core.metrics import get_metrics, preload_metrics
from core.monitor import WebsiteMonitor
from core.log_analyzer import get_analyzer
from core.log_monitor import LogMonitor
from utils.logger_factory import get_system_logger, get_logger, log_with_symbol  # v1.7.3修改
from core.scanner import quick_scan_yara, get_scanner_chain
from utils.platform_utils import check_port_reachable
from config.version import get_version, get_release_date
# v1.7.0新增：统一Flask应用
from web.factory import create_app, run_app

def load_banner() -> str:
    """
    从banner.txt加载ASCII艺术字
    如果文件不存在，返回默认文字
    """
    try:
        banner_path = normalize_path(__file__).parent / "banner.txt"
        if banner_path.exists():
            return banner_path.read_text(encoding='utf-8')
        else:
            return f"Trident v{get_version()}"
    except Exception as e:
        return f"Trident v{__version__} (加载banner失败: {e})"

def main():
    # ANSI颜色码
    C = {
        'reset': '[0m',
        'bold': '[1m',
        'dim': '[2m',
        'green': '[32m',
        'cyan': '[36m',
        'yellow': '[33m',
        'red': '[31m',
        'blue': '[34m',
        'magenta': '[35m',
        'white': '[37m',
    }
    def _log(*args):
        # v1.7.9: 兼容旧调用 _log(emoji, level, component, msg) 和新的 _log(level, component, msg)
        if len(args) == 4:
            _, level, component, msg = args  # strip emoji
        else:
            level, component, msg = args
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        color = C['green'] if level == 'OK' else C['yellow'] if level == 'WARN' else C['red'] if level == 'ERR' else C['cyan']
        label = f'[{level}]'
        print(f"{C['dim']}{ts}{C['reset']} {color}{label}{C['reset']} {C['bold']}[{component}]{C['reset']} {msg}")
    def _sep(char='─', width=60):
        print(f"{C['dim']}{char * width}{C['reset']}")
    def _header(title):
        print(f"{C['cyan']}▶ {title}{C['reset']}")
        _sep()

    # 启动SSE推送工作线程（必须在任何导入前）
    from utils.sse_manager import start_sse_worker
    start_sse_worker()

    system_logger = get_system_logger()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    # ═══════════════════════════════════════════════════════
    #  启动横幅
    # ═══════════════════════════════════════════════════════
    print(load_banner())
    _sep('═', 60)
    print(f"{C['bold']}{C['green']}  Trident v{get_version()}  {C['reset']}{C['dim']}— WebShell Detection System  |  {get_release_date()}{C['reset']}")
    print(f"{C['dim']}  Platform: {platform.system()} {platform.release()} | Python {platform.python_version()}{C['reset']}")
    _sep('═', 60)

    # ═══════════════════════════════════════════════════════
    #  阶段 1: 配置加载
    # ═══════════════════════════════════════════════════════
    _header('PHASE 1: CONFIGURATION')
    ConfigRegistry.initialize()
    websites = ConfigRegistry.get_enabled_websites()

    if not websites:
        _log('ERR', 'CONFIG', 'No enabled websites found. Exiting.')
        return

    website = websites[0]
    website.path = normalize_path(website.path)
    website_reachable = check_port_reachable("127.0.0.1", website.port)
    website._reachable = website_reachable

    _log('📁', 'OK', 'CONFIG', f'Website: {C["bold"]}{website.name}{C["reset"]}')
    _log('🌐', 'OK' if website_reachable else 'WARN', 'NETWORK',
         f'Port {website.port} {"LISTENING" if website_reachable else "NOT LISTENING (monitor continues)"}')
    _log('📂', 'OK', 'PATH', f'Watch: {website.path}')

    # v1.7.3：每个网站使用独立的monitor logger
    logger = get_logger(website.name)

    # ═══════════════════════════════════════════════════════
    #  阶段 2: 引擎预热
    # ═══════════════════════════════════════════════════════
    _header('PHASE 2: ENGINE WARMUP')
    preload_metrics()
    scanner_chain = get_scanner_chain(logger)
    engines = [e.get_name() for _, e in scanner_chain.engines]
    _log('🔍', 'OK', 'SCANNER', f'Loaded {len(engines)} engine(s): {", ".join(engines)}')
    _log('📊', 'OK', 'METRICS', 'Metrics preloaded')

    # ═══════════════════════════════════════════════════════
    #  阶段 3: API服务启动
    # ═══════════════════════════════════════════════════════
    _header('PHASE 3: API SERVICE')
    api_config = ConfigRegistry.get_raw_config().get("api", {})
    host = api_config.get("health_check_host", "127.0.0.1")
    port = api_config.get("health_check_port", 8080)

    app = create_app()
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
    )

    threading.Thread(
        target=run_app,
        kwargs={"host": host, "port": port},
        daemon=True,
        name="FlaskUnifiedServer"
    ).start()

    _log('🚀', 'OK', 'API', f'Flask starting on {C["bold"]}http://{host}:{port}{C["reset"]}')
    _log('🔗', 'OK', 'API', f'Health  → http://{host}:{port}/api/v1/health')
    _log('🛡', 'OK', 'API', f'Admin   → http://{host}:{port}/admin')

    # ═══════════════════════════════════════════════════════
    #  阶段 4: 监控启动
    # ═══════════════════════════════════════════════════════
    _header('PHASE 4: MONITOR STARTUP')

    config_observer = start_config_watcher(ConfigRegistry, logger)
    _log('⚙', 'OK', 'WATCHER', 'Config hot-reload watcher started')

    analyzer = get_analyzer(website, logger)
    log_monitor = LogMonitor(logger, analyzer)
    log_monitor.start()
    _log('📜', 'OK', 'LOG', f'Log monitor started (tail from analyzer position)')

    scan_callback = quick_scan_yara
    monitor = WebsiteMonitor(website, scan_callback, logger)
    monitor.start()
    _log('👁', 'OK', 'MONITOR', f'File watcher started on {website.path}')

    from core.metrics import get_metrics
    get_metrics().load_persisted()
    metrics = get_metrics()
    _log('💾', 'OK', 'METRICS', 'Persisted metrics loaded')

    # ═══════════════════════════════════════════════════════
    #  就绪汇总
    # ═══════════════════════════════════════════════════════
    time.sleep(0.5)  # 等待Flask线程启动
    _sep('═', 60)
    print(f"{C['bold']}{C['green']}  ✓ ALL SYSTEMS OPERATIONAL{C['reset']}")
    _sep('═', 60)
    print(f"  {C['dim']}Dashboard:{C['reset']}  http://{host}:{port}/admin")
    print(f"  {C['dim']}Health:   {C['reset']}  http://{host}:{port}/api/v1/health")
    print(f"  {C['dim']}Watch:    {C['reset']}  {website.path}")
    print(f"  {C['dim']}Engines:  {C['reset']}  {', '.join(engines)}")
    print(f"  {C['dim']}Version:  {C['reset']}  v{__version__}")
    _sep('═', 60)
    print(f"{C['dim']}  Press Ctrl+C to stop{C['reset']}")

    try:
        while True:
            if int(time.time()) % 60 == 0:  # 每分钟检查一次
                try:
                    from core.suspicious_registry import _async_save_queue
                    if _async_save_queue and _async_save_queue.qsize() > 10000:
                        _log('🚨', 'ERR', 'RISK', f'Registry queue backlog: {_async_save_queue.qsize()} items')

                    from core.notifier import get_notifier
                    notifier = get_notifier(logger)
                    if hasattr(notifier, '_alert_queue') and notifier._alert_queue.qsize() > 500:
                        _log('🚨', 'ERR', 'RISK', f'Alert queue backlog: {notifier._alert_queue.qsize()} items')

                    metrics.record_memory_usage()
                    mem = metrics.get()["memory_mb"]
                    if mem > 500:
                        _log('🚨', 'ERR', 'RISK', f'Memory usage high: {mem:.1f}MB')
                except Exception as e:
                    system_logger.error(f"[RISK][CHECK] 监控检查失败: {e}", exc_info=True)

            if int(time.time()) % 300 == 0:
                metrics.record_memory_usage()
                mem = metrics.get()["memory_mb"]
                if mem > 500:
                    _log('🚨', 'ERR', 'RISK', f'Memory usage high: {mem:.1f}MB')

            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n{C['yellow']}⚠  Interrupted by user{C['reset']}")
        config_observer.stop()
        config_observer.join()
        log_monitor.stop()
        monitor.stop()
        _sep('─', 60)
        _log('📊', 'OK', 'STAT', f'{monitor.website.name} running: {monitor.is_running()}')
        _sep('─', 60)


if __name__ == "__main__":
    main()