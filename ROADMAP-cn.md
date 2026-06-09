# 路线图

> **当前版本**：v1.7.8（稳定版）  
> **下一里程碑**：v1.8.0  
> **愿景**：轻量级 Web 边界安全 — 被动检测 + 半主动响应

---

## v1.8.0 — 威胁检测扩展（2026-Q3）

**目标**：从"仅 WebShell"扩展到"Web 层威胁检测平台"。

**核心原则**：
- 被动检测优先：文件系统监控 + 日志分析，零 HTTP 拦截
- 半主动响应：检测到威胁后自动隔离文件 + 阻断 IP，HTTP 过滤留给 Nginx/WAF
- 开放接口：提供 IP 封禁 API，对接自有 WAF/FW
- 攻击面收敛：管理后台加固、多站点支持、前端不暴露版本号

**计划功能**：

| # | 功能 | 模块 | 复杂度 |
|---|------|------|--------|
| 1 | 文件自动隔离 | `core/quarantine.py` | 低 |
| 2 | IP 自动阻断（本地黑名单） | `core/ip_blocker.py` | 中 |
| 3 | IP 阻断 API（外部 WAF/FW） | `core/ip_blocker.py` | 中 |
| 4 | 进程行为监控 | `core/process_monitor.py` | 中 |
| 5 | 内存马插件架构 | `plugins/java-memshell/` | 高 |
| 6 | PE/EXE 上传检测 | `core/pe_detector.py` | 低 |
| 7 | Webhook 告警（钉钉/企业微信/飞书） | `core/notifier.py` | 低 |
| 8 | SIEM 导出（JSON Lines / CEF / Syslog） | `utils/siem_formatter.py` | 中 |
| 9 | MITRE ATT&CK 标签 | 事件 schema | 低 |
| 10 | 攻击链还原 | Dashboard 时间轴 | 中 |

**设计决策**：

- **IP 阻断**："事件输出者，而非执行者" — 维护内部黑名单表 + Webhook 输出；由外部 WAF/FW 执行封禁
- **自动处置**：三层置信度（低/中/高），阈值可配置
- **内存马**：插件架构配合 subprocess 编排；Python 代码库不嵌入 JVM/CLR
- **存储层**：v1.8 保持 JSON；v1.9 引入 SQLite（可选），通过抽象层切换

---

## v1.9.x — 多站点 + 生态（2026-Q4）

- 多站点监控：`config.toml` 中 `[[website]]` 数组，单 Dashboard 管理所有站点
- 站点隔离：每个站点独立 registry/WAL，或共享中央 WAL
- 集中告警：单 Webhook 带 `site_id` 标签
- Geo-IP：MaxMind GeoLite2 集成
- 威胁情报：MISP / AbuseIPDB 集成
- 管理后台加固：2FA（TOTP）、登录频率限制、暴力破解检测
- API 密钥管理：带作用域的密钥，供外部系统调用
- SQLite 默认后端

---

## v2.0-alpha — 架构重构（2026-Q3/Q4）

**目标**：从"脚本项目"升级为"Python 包"，引入整洁架构。

**结构变更**：
- 新增 `pyproject.toml`，支持 `pip install -e .`
- `app.py` 移至 `src/trident/` 包结构
- 引入 `domain/ports.py` 抽象层
- 分离 domain / application / infrastructure 三层
- 插件契约：新检测引擎通过插件接入，无需硬编码
- 存储抽象：`JsonEventRepository` → `SQLiteEventRepository`

**目标目录结构**：
```
trident/
├── pyproject.toml
├── src/trident/
│   ├── domain/      （模型、接口、事件）
│   ├── application/ （用例、插件管理）
│   ├── infrastructure/ （持久化、配置、Web、监控）
│   └── interfaces/  （CLI、API、Dashboard）
└── plugins/
```
