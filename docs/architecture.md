# agent-as-a-cfo 系统架构

> Framework 壳子从 fin-pilot v0.1.0（commit `ac6f87c`）复制 —— 三层 backend
> + 三栏 frontend + LangGraph 单 agent 编排 + Vercel AI SDK Data Stream
> Protocol。本文是 CFO 视角的描述。

---

## 1. 整体形态（与 fin-pilot 一致）

```
┌────────────────────────────────────────────────────────────────────┐
│                          浏览器（localhost:3000）                    │
│  ┌──────────┬──────────────────────────────┬──────────────┐        │
│  │ LeftMenu │      WorkspaceCanvas          │  ChatPanel   │        │
│  │          │   ┌──────────────────────┐   │              │        │
│  │ 凭证 ⭐  │   │ VoucherDraftCard     │   │ 输入问题     │        │
│  │ 月结 v0.2│   │ AccountingPolicyCard │   │ 流式输出     │        │
│  │ 报表 v0.3│   │ TaxRiskCard          │   │ + [N] 角标   │        │
│  │ 报税 v0.4│   │ RegulationSnippetCard│   │              │        │
│  │ 法规 ⭐  │   │                      │   │              │        │
│  └──────────┴──────────────────────────────┴──────────────┘        │
│                          │                  │                      │
│                CitationDrawer (右侧抽出，加载法规 PDF)              │
└─────────────────────┬─────────────────────────┬────────────────────┘
                      │                         │
            REST + SSE (Vercel AI SDK)         │
                      │                         │
┌─────────────────────▼─────────────────────────▼────────────────────┐
│                    后端（FastAPI on localhost:8000）                 │
│  ┌──────────┐ ┌────────────────┐ ┌─────────────────────────┐       │
│  │ routes/  │→│ services/      │→│ repositories/            │       │
│  │  chat    │ │  chat (LangGraph)│ │  invoices/              │       │
│  │  health  │ │  bookkeeping ⏳│ │  regulations/            │       │
│  │  ...     │ │  regulatory ⏳ │ │  (各模块 v0.1+ 实现)     │       │
│  └──────────┘ └────────────────┘ └─────────────────────────┘       │
│                       │                       │                    │
│                       ▼                       ▼                    │
│                  ┌─────────┐            ┌──────────┐               │
│                  │  llm/   │            │ 外部数据源 │               │
│                  │ Claude  │            │ OCR API   │               │
│                  │ DeepSeek│            │ 法规 RAG  │               │
│                  │ OpenAI  │            │ 国税系统   │               │
│                  │ Ollama  │            └──────────┘               │
│                  └─────────┘                                       │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. 前端架构

### 2.1 目录布局

```
frontend/
├── src/
│   ├── app/                     # 路由 + 布局
│   │   ├── layout.tsx           # ThreePaneLayout 根布局
│   │   ├── page.tsx             # 重定向 → /bookkeeping
│   │   ├── bookkeeping/page.tsx # 凭证录入（v0.1 候选）
│   │   ├── regulations/page.tsx # 法规问答（v0.1 候选）
│   │   ├── month-end/page.tsx   # 月结对账（v0.2）
│   │   ├── reports/page.tsx     # 财务报表（v0.3）
│   │   └── tax-filing/page.tsx  # 报税申报（v0.4）
│   ├── components/              # 纯展示
│   │   ├── ui/                  # shadcn/ui
│   │   ├── ThreePaneLayout.tsx
│   │   ├── LeftMenu.tsx         # 5 模块菜单
│   │   ├── WorkspaceCanvas.tsx
│   │   ├── ChatPanel.tsx
│   │   └── CitationDrawer.tsx
│   ├── features/                # 业务（v0.1 待开发）
│   │   ├── chat/ChatStream.tsx  # 已就位
│   │   ├── bookkeeping/         # 待开发
│   │   └── regulations/         # 待开发
│   ├── hooks/useChatStream.ts
│   ├── services/apiClient.ts
│   ├── stores/                  # zustand
│   │   ├── workspaceStore.ts    # generic placeholder
│   │   └── citationStore.ts
│   └── types/                   # 与 backend 对齐
│       ├── citation.ts / chat.ts / workspace.ts
└── ...
```

### 2.2 关键交互流

1. 用户在 LeftMenu 选模块（凭证 / 法规 ...）→ 对应 page.tsx 渲染
2. 模块特定输入（如凭证：拖发票；法规：自然语言查询）→ 调对应 service API
3. backend 处理 → 返回 `WorkspaceCard[]` → 写入 `workspaceStore`
4. `WorkspaceCanvas` 订阅 store → 按 `card_type` 渲染对应组件
5. 用户在 `ChatPanel` 追问 → `useChatStream` 发 POST 到 `/api/v1/chat/stream`
6. SSE 流回，识别 `[N]` 角标 → CitationLabel button
7. 点 `[N]` → `citationStore.open(citation)` → `CitationDrawer` iframe 加载原文

---

## 3. 后端架构

### 3.1 目录布局

```
backend/
├── main.py                      # FastAPI app + lifespan + CORS
├── config.py                    # pydantic-settings；LLM + API config
├── constants.py                 # 数据源 endpoint、超时、卡片类型枚举
├── interfaces.py                # Citation + WorkspaceCard + DataSourceError
├── routes/                      # 表现层
│   ├── chat.py                  # /api/v1/chat/stream（共享）
│   ├── health.py                # /healthz
│   └── _schemas.py              # Pydantic 响应模型
├── services/
│   ├── chat/orchestrator.py     # LangGraph + 4 provider streaming
│   ├── bookkeeping/             # v0.1+ 待开发
│   └── regulatory/              # v0.1+ 待开发
├── repositories/
│   ├── invoices/                # v0.1+ OCR adapter
│   └── regulations/             # v0.1+ RAG adapter
├── llm/                         # 4 provider 抽象（与 fin-pilot 共享）
├── data/prompts/
│   └── chat/                    # CFO 版 system_prompt + follow_up
└── tests/
    ├── test_chat_orchestrator.py
    └── test_chat_route.py
```

### 3.2 三层职责

| 层 | 职责 | 禁止 |
|---|---|---|
| `routes/` | Pydantic 参数校验、调 service、JSON / SSE 响应 | 写业务逻辑 |
| `services/` | 核心业务（凭证拼装 / RAG 检索 / 报税计算 / chat 编排） | 感知 HTTP |
| `repositories/` | 数据 CRUD、外部 API（OCR / 法规库 / 国税系统） | 业务判断 |

### 3.3 LLM Orchestration

`services/chat/orchestrator.py` 用 **LangGraph** 单节点 graph（`prepare`
渲染 prompts），streaming 走各 provider 原生 SDK：

- `anthropic.AsyncAnthropic` for Claude
- `openai.AsyncOpenAI` for OpenAI / DeepSeek（OpenAI 兼容协议）
- `httpx.AsyncClient` for Ollama（NDJSON）

新 provider = orchestrator 加 `_stream_<provider>` 方法 + 注册到 `__init__`
分支，~50 行；不动 routes / services 上层。

---

## 4. 配置 + 运行（v0.1）

### 4.1 必须的 env

```
LLM_PROVIDER=deepseek                  # 或 anthropic / openai / ollama
DEEPSEEK_API_KEY=sk-xxx                # 对应 provider 的 key
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

CFO 模块特定 env（v0.1 待选定）：
```
# OCR provider
TENCENT_OCR_SECRET_ID=
TENCENT_OCR_SECRET_KEY=

# 法规 RAG 数据源
REGULATIONS_DB_PATH=./data/regulations.db
QDRANT_URL=
```

### 4.2 启动

```bash
# 后端（终端 A）
conda activate agent-as-a-cfo
uvicorn backend.main:app --reload --port 8000

# 前端（终端 B）
cd frontend && npm run dev   # localhost:3000
```

按 [agent-rules / workflows/local-dev.md](https://github.com/jeffliulab/agent-rules)
的端口纪律：先 `lsof` 探测，被占则按段顺移并通过 env 覆盖。

---

## 5. v0.1 不在架构内的（明确 punt）

- 用户认证 / RBAC / 多租户 / 代账机构权限隔离 → v0.6
- 数据库（SQLite）→ v0.4 引入工作区持久化时
- 真 RAG 向量库 → v0.5（v0.1 用简单 retrieval）
- 行业 / 报税自动化的国税系统对接 → v0.4 + 法律咨询完成后

详细推迟原因见 [PRD.md §5](PRD.md)。

---

## 6. 与 fin-pilot 的代码共享路线

**v0.1**：各自维护 framework，差异点 manual sync。
**v0.4+**：UI primitives 真稳定后，抽 `agent-shell-ui` (npm) +
`agent-llm-providers` (pip) 共享包；两边 `pip install` / `npm install` 引入。
**v1.0**：考虑 monorepo（pnpm workspace）或 git submodule 统一管理。
