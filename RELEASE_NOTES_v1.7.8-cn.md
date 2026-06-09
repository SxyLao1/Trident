# Trident v1.7.8 — 发行说明

**发布日期**：2026-05-27  
**状态**：生产就绪

---

## 发布亮点

v1.7.8 在 v1.7.7 功能基础上完成工程化增强，新增模块化安装器、后台启动脚本及完整双语文档。

### 对用户
- Linux/macOS/Windows 一键安装脚本 — 自动检测 Python、创建 venv、安装依赖
- 配置感知安装：保留 / 覆盖 / 审查 现有配置
- 前台/后台启动脚本，支持基于 PID 的优雅停止
- 卸载脚本清理 venv 和数据，保留 config.toml 和日志

### 对开发者
- 安装逻辑全部集中到 `scripts/install.py`；shell/bat 包装器跨版本无需改动
- 版本零硬编码：`config.toml` → `config/version.py` → 全项目级联
- CI/CD 多平台矩阵 + 兼容性测试 + 工具验证
- Docker 多阶段构建，带健康检查端点

---

## 安装

### Linux / macOS / WSL
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

### Docker
```bash
docker-compose up -d
```

---

## 验证清单

- [ ] 登录页显示矩阵雨动画
- [ ] Dashboard 加载四象限（Metrics / Log Stream / YARA / Records）
- [ ] Records 显示正确的文件名、时间、规则、通信次数
- [ ] YARA 卡片可滚动查看所有规则
- [ ] YARA Upload 按钮打开模态框，支持拖拽/选择文件
- [ ] 每规则都有 Edit/Delete 按钮
- [ ] LIVE LOG STREAM 显示历史日志
- [ ] SSE 追加新日志不覆盖历史
- [ ] Records False Pos 按钮标记误报，变为 Cancel FP
- [ ] Records 分页 Prev/Next/跳转工作正常
- [ ] Records 搜索后分页保留参数
- [ ] System Management 四象限数据正常加载
- [ ] WAL Replay 点击后正常重放
- [ ] Session Cleanup 后正常刷新
- [ ] Config Reload 后配置热加载生效
- [ ] 刷新按钮刷新当前页面
- [ ] 移动端侧边栏能展开/收起
- [ ] 登录页 FX 开关可关闭矩阵雨
- [ ] 修改密码拒绝弱密码
- [ ] 开放健康检查 `/api/v1/health` 返回 `{"status": "healthy"}`
- [ ] 登录后健康检查 `/admin/health` 返回完整诊断信息

---

## 已知问题

| 问题 | 严重度 | 变通方案 | 修复目标 |
|------|--------|----------|----------|
| 紧凑模式下批量操作隐藏 | 低 | 使用完整 Records 页面 | v1.7.9 |
| SSE 历史限制 1000 条 | 低 | 增加缓冲区轮转 | v1.7.9 |
| WAL 归档仅显示无下载 | 低 | 从 `data/` 手动下载 | v1.7.9 |
| Windows 后台 PID 过期 | 低 | 任务管理器回退 | v1.7.9 |

---

## 安全提示

- 生产环境务必更换默认 `secret_key`
- 默认 `allowed_ips` 为 `["127.0.0.1"]` — 可扩展至 LAN 网段供团队使用
- 首次使用前运行 `python tools/admin_passwd.py` 生成强密码哈希
- 公网暴露时启用 HTTPS
- 版本号不在登录页或未认证端点暴露
