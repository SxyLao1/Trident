# 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)
和 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [1.8.3] - 2026-06-26

### 新增
- **攻击者画像引擎**：UA+时间窗口聚类、IP 池重叠自动合并、衰减可视化（红/黄/灰）
- **文件相似度聚类**：三轨哈希引擎（ssdeep/py-tlsh/SimHash），80% 相似度阈值自动归簇
- **WebShell 解码过滤器**：Unicode/Hex/char()/拼接/str_replace 多轮解码 + 变量内联替换
- **IP 封禁模块**：多设备广播架构（stdout/mock/http），失败重试队列（指数退避），持久化
- **Mock WAF 服务**：4 种攻击场景，时间压缩模拟，有状态增量事件轮询
- **报告生成器**：可打印 HTML 报告，含 MITRE ATT&CK 标签 + 攻击检测时间线 + 处置建议
- **WAF 事件桥**：抽象接口 + HTTP 客户端 + 后台轮询 + JSONL 缓存
- **Log Analyzer**：全屏日志分析器，关键词+级别+模块+时间范围四维过滤
- **动态 Config 编辑器**：树形层级、搜索定位、env 只读保护、.env 结构化编辑器
- **Threats 标签页**：Active Threats / Quarantine / Audit Log 三标签合并
- **YARA 批量操作**：跨页勾选、全选/清除、批量删除

### 变更
- 导航重构：6 项 → 5 项（Overview / Threats / Rules / Profiles / Settings）
- LIVE LOG 历史日志直接从 monitor.log 读取
- 页面工具栏回归内容区，header-center 预留给多站点选择器
- 画像 ID 仅用 UA+时间（不再依赖 URL 模式）
- URL 降级为画像 metadata，不参与聚类主键

### 修复
- 隔离管道 5 个关键 bug（异步竞态、原子写入缩进、file_size 时序等）
- HTMX `<script>` 不执行问题全面修复
- 6 个安全漏洞（认证绕过、路径穿越、信息泄露、速率限制）
- 通知批量聚合避免邮件轰炸

---

## [1.7.9] - 2026-06-25

### 新增
- 导航重构：6项→4项（Overview / Threats / Rules / Settings）
- Web 配置面板 + 动态 config.toml 编辑器 + 结构化 .env 编辑器
- Log Analyzer 全屏日志分析器，四维过滤
- System 管理弹窗 + Threats 标签页 + YARA 批量操作

### 变更
- LIVE LOG 从 monitor.log 读历史，页面工具栏回归内容区
- 启动 banner 去重，Settings 等高布局

### 修复
- HTMX script 不执行、Detail 遮罩残留、Audit 翻页参数、SSE buffer 损坏

---

## [1.7.9] - 2026-06-25

### 新增
- 文件自动隔离：`core/quarantine.py`，支持隔离/恢复/永久删除
- 递归 Webshell 扫描工具：`tools/recursive_webshell_scan.py`
- 威胁情报画像系统架构设计（`ThreatIntelligence` ABC + `AttackerProfile`）
- 三轨哈希引擎设计（ssdeep / py-tlsh / 内置 SimHash，graceful degradation）
- WAL 目录标准化方案（`wal/` / `threat_intel/` / `archives/`）
- 衰减引擎设计（`SimpleDecayEngine`，24h/0.5 / 72h/0.1）
- `RELEASE_NOTES_v1.7.9-cn.md` — 增量更新的发布说明草稿

### 变更
- 文件监控：目录验证缓存从 LRU(100) 升级为 Set + TTL，无容量上限
- 路径标准化：小写 + 正斜杠 + 绝对路径三统一（`utils/path_utils.py`）
- 路径别名映射：move 事件自动继承 TTL
- Config loader 换行符跨平台修复
- `.env` 敏感配置从 `config.toml` 分离

### 修复
- `dashboard.js` — Record Detail 弹窗不显示（`showRecordDetail()` 未定义）
- `core/quarantine.py` — 隔离失败 `FileNotFoundError` 优雅降级
- `core/suspicious_registry.py` — `PermissionError` 降级内存模式，避免崩溃

### 安全
- ~~V-001/V-002~~ — YARA 规则未授权读写（CRITICAL）— 已修复：所有 `/admin/yara/*` 路由加 `@require_auth`，抽取 `web/auth.py` 公共认证模块
- ~~V-003~~ — YARA 搜索未授权访问（HIGH）— 已修复：`/admin/yara/search` 加 `@require_auth`
- ~~V-004~~ — 路径穿越导致 500（MEDIUM）— 已修复：`_validate_rule_path()` 统一路径验证，拒绝 `..` 和 null byte 注入
- ~~V-005~~ — 服务器信息泄露（LOW）— 已修复：`factory.py` 移除 `Server` 响应头
- ~~V-006~~ — 登录无速率限制（LOW）— 已修复：内存级速率限制，每 IP 每分钟最多 5 次

---

## [1.7.8] - 2026-05-27

### 新增
- 模块化安装器架构：`scripts/install.py` 集中处理安装逻辑；`install.sh`/`install.bat` 为最小入口包装器
- 配置感知安装：读取现有 `config.toml`，提供保留 / 覆盖 / 审查 三种模式
- 启动脚本：前台/后台/停止/卸载全覆盖
- Systemd 服务模板，支持 Linux 开机自启
- 完整文档重构，含徽章、快速开始、故障排查
- 中英双语 CHANGELOG 与 RELEASE_NOTES

### 变更
- 零硬编码设计：安装脚本不再嵌入版本号，版本从 `config.toml` 经 `config/version.py` 级联
- `banner.txt` 包含版本与发布日期元数据
- `ci.yml` 工作流名称与当前版本同步

### 修复
- `install.bat` Python 检测重写，修复 Python 3.12 检测失败
- `install.sh` 按 python3 → python → py3 → py 顺序检测
- README-cn.md 完全重写至 v1.7.8 功能集

---

## [1.7.7] - 2026-05-26

### 新增
- 赛博朋克终端风格前端：暗色主题、霓虹绿强调色、Canvas 矩阵雨登录动画
- CSS/JS 模块化：6 个 CSS 文件 + 4 个 JS 文件
- WAL 高内聚迁移：全部 WAL 功能提取至 `core/wal_manager.py`
- 全站 CSRF 保护（Flask-WTF）
- Records 单列表 + 内联误报切换
- SSE 历史日志后端嵌入
- 零硬编码分页：所有分页参数从 `config.toml` 读取
- Records / YARA 批量操作
- 导航精简为 Dashboard / System / Account

### 变更
- 前端主题从浅色管理风格切换为赛博朋克暗色终端
- `suspicious_registry.py` 不再管理 WAL
- SSE 日志流改为服务端嵌入历史

### 修复
- innerHTML 替换导致的容器嵌套 bug
- 紧凑模式下 YARA 上传模态框不可用（移至全局作用域）
- HTMX POST 请求缺失 CSRF Token
- 多配置文件版本号不一致

### 安全
- 全站 CSRF 防护
- 管理后台 IP 白名单
- Scrypt 密码哈希 + 强度校验

---

## [1.7.6] - 2026-01-20

### 新增
- SSE 重构：原生 EventSource 替代 HTMX SSE 扩展
- 账户安全管理：密码修改 + 强度校验
- 系统管理四象限：Registry / WAL / Session / Config
- 幽灵目录检测（惰性缓存）
- `utils/sse_manager.py`：独立 SSE 推送管理器
- `utils/password_utils.py`：密码强度校验库
- `tools/ci_quick_validator.py`：CI 快速验证脚本

### 变更
- Metrics 面板从 SSE 改为 HTMX 轮询（10s 间隔）
- Registry 更新防抖 500ms

### 修复
- SSE 连接泄漏与重复刷新
- Session 认证边界情况
- 配置热加载持久化失败

---

## [1.7.5] - 2025-12

### 新增
- 幽灵目录检测（LRU 缓存，容量 100）
- 通配符日志路径：`**/access.log` 递归匹配
- Session 认证系统（文件系统后端）
- 三层智能告警：指数退避 + 自适应阈值

### 变更
- Windows 轮询优化：目录缓存 TTL

---

## [1.7.0] - 2025-11

### 新增
- HTMX 管理前端（零 Node.js 依赖）
- WAL 事务日志
- 三层告警：指数退避 + 自适应阈值
- 跨平台监控：Linux Inotify / Windows 轮询自适应切换
- YARA 规则引擎集成
- Webhook / 微信 / 邮件多通道告警

---

## [1.0.0] - 2025

### 新增
- 初始版本：文件系统监控 + 基础告警
