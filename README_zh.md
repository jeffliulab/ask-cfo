# Ask CFO · 财务版 Cursor

> 借鉴姐妹项目 [`fin-pilot`](https://github.com/jeffliulab/fin-pilot)（同一形态做金融分析师工具）
> 已验证的"三栏 AI 工作台"形态，让财务人员的凭证 / 月结 / 报税 / 法规检索日常被 AI 加速。

> 🇬🇧 English README → [`README.md`](README.md)

## 是什么

面向**中国小微企业 / 个体工商户 / 代账机构**的全栈 AI 财务工作台。v0.x roadmap 5 模块：

| # | 模块 | v0.1 状态 |
|---|------|---|
| 1 | **凭证录入** —— 上传发票 / 银行流水 → AI 草拟会计分录 + 引用准则原文 | ⭐ v0.1 候选 |
| 2 | **法规问答** —— RAG 检索税法 / 会计准则 / 国税总局公告，Citation drawer 抽屉打开原文 PDF | ⭐ v0.1 候选 |
| 3 | 月结对账 —— 凭证审核 + 试算平衡 + 期末结转 | v0.2 |
| 4 | 财务报表 —— 三大报表 + 多期对比 + 关键比率 | v0.3 |
| 5 | 报税申报 —— 增值税 / 企业所得税 / 个税自动计算 + 预填表 | v0.4 |

详见 [docs/PRD.md](docs/PRD.md)，含 OCR / 法规 RAG 数据源调研 + **6 个待你拍板的决策**。

## 为什么三栏

沿用 fin-pilot 已验证的形态：
- **Workspace 一等公民**，对话只是触发器
- **引用即抽屉**：点 [N] 角标 → 右抽屉打开**法规原文 PDF**，不离开当前页
- **CFO 场景这条价值翻倍** —— 财务每天都要查"这条政策怎么说"，金融人偶尔查

## 技术栈（与 fin-pilot 共享）

- **后端**：FastAPI + Python 3.11 + LangGraph + 4 LLM provider 矩阵
- **前端**：Next.js 14 + TypeScript 严格 + Tailwind + shadcn/ui + Zustand + Vercel AI SDK
- **LLM**：CFO 场景**首选 DeepSeek**（中文 + 便宜），可切 Claude / GPT / Ollama
- **存储**：v0.1 in-memory；v0.4 引入 SQLite

## 仓库结构

```
ask-cfo/
├── AGENTS.md / CLAUDE.md         agent 规则入口
├── VERSIONS.md                   版本总览（rapid-versioning）
├── README.md / README_zh.md      英文 / 中文
├── pyproject.toml                后端依赖
├── .env.example                  所需 env（LLM_PROVIDER + key）
├── docs/
│   ├── PRD.md                    ⭐ 产品需求 + 6 个待你拍板的决策
│   ├── architecture.md           三栏架构 + 数据流
│   ├── QUICKSTART.md             本地启动指南
│   ├── NEXT_STEPS.md             当前 v0.1 任务清单
│   ├── SALVAGE_MAP.md            wencfo 旧代码出处追溯
│   └── versions/v0.1.0-封版.md   v0.1 开发日志（已封版）
├── backend/                      FastAPI 三层（routes/services/repositories）
├── frontend/                     Next.js 5 模块占位页 + 三栏壳
└── legacy/wencfo/                旧 wencfo 工程（参考用，不维护）
```

## 状态

🚧 **v0.1.0 开发中**（2026-04-24 启动）。Framework 壳子从 fin-pilot v0.1.0
（commit `ac6f87c`）复制；CFO 业务模块设计中（详见
[docs/PRD.md §9](docs/PRD.md) 的 6 个待你拍板的决策，主要是 v0.1 先做哪个模块）。

## 快速开始

详细步骤见 [docs/QUICKSTART.md](docs/QUICKSTART.md)。TL;DR：

```bash
# 后端
conda create -n ask-cfo python=3.11 -y && conda activate ask-cfo
pip install -e ".[dev]"
cp .env.example .env  # 填 LLM_PROVIDER + 对应 key（CFO 推荐 DeepSeek）
uvicorn backend.main:app --reload --port 8000

# 前端（另一个终端）
cd frontend && npm install
cp .env.example .env.local
npm run dev  # http://localhost:3000
```

然后浏览器开 http://localhost:3000 → 默认跳到 `/bookkeeping`（占位页）。
v0.1 模块实施待 PRD 决策 A + B（先做哪个）。

## License

待定。
