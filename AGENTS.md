# Ask CFO — Agent 规则入口

本项目遵守 [`~/Local_Root/agent-rules/agent-rules/`](../agent-rules/agent-rules/) 的统一规范。

## 项目类型

**fullstack-app** —— 后端 FastAPI + 前端 Next.js。三栏 IDE 形态借鉴姐妹项目
[`fin-pilot`](https://github.com/jeffliulab/fin-pilot)（v0.1.0 commit `ac6f87c`）。

按 [`paths/fullstack-app.md`](../agent-rules/agent-rules/paths/fullstack-app.md) 阅读顺序：

1. [`GLOBAL.md`](../agent-rules/agent-rules/GLOBAL.md)
2. [`principles/architecture.md`](../agent-rules/agent-rules/principles/architecture.md)
3. [`principles/engineering.md`](../agent-rules/agent-rules/principles/engineering.md)
4. [`stacks/python-backend.md`](../agent-rules/agent-rules/stacks/python-backend.md)
5. [`stacks/frontend.md`](../agent-rules/agent-rules/stacks/frontend.md)
6. [`workflows/local-dev.md`](../agent-rules/agent-rules/workflows/local-dev.md) — 启动 dev server 必读（端口 + CORS）
7. [`workflows/git.md`](../agent-rules/agent-rules/workflows/git.md)
8. [`workflows/quality.md`](../agent-rules/agent-rules/workflows/quality.md)
9. [`workflows/rapid-versioning.md`](../agent-rules/agent-rules/workflows/rapid-versioning.md) — pre-1.0 轻量版本管理
10. [`workflows/github.md`](../agent-rules/agent-rules/workflows/github.md)（公开仓库）

## 项目专属约定

### 范围边界
- 本项目（Ask CFO）只做**财务**（记账 / 月结 / 报表 / 报税 / 法规问答）
- 投资 / 投研 / 行情 / 合规审查 → 姐妹项目 [`fin-pilot`](https://github.com/jeffliulab/fin-pilot)
- v0.1 候选优先级：**凭证录入 + 法规问答**（详见 docs/PRD.md §4）

### 技术栈（与 fin-pilot 共享 framework）
- 后端：FastAPI + Python 3.11+ + LangGraph + 4 LLM provider（anthropic / openai / deepseek / ollama）
- 前端：Next.js 14+ + TypeScript 严格 + Tailwind + shadcn/ui + Zustand + TanStack Query + Vercel AI SDK Data Stream Protocol（自写 hook 解析）
- LLM：CFO 场景**优先 DeepSeek**（中文 + 便宜），其次 Claude；通过 LLM_PROVIDER 切
- 数据库：v0.1 不引入（in-memory zustand）；v0.4 评估 SQLite

### 端口分配（启动 dev server 前必读）

按 [agent-rules / workflows/local-dev.md](../agent-rules/agent-rules/workflows/local-dev.md)。**绝不假设默认端口空闲**；**绝不 kill 别的项目的进程**。

| 服务 | 默认 | 探测段 | env 覆盖 |
|---|---|---|---|
| FastAPI backend | 8000 | 8000-8010 | `--port` flag |
| Next.js frontend | **3003** | 3003-3010（**跳过 3000/3001/3002**）| `npm run dev -- --port N` |

**用户保留段（macOS）—— 即使探测显示空闲也不许用**：

| 端口 | 占用方 | 说明 |
|---|---|---|
| 3000 | 长期挂在那的某 node 进程（外部）| 用户日常依赖；不许碰 |
| 3001 | 用户**另一个项目** | 偶发占用；不许碰 |
| 3002 | Code Helper（macOS 系统） | 不许碰 |

ask-cfo 的 frontend **从 3003 起步**。fin-pilot 同时也用 3000-3010 段，所以两边
联动跑时按 lsof + AGENTS.md 双重过滤后顺移，并把实际选定的 port 通过
`CORS_ORIGINS` / `NEXT_PUBLIC_API_URL` 同步配。

### 版本管理
- 当前版本：见 [`VERSIONS.md`](VERSIONS.md)
- 当前任务：[`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md)
- 当前开发日志：[`docs/versions/v0.2.0-开发中.md`](docs/versions/v0.2.0-开发中.md)（v0.1.0 已封版 → [`v0.1.0-封版.md`](docs/versions/v0.1.0-封版.md)）

### Git 流程
- Push 前必须问 "PR 还是直推 main？"（v0.1 单人开发倾向直推）
- Conventional Commits

### 文档语言
- 文件 / 目录英文优先
- 文档正文中文（简体）
- 代码 / commit / 标识符英文

## 关键文档索引

| 文档 | 用途 |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | 产品需求（CFO 5 模块取舍 + v0.1 优先级 + 待办决策） |
| [`docs/architecture.md`](docs/architecture.md) | 系统架构（三栏 + 数据流 + 三层） |
| [`docs/QUICKSTART.md`](docs/QUICKSTART.md) | 本地启动指南 |
| [`docs/SALVAGE_MAP.md`](docs/SALVAGE_MAP.md) | 旧仓库代码出处追溯（含 legacy/wencfo/）|
| [`legacy/wencfo/`](legacy/wencfo/) | 旧 wencfo 项目代码（仅参考，不维护） |
