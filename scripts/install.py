#!/usr/bin/env python3
"""
Trident Installer Core v1.7.8
Cross-platform installation logic with resilience.
"""
import sys, os, subprocess, shutil, platform, socket, glob, re, json, urllib.request
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

class C:
    RED = '\033[91m'; GREEN = '\033[92m'; YELLOW = '\033[93m'; CYAN = '\033[96m'
    BOLD = '\033[1m'; DIM = '\033[2m'; NC = '\033[0m'
    @classmethod
    def disable(cls):
        if platform.system() == 'Windows':
            for attr in dir(cls):
                if not attr.startswith('_') and attr != 'disable':
                    setattr(cls, attr, '')

if platform.system() == 'Windows' and not sys.stdout.isatty():
    C.disable()

# ============================================================================
# Trident LOG_PATTERNS (from core/log_analyzer.py)
# ============================================================================
LOG_PATTERNS = [
    r'(?P<ip>\d+\.\d+\.\d+\.\d+)\s+-(\s+-)?\s*\[(?P<time>[^\]]+)\]\s*"(?P<method>\w+)\s+(?P<url>[^ ]+)\s+[^"]+"\s+(?P<status>\d+)\s+(?P<size>\d+)',
    r'(?P<ip>\d+\.\d+\.\d+\.\d+)\s+(?:-|\S*)\s+(?:-|\S*)\s*\[(?P<time>[^\]]+)\]\s*"(?P<method>\w+)\s+(?P<url>[^ ]+)\s+[^"]+"\s+(?P<status>\d+)\s+(?P<size>\d+)\s+"[^"]*"\s+"[^"]*"'
]


def get_trident_version():
    try:
        from config.version import get_version
        return get_version()
    except Exception:
        try:
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli as tomllib
            with open(os.path.join(PROJECT_ROOT, 'config.toml'), 'rb') as f:
                return tomllib.load(f).get('system', {}).get('version', 'unknown')
        except Exception:
            return 'unknown'


def is_china_network():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('223.5.5.5', 53))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_pypi_mirrors():
    if is_china_network():
        print(f"{C.CYAN}  [INFO] China network detected, using domestic PyPI mirrors{C.NC}")
        return [
            ('https://pypi.tuna.tsinghua.edu.cn/simple', ['pypi.tuna.tsinghua.edu.cn']),
            ('https://mirrors.aliyun.com/pypi/simple', ['mirrors.aliyun.com']),
            ('https://pypi.mirrors.ustc.edu.cn/simple', ['pypi.mirrors.ustc.edu.cn']),
            ('https://pypi.doubanio.com/simple', ['pypi.doubanio.com']),
        ]
    else:
        return [('https://pypi.org/simple', ['pypi.org', 'files.pythonhosted.org'])]


def run_cmd(cmd, cwd=None, timeout=60):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def check_vc_build_tools():
    """Check if Visual C++ Build Tools are installed on Windows"""
    if platform.system() != 'Windows':
        return True, "Not Windows"

    # Check for cl.exe
    ok, out, err = run_cmd(['where', 'cl.exe'], timeout=5)
    if ok:
        return True, "cl.exe found"

    # Check common VS paths
    vs_paths = [
        r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools',
        r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools',
        r'C:\Program Files\Microsoft Visual Studio\2022\BuildTools',
        r'C:\Program Files\Microsoft Visual Studio\2019\BuildTools',
    ]
    for p in vs_paths:
        if os.path.exists(p):
            return True, f"VS BuildTools found: {p}"

    return False, "Visual C++ Build Tools not found"


def download_yara_wheel(venv_python):
    """Try to download pre-built yara-python wheel for Windows"""
    if platform.system() != 'Windows':
        return False, "Not Windows"

    import platform as plat
    arch = plat.machine().lower()
    py_ver = f"cp{sys.version_info.major}{sys.version_info.minor}"

    # Map architecture
    if 'amd64' in arch or 'x86_64' in arch:
        wheel_arch = 'win_amd64'
    elif 'arm64' in arch:
        wheel_arch = 'win_arm64'
    else:
        wheel_arch = 'win32'

    # Try to find matching wheel from PyPI
    yara_version = "4.5.1"  # Known stable version
    wheel_name = f"yara_python-{yara_version}-{py_ver}-{py_ver}-{wheel_arch}.whl"

    urls = [
        f"https://files.pythonhosted.org/packages/{wheel_name}",
        f"https://pypi.tuna.tsinghua.edu.cn/packages/{wheel_name}",
    ]

    wheel_path = os.path.join(PROJECT_ROOT, wheel_name)

    for url in urls:
        try:
            print(f"{C.CYAN}  Trying to download yara-python wheel...{C.NC}")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(wheel_path, 'wb') as f:
                    f.write(response.read())

            # Install the wheel
            ok, out, err = run_cmd([venv_python, '-m', 'pip', 'install', wheel_path], timeout=60)
            if ok:
                os.remove(wheel_path)
                return True, "yara-python installed from pre-built wheel"
            else:
                os.remove(wheel_path)
        except Exception as e:
            continue

    return False, "Could not download pre-built wheel"


def install_with_fallback(venv_python, req_file):
    """Full dependency installation with multiple fallback strategies"""

    # Strategy 1: Normal pip install with mirrors
    mirrors = get_pypi_mirrors()
    for i, (mirror_url, trusted_hosts) in enumerate(mirrors):
        print(f"{C.CYAN}  Trying mirror {i+1}/{len(mirrors)}: {mirror_url}{C.NC}")
        cmd = [venv_python, '-m', 'pip', 'install', '-r', req_file,
               '--index-url', mirror_url, '--timeout', '60', '--no-cache-dir']
        for host in trusted_hosts:
            cmd.extend(['--trusted-host', host])
        ok, out, err = run_cmd(cmd, timeout=120)
        if ok:
            print(f"{C.GREEN}  [OK] Dependencies installed{C.NC}")
            return True, "normal"
        else:
            print(f"{C.YELLOW}  [WARN] Mirror {i+1} failed{C.NC}")
            detail = err.strip() or out.strip()
            if detail:
                print(f"{C.DIM}  {detail[:600]}{C.NC}")

    # Strategy 2: System default pip
    print(f"{C.YELLOW}  [WARN] All mirrors failed, trying system default...{C.NC}")
    ok, out, err = run_cmd([venv_python, '-m', 'pip', 'install', '-r', req_file, '--no-cache-dir'], timeout=120)
    if ok:
        return True, "system_default"

    # Strategy 3: Check if it's yara-python compilation issue on Windows
    if platform.system() == 'Windows' and 'yara' in err.lower():
        print(f"{C.YELLOW}  [WARN] yara-python compilation failed. Trying pre-built wheel...{C.NC}")
        ok, msg = download_yara_wheel(venv_python)
        if ok:
            # Retry remaining packages without yara-python
            print(f"{C.GREEN}  [OK] {msg}{C.NC}")
            # Install everything else
            ok2, out2, err2 = run_cmd([venv_python, '-m', 'pip', 'install', '-r', req_file, 
                                       '--no-cache-dir', '--no-deps'], timeout=120)
            if ok2:
                return True, "yara_wheel"

    # Strategy 4: Check if packages already exist globally
    print(f"{C.YELLOW}  [WARN] Checking if packages exist in system Python...{C.NC}")
    sys_python = sys.executable
    missing = []
    with open(req_file, 'r') as f:
        for line in f:
            pkg = line.strip().split('#')[0].strip()
            if pkg and not pkg.startswith('-'):
                pkg_name = pkg.split('==')[0].split('>=')[0].split('<')[0].strip()
                ok_pkg, _, _ = run_cmd([sys_python, '-c', f'import {pkg_name.replace("-", "_")}; print("OK")'], timeout=5)
                if not ok_pkg:
                    missing.append(pkg_name)

    if not missing:
        print(f"{C.GREEN}  [OK] All packages already available in system Python{C.NC}")
        print(f"{C.YELLOW}  [INFO] Consider recreating venv with --system-site-packages{C.NC}")
        return True, "system_packages"
    else:
        print(f"{C.RED}  Missing packages: {', '.join(missing)}{C.NC}")

    return False, "all_failed"


def upgrade_pip(venv_python):
    print(f"{C.CYAN}  Upgrading pip...{C.NC}")
    ok, out, err = run_cmd([venv_python, '-m', 'pip', 'install', '--upgrade', 'pip', '-q'], timeout=30)
    if ok:
        print(f"{C.GREEN}  [OK] pip upgraded{C.NC}")
    else:
        print(f"{C.YELLOW}  [WARN] pip upgrade failed: {err[:200]}{C.NC}")
    return ok


def verify_critical_packages(venv_python):
    critical = [
        ('flask', 'Flask'), ('watchdog', 'Watchdog'), ('yara', 'YARA'),
        ('requests', 'Requests'), ('psutil', 'psutil'),
        ('flask_wtf', 'Flask-WTF'), ('wtforms', 'WTForms'),
    ]
    missing = []
    for module, name in critical:
        ok, out, err = run_cmd([venv_python, '-c', f'import {module}; print("OK")'], timeout=10)
        if ok and 'OK' in out:
            print(f"{C.GREEN}    ✓ {name}{C.NC}")
        else:
            print(f"{C.RED}    ✗ {name}{C.NC}")
            missing.append(name)
    return len(missing) == 0, missing


def validate_path(path_str, label="Path"):
    if not path_str or path_str == '.':
        return False, f"{label} is empty"
    p = Path(path_str.replace('/', os.sep))
    if not p.exists():
        return False, f"{label} does not exist: {p}"
    if not p.is_dir():
        return False, f"{label} is not a directory: {p}"
    try:
        list(p.iterdir())
        return True, f"{label} OK: {p}"
    except PermissionError:
        return False, f"{label} no read permission: {p}"


def find_log_files(website_path):
    patterns = ["**/access.log", "**/nginx/access.log", "**/apache/access.log", "**/logs/access.log", "**/*.log"]
    found = []
    wp = Path(website_path.replace('/', os.sep))
    if not wp.exists():
        return found
    for pattern in patterns:
        matches = list(wp.glob(pattern))
        for m in matches:
            if m.is_file() and m.stat().st_size > 0:
                found.append(str(m))
        if found:
            break
    return found


def test_log_format(log_file_path, max_lines=10):
    try:
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [l.strip() for l in f if l.strip()][:max_lines]
        if not lines:
            return False, "Log file is empty", None
        for line in lines:
            for pattern in LOG_PATTERNS:
                m = re.match(pattern, line)
                if m:
                    ip = m.group('ip') if 'ip' in m.groupdict() else 'unknown'
                    return True, f"Format matched (IP: {ip})", line
        return False, f"Format NOT matched. Sample: {lines[0][:120]}", lines[0]
    except Exception as e:
        return False, f"Read error: {e}", None


def validate_log_config(cfg):
    log_config = cfg.get('website', {}).get('log_config', {})
    access_log_path = log_config.get('access_log_path', '')
    website_path = cfg.get('website', {}).get('path', '')

    print(f"\n{C.CYAN}[Log Configuration Validation]{C.NC}")

    if access_log_path:
        p = Path(access_log_path.replace('/', os.sep))
        if p.exists() and p.is_file():
            print(f"  Configured log: {p}")
            ok, msg, sample = test_log_format(str(p))
            if ok:
                print(f"  {C.GREEN}  ✓ {msg}{C.NC}")
                return True, str(p)
            else:
                print(f"  {C.YELLOW}  ⚠ {msg}{C.NC}")
        else:
            print(f"  {C.YELLOW}  ⚠ Configured log not found: {p}{C.NC}")
    else:
        print(f"  {C.YELLOW}  ⚠ access_log_path not configured{C.NC}")

    if website_path and website_path != '.':
        print(f"  Searching under website path: {website_path}")
        found = find_log_files(website_path)
        if found:
            for log_file in found[:3]:
                ok, msg, sample = test_log_format(log_file)
                status = f"{C.GREEN}✓{C.NC}" if ok else f"{C.YELLOW}✗{C.NC}"
                print(f"  {status} {log_file} -> {msg}")
                if ok:
                    update = input(f"  Update config.toml with this log path? [Y/n]: ").strip().lower()
                    if update != 'n':
                        if 'log_config' not in cfg['website']:
                            cfg['website']['log_config'] = {}
                        cfg['website']['log_config']['access_log_path'] = log_file.replace(os.sep, '/')
                        return True, log_file
            print(f"  {C.YELLOW}No matching log format found.{C.NC}")
        else:
            print(f"  {C.YELLOW}No log files found under website path.{C.NC}")

    print(f"\n{C.YELLOW}[WARN] Log monitoring may not work without valid access.log.{C.NC}")
    print(f"{C.DIM}  Supported: Nginx / Apache standard access log{C.NC}")
    print(f"{C.DIM}  Example: 192.168.1.1 - - [27/May/2026:10:00:00 +0800] \"GET /index.php HTTP/1.1\" 200 1234{C.NC}")
    return False, None


def load_config():
    config_path = os.path.join(PROJECT_ROOT, 'config.toml')
    if not os.path.exists(config_path):
        return None
    try:
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        with open(config_path, 'rb') as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"{C.YELLOW}[WARN] Failed to parse config.toml: {e}{C.NC}")
        return None


def save_config(cfg):
    """保存 config.toml，并同步提取敏感值到 .env 文件"""
    try:
        try:
            import tomli_w
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'tomli-w', '-q'])
            import tomli_w

        config_path = os.path.join(PROJECT_ROOT, 'config.toml')
        env_path = os.path.join(PROJECT_ROOT, '.env')

        # 备份原配置
        if os.path.exists(config_path) and not os.path.exists(config_path + '.backup'):
            shutil.copy(config_path, config_path + '.backup')
            print(f"{C.DIM}  Backup: config.toml.backup{C.NC}")

        # 提取敏感值，生成 .env 文件
        env_lines = ['# Trident Environment Variables — Auto-generated by install.py', '']

        web_admin = cfg.get('web_admin', {})
        security = cfg.get('security', {})
        alert = cfg.get('alert', {})

        # 提取真实值（非占位符）
        password_hash = web_admin.get('password_hash', '')
        if password_hash and 'YOUR_HASH_HERE' not in password_hash:
            env_lines.append(f'TRIDENT_PASSWORD_HASH={password_hash}')

        secret_key = security.get('secret_key', '')
        if secret_key and 'YOUR_SECRET_KEY_HERE' not in secret_key:
            env_lines.append(f'TRIDENT_SECRET_KEY={secret_key}')

        webhook_url = alert.get('webhook_url', '')
        if webhook_url:
            env_lines.append(f'TRIDENT_WEBHOOK_URL={webhook_url}')

        # 写入 .env（如果不存在或需要更新）
        if len(env_lines) > 2:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(env_lines))
            print(f"{C.GREEN}  Generated .env with sensitive values{C.NC}")

        # 保存 config.toml（敏感值保持占位符，由 loader 解析时从 .env 覆盖）
        with open(config_path, 'wb') as f:
            tomli_w.dump(cfg, f)
        return True
    except Exception as e:
        print(f"{C.RED}[ERROR] Failed to save config: {e}{C.NC}")
        return False


def check_existing_config(cfg):
    if not cfg:
        return False
    website = cfg.get('website', {})
    web_admin = cfg.get('web_admin', {})
    has_path = bool(website.get('path')) and website.get('path') != '.'
    has_password = bool(web_admin.get('password_hash')) and 'scrypt' in str(web_admin.get('password_hash', ''))
    has_custom_ip = bool(web_admin.get('allowed_ips')) and web_admin.get('allowed_ips') != ['127.0.0.1']
    return has_path or has_password or has_custom_ip


def print_banner(version):
    print(f"""
{C.CYAN}  _____     _     _            _   {C.NC}
{C.CYAN} |_   _| __(_) __| | ___ _ __ | |_ {C.NC}
{C.CYAN}   | || '__| |/ _\` |/ _ \\ '_ \\| __|{C.NC}
{C.CYAN}   | || |  | | (_| |  __/ | | | |_ {C.NC}
{C.CYAN}   |_||_|  |_|\\__,_|\\___|_| |_|\\__|{C.NC}

{C.GREEN}  Trident WebShell Detector v{version} Installer{C.NC}
{C.GREEN}  ========================================={C.NC}
""")


def detect_venv_python():
    venv_dir = os.path.join(PROJECT_ROOT, 'venv')
    candidates = [
        os.path.join(venv_dir, 'bin', 'python'),
        os.path.join(venv_dir, 'Scripts', 'python.exe'),
        os.path.join(venv_dir, 'bin', 'python3'),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def create_venv(python_cmd):
    venv_dir = os.path.join(PROJECT_ROOT, 'venv')
    if os.path.exists(os.path.join(venv_dir, 'bin', 'python')) or \
       os.path.exists(os.path.join(venv_dir, 'Scripts', 'python.exe')):
        print(f"{C.YELLOW}  [SKIP] venv already exists{C.NC}")
        return True
    print(f"{C.CYAN}  Creating venv...{C.NC}")
    ok, out, err = run_cmd([python_cmd, '-m', 'venv', venv_dir], timeout=60)
    if not ok:
        print(f"{C.RED}  [ERROR] {err}{C.NC}")
        return False
    print(f"{C.GREEN}  [OK] venv created{C.NC}")
    return True


def init_dirs():
    for d in ['data/sessions', 'logs/Trident', 'logs/Website-PhpStudy', 'logs/integration', 'logs/yara']:
        os.makedirs(os.path.join(PROJECT_ROOT, d), exist_ok=True)
    print(f"{C.GREEN}  [OK] Directories initialized{C.NC}")


def configure_website(cfg):
    website = cfg.get('website', {})
    current_path = website.get('path', '')

    print(f"\n{C.CYAN}[Website Configuration]{C.NC}")
    if current_path and current_path != '.':
        print(f"  Current: {current_path}")
        ok, msg = validate_path(current_path, "Website path")
        if ok:
            print(f"  {C.GREEN}  ✓ {msg}{C.NC}")
        else:
            print(f"  {C.YELLOW}  ⚠ {msg}{C.NC}")

        choice = input(f"  Change? [y/N]: ").strip().lower()
        if choice != 'y':
            print(f"{C.DIM}  Keeping: {current_path}{C.NC}")
            return cfg

    print("  Examples: /var/www/html, E:/Software/phpstudy_pro/WWW, C:/inetpub/wwwroot")
    while True:
        new_path = input("  Website root path: ").strip()
        if not new_path:
            break
        ok, msg = validate_path(new_path, "Website path")
        if ok:
            cfg['website']['path'] = new_path.replace('\\', '/')
            print(f"{C.GREEN}  ✓ Set: {cfg['website']['path']}{C.NC}")
            # Auto-discover log files and update log_config
            print(f"{C.CYAN}  Auto-discovering log files...{C.NC}")
            found = find_log_files(new_path)
            if found:
                for log_file in found[:3]:
                    l_ok, l_msg, sample = test_log_format(log_file)
                    if l_ok:
                        if 'log_config' not in cfg['website']:
                            cfg['website']['log_config'] = {}
                        cfg['website']['log_config']['access_log_path'] = log_file.replace(os.sep, '/')
                        print(f"  {C.GREEN}  ✓ Auto-linked log: {log_file}{C.NC}")
                        break
            break
        else:
            print(f"  {C.RED}  ✗ {msg}{C.NC}")
            print(f"  {C.YELLOW}  Please enter a valid directory path.{C.NC}")

    return cfg


def configure_admin(cfg):
    web_admin = cfg.get('web_admin', {})
    current_hash = web_admin.get('password_hash', '')

    print(f"\n{C.CYAN}[Admin Configuration]{C.NC}")
    if current_hash and 'scrypt' in current_hash:
        print(f"  Password: CONFIGURED")
        choice = input(f"  Change password? [y/N]: ").strip().lower()
        if choice != 'y':
            print(f"{C.DIM}  Keeping existing password{C.NC}")
            return cfg

    from werkzeug.security import generate_password_hash
    new_pass = input("  New admin password [default: admin123]: ").strip() or "admin123"
    new_hash = generate_password_hash(new_pass)
    cfg['web_admin']['password_hash'] = new_hash
    print(f"{C.GREEN}  Password updated{C.NC}")
    return cfg


def configure_security(cfg):
    web_admin = cfg.get('web_admin', {})
    current_ips = web_admin.get('allowed_ips', ['127.0.0.1'])

    print(f"\n{C.CYAN}[Security Configuration]{C.NC}")
    print(f"  Current allowed IPs: {current_ips}")
    choice = input("  Add more IPs? (comma-separated, or 'skip'): ").strip()
    if choice and choice.lower() != 'skip':
        new_ips = [ip.strip() for ip in choice.split(',')]
        cfg['web_admin']['allowed_ips'] = new_ips
        print(f"{C.GREEN}  Updated: {new_ips}{C.NC}")
    return cfg


def print_summary(version):
    print(f"""
{C.GREEN}========================================{C.NC}
{C.GREEN}  Trident v{version} Ready!{C.NC}
{C.GREEN}========================================{C.NC}

{C.CYAN}Quick Start:{C.NC}
  Foreground:   {C.BOLD}./start.sh{C.NC} (Linux) / {C.BOLD}start.bat{C.NC} (Windows)
  Background:   {C.BOLD}./start_background.sh{C.NC} / {C.BOLD}start_background.bat{C.NC}
  Stop:         {C.BOLD}./stop.sh{C.NC} / {C.BOLD}stop.bat{C.NC}
  URL:          {C.BOLD}http://127.0.0.1:8080{C.NC}
  Login:        {C.BOLD}admin{C.NC} / (your password)

{C.CYAN}Files:{C.NC}
  Config:       config.toml
  Logs:         logs/Trident/
  Tests:        python test/test_runner.py --suite=all

{C.GREEN}Happy hunting!{C.NC}
""")


def print_manual_fix_guide(venv_python, req_file):
    vc_ok, vc_msg = check_vc_build_tools()

    print(f"""
{C.YELLOW}========================================{C.NC}
{C.YELLOW}  Manual Fix Guide{C.NC}
{C.YELLOW}========================================{C.NC}

1. {C.BOLD}Upgrade pip manually:{C.NC}
   {venv_python} -m pip install --upgrade pip

2. {C.BOLD}Install with trusted hosts:{C.NC}
   {venv_python} -m pip install -r {req_file} \\
       --index-url https://pypi.tuna.tsinghua.edu.cn/simple \\
       --trusted-host pypi.tuna.tsinghua.edu.cn \\
       --trusted-host files.pythonhosted.org

3. {C.BOLD}If behind corporate proxy:{C.NC}
   set HTTP_PROXY=http://proxy.company.com:8080
   set HTTPS_PROXY=http://proxy.company.com:8080
   Then retry install.bat

4. {C.BOLD}If SSL certificate errors:{C.NC}
   {venv_python} -m pip install --upgrade certifi
   Then retry install.bat
""")

    if platform.system() == 'Windows' and not vc_ok:
        print(f"""
5. {C.BOLD}yara-python requires Visual C++ Build Tools:{C.NC}
   {C.RED}  Status: {vc_msg}{C.NC}
   Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   Or try pre-built wheel:
     {venv_python} -m pip install yara_python-4.5.1-cp312-cp312-win_amd64.whl

""")

    print(f"""
6. {C.BOLD}If you already have the packages:{C.NC}
   Check: {venv_python} -c "import flask; print('OK')"
   If OK, you can ignore this error and run start.bat directly.

{C.CYAN}After fixing, run: install.bat again{C.NC}
""")


def main():
    version = get_trident_version()
    print_banner(version)

    # Step 1: Config
    print(f"{C.CYAN}[1/7] Loading configuration...{C.NC}")
    cfg = load_config()
    if cfg is None:
        print(f"{C.RED}[ERROR] config.toml not found{C.NC}")
        sys.exit(1)

    existing = check_existing_config(cfg)

    if existing:
        print(f"\n{C.YELLOW}[NOTICE] Existing configuration detected:{C.NC}")
        website = cfg.get('website', {})
        web_admin = cfg.get('web_admin', {})
        log_config = cfg.get('website', {}).get('log_config', {})

        print(f"  Website path: {website.get('path', 'NOT SET')}")
        print(f"  Admin user:   {web_admin.get('username', 'NOT SET')}")
        print(f"  Password:     {'CONFIGURED' if web_admin.get('password_hash') else 'NOT SET'}")
        print(f"  Allowed IPs:  {web_admin.get('allowed_ips', ['127.0.0.1'])}")
        print(f"  Log path:     {log_config.get('access_log_path', 'NOT SET')}")

        print(f"\n{C.CYAN}Options:{C.NC}")
        print(f"  [{C.BOLD}K{C.NC}]eep  - Keep existing config, only install dependencies")
        print(f"  [{C.BOLD}O{C.NC}]ver  - Overwrite all configuration")
        print(f"  [{C.BOLD}R{C.NC}]ev   - Review and selectively update")
        print(f"  [{C.BOLD}S{C.NC}]kip  - Skip install entirely")

        choice = input(f"\nYour choice [K/o/r/s]: ").strip().lower() or 'k'

        if choice == 's':
            print(f"{C.YELLOW}Installation cancelled.{C.NC}")
            sys.exit(0)
        elif choice == 'k':
            print(f"\n{C.CYAN}Keeping existing configuration.{C.NC}")
            website_path = cfg.get('website', {}).get('path', '')
            if website_path:
                ok, msg = validate_path(website_path, "Website path")
                print(f"  {'✓' if ok else '⚠'} {msg}")
            validate_log_config(cfg)
        elif choice == 'o':
            print(f"\n{C.CYAN}Reconfiguring...{C.NC}")
            cfg = configure_website(cfg)
            cfg = configure_admin(cfg)
            cfg = configure_security(cfg)
            validate_log_config(cfg)
            save_config(cfg)
        elif choice == 'r':
            print(f"\n{C.CYAN}Review mode...{C.NC}")
            cfg = configure_website(cfg)
            cfg = configure_admin(cfg)
            cfg = configure_security(cfg)
            validate_log_config(cfg)
            save_config(cfg)
        else:
            print(f"\n{C.YELLOW}Invalid choice, keeping existing config.{C.NC}")
            website_path = cfg.get('website', {}).get('path', '')
            if website_path:
                ok, msg = validate_path(website_path, "Website path")
                print(f"  {'✓' if ok else '⚠'} {msg}")
            validate_log_config(cfg)
    else:
        print(f"\n{C.CYAN}[NOTICE] No existing configuration. Starting fresh setup...{C.NC}")
        cfg = configure_website(cfg)
        cfg = configure_admin(cfg)
        cfg = configure_security(cfg)
        validate_log_config(cfg)
        save_config(cfg)

    # Step 2: Python
    print(f"\n{C.CYAN}[2/7] Detecting Python...{C.NC}")
    python_cmd = sys.executable
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"{C.GREEN}  [OK] Python {py_version} ({python_cmd}){C.NC}")

    # Step 3: venv
    print(f"\n{C.CYAN}[3/7] Virtual environment...{C.NC}")
    if not create_venv(python_cmd):
        sys.exit(1)
    venv_python = detect_venv_python() or python_cmd

    # Step 4: Upgrade pip
    print(f"\n{C.CYAN}[4/7] Upgrading pip...{C.NC}")
    upgrade_pip(venv_python)

    # Step 5: Install dependencies
    print(f"\n{C.CYAN}[5/7] Installing dependencies...{C.NC}")
    req_file = os.path.join(PROJECT_ROOT, 'requirements.txt')
    if not os.path.exists(req_file):
        print(f"{C.RED}[ERROR] requirements.txt not found{C.NC}")
        sys.exit(1)

    install_ok, strategy = install_with_fallback(venv_python, req_file)

    # Step 6: Verify
    print(f"\n{C.CYAN}[6/7] Verifying installation...{C.NC}")
    all_ok, missing = verify_critical_packages(venv_python)

    if all_ok:
        print(f"{C.GREEN}  [OK] All packages verified{C.NC}")
    elif install_ok:
        print(f"{C.YELLOW}  [WARN] Some packages not importable: {', '.join(missing)}{C.NC}")
        print(f"{C.YELLOW}  This may be normal for yara-python on first install.{C.NC}")
    else:
        print(f"\n{C.RED}  [FATAL] Dependency installation failed.{C.NC}")
        print(f"{C.RED}  Missing packages: {', '.join(missing)}{C.NC}")
        print_manual_fix_guide(venv_python, req_file)
        cont = input(f"{C.YELLOW}Continue anyway and try to start? [y/N]: {C.NC}").strip().lower()
        if cont != 'y':
            sys.exit(1)

    # Step 7: Initialize
    print(f"\n{C.CYAN}[7/7] Initialization...{C.NC}")
    init_dirs()
    print_summary(version)


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:
        if platform.system() == 'Windows' and e.code != 0:
            print("\n")
            input("Press Enter to exit...")
        raise
