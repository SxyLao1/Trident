# Trident v1.7.9 发布说明（草稿）

> **状态：🟢 v1.7.9-stable 已发布**  
> **发布日期：2026-06-25**

---

## 概述

v1.7.9 "Threat-Intel-Preview" 是威胁情报画像系统的首个预览版本。核心升级：引入攻击者画像（Attacker Profile）概念，以行为指纹替代 IP 作为聚类标识；新增三轨哈希引擎实现文件相似度分析；标准化 WAL 目录结构为 v2.0 存储层铺路。

---

## 新功能

### 威胁情报画像系统（设计中）

- [ ] `AttackerProfile` — 攻击者画像实体，基于行为指纹（UA + 文件簇 + 时间桶）聚类
- [ ] `IPReputation` / `FileReputation` — IP 信誉 + 文件信誉双表关联
- [ ] `ThreatIntelligence` ABC — 抽象接口，为 v2.0 架构预留

### 三轨哈希引擎（设计中）

- [ ] ssdeep（CTPH）— 精度最高，需 libfuzzy C 库
- [ ] py-tlsh（Trend Micro TLSH）— 纯 Python，零外部依赖风险
- [ ] 内置 SimHash — 零依赖，永不失败
- [ ] 安装时自动探测，运行时自动降级

### 衰减引擎（设计中）

- [ ] `SimpleDecayEngine` — 后台线程每 60 秒遍历全表
- [ ] 衰减公式：24h/0.5, 72h/0.1
- [ ] 过期策略：7 天内存移除，30 天 WAL 归档

### 文件隔离 ✅

- 新增 `core/quarantine.py` — 可疑文件自动/手动隔离
- 隔离文件移至 `data/quarantine/files/`，SQLite 记录元数据
- 管理后台：隔离列表 / 详情 / 恢复 / 永久删除

### 递归 Webshell 扫描工具 ✅

- 新增 `tools/recursive_webshell_scan.py`
- 指定目录递归扫描，YARA + 静态特征双重检测
- 生成扫描报告（路径 / 引擎 / 规则 / 得分）

### WAL 目录标准化（部分完成）

- [x] 设计标准化目录结构（`wal/` / `threat_intel/` / `archives/`）
- [ ] 实际迁移

---

## 改进

- 文件监控：目录验证缓存从 LRU(100) 升级为 Set + TTL，无容量上限
- 路径标准化：`utils/path_utils.py` — 小写 + 正斜杠 + 绝对路径三统一
- 路径别名映射：move 事件自动继承 TTL

---

## 修复

- `dashboard.js` — Record Detail 弹窗不显示（`showRecordDetail()` 未定义）
- `core/quarantine.py` — 隔离失败 FileNotFoundError 优雅降级
- `core/suspicious_registry.py` — PermissionError 降级内存模式，避免崩溃
- Config loader 换行符跨平台修复
- `.env` 敏感配置从 `config.toml` 分离

---

## 安全修复

> 来源：2026-06-24 渗透测试报告

- [x] V-001/V-002 — `/admin/yara/*` 路由未授权访问（加 `@login_required`）✅
- [x] V-003 — YARA 搜索未授权访问 ✅
- [x] V-004 — 路径穿越导致 500 / DoS ✅
- [x] V-005 — 服务器信息泄露（隐藏 Werkzeug/Python 版本）✅
- [x] V-006 — 登录无速率限制（内存级，5次/分钟/IP）✅

---

## 升级说明

从 v1.7.8 升级：

```bash
# 1. 拉取新版本
git checkout main && git pull

# 2. 同步依赖（三轨哈希新增）
pip install ssdeep  # 可选；失败自动降级 py-tlsh

# 3. 重新运行安装
python scripts/install.py
```

---

## 已知问题

- 画像系统仅完成架构设计，功能代码未实现
- notifier 仍按时间 batch 聚合（等画像系统完成后改为按画像聚合）
- Registry 内存模式重启后数据丢失（v2.0 通过 WAL 双写彻底解决）
- Werkzeug 开发服务器（v2.0 迁移到 Gunicorn）

---

*此文档随开发进度更新。所有 [ ] 项完成后，状态改为"就绪"并创建 GitHub Release。*
