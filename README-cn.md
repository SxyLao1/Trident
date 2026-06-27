<div align="center">

<pre>
 _____     _     _            _   
|_   _| __(_) __| | ___ _ __ | |_ 
  | || '__| |/ _` |/ _ \ '_ \| __|
  | || |  | | (_| |  __/ | | | |_ 
  |_||_|  |_|\__,_|\___|_| |_|\__|
</pre>

<h1>Trident WebShell 检测系统</h1>

<p>
  <strong>中文</strong> | <a href="README.md">English</a>
</p>

<p>
  <img src="https://img.shields.io/badge/version-1.8.4-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/status-stable-success?style=flat-square" alt="Status">
  <img src="https://img.shields.io/badge/python-3.8%2B-green?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
</p>

<p>跨平台 WebShell 实时检测系统</p>

</div>

---

Trident 是一款面向 Linux 和 Windows 的生产级 WebShell 检测系统。它实时监控文件系统变更，通过内置 YARA 规则引擎检测 WebShell，并提供 Web 管理后台。

核心能力：

- **实时文件监控** — Linux Inotify / Windows ReadDirectoryChangesW 自适应切换
- **主动扫描器** — 全量目录扫描 + SSE 实时进度 + 扫描历史 + 可打印报告
- **YARA 规则引擎** — 18+ 规则文件覆盖 PHP、ASP、JSP、ASPX、Godzilla、冰蝎；支持热重载
- **威胁画像** — UA/时间窗口行为聚类 + IP 池合并 + 衰减引擎
- **文件相似度聚类** — ssdeep/TLSH/SimHash 三轨哈希 + 0.80 阈值簇归并
- **批量操作** — Records/Quarantine 跨页多选 + 批量隔离/恢复/删除
- **WAL 事务日志** — 异步批量写入 + 自动轮转，文件锁定场景下数据丢失极低
- **智能告警** — 指数退避 + 自适应阈值，降低误报
- **Web 管理后台** — 暗色终端风格界面，SSE 实时日志流，HTMX SPA 导航
- **企业级安全** — CSRF 全站保护、IP 白名单、Scrypt 密码哈希、静态 JS 鉴权守卫
- **通配符日志溯源** — 支持 `**/access.log` 递归匹配，自动提取攻击者 IP

## 快速开始

### Linux / macOS

```bash
git clone https://github.com/yourusername/trident.git
cd trident
chmod +x install.sh
./install.sh
```

### Windows

```powershell
git clone https://github.com/yourusername/trident.git
cd trident
.\install.bat
```

安装器自动检测 Python、创建虚拟环境、安装依赖，并提示配置（网站路径、管理员密码、允许 IP）。

### Docker

```bash
docker-compose up -d
```

然后访问 `http://127.0.0.1:8080`。默认用户名 `admin`，密码在首次安装时输出到控制台。

## 项目结构

```
Trident/
├── app.py                  # 入口
├── config.toml             # 主配置
├── config/                 # 配置加载器 & 注册表
├── core/                   # 检测引擎、WAL、指标、告警
├── web/                    # Flask 蓝图、模板、静态资源
├── rules/webshell/         # YARA 规则文件
├── tools/                  # 管理工具
├── scripts/                # 安装脚本 & 服务模板
└── tests/                  # 兼容性 & 工具验证
```

## 依赖要求

- Python 3.8+
- yara-python
- Flask + Flask-WTF
- psutil（Windows 监控优化）

完整列表见 `requirements.txt`。

## 安全提示

- 生产环境务必更换默认 `secret_key`
- 将 `allowed_ips` 限制为管理网段
- 通过 `python tools/admin_passwd.py` 生成强密码哈希
- 公网暴露时启用 HTTPS

## 许可协议

MIT License。可用于生产环境、学术研究和个人用途。

---

<div align="center">
  <sub>Trident Security Platform — MIT License</sub>
</div>
