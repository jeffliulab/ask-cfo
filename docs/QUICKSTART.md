# agent-as-a-cfo v0.1.0 本地启动指南

> 第一次跑请按这个顺序来。需要：Python 3.11+ 和 Node 22+，以及一个 LLM
> provider 的 API key（CFO 场景推荐 DeepSeek）。

---

## 1. 后端：FastAPI

### 1.1 建虚拟环境

```bash
cd /path/to/agent-as-a-cfo
conda create -n agent-as-a-cfo python=3.11 -y
conda activate agent-as-a-cfo
```

> 如果已经在 fin-pilot 用过 conda，可以共用 env 节省磁盘 —— 两个项目依赖几乎重叠
> （除了 fin-pilot 多 akshare/yfinance）。但建议各自独立 env，按 agent-rules /
> GLOBAL.md 的"虚拟环境名 = 项目名"约定。

### 1.2 装依赖

```bash
pip install -e ".[dev]"
```

> 首次安装大约 1-2 分钟（fastapi + langgraph + 4 LLM SDK + pytest 等）。

### 1.3 配 .env

```bash
cp .env.example .env
# 编辑 .env，至少填一个 LLM provider key
```

最少需要的字段（任选一个 provider）：

```
# CFO 场景推荐：DeepSeek（中文好 + 最便宜）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxx

# 或：Anthropic Claude（reasoning 强，中文 OK）
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-xxx

# 或：OpenAI / ChatGPT
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-proj-xxx

# 或：本地 Ollama（无需 API key，需先 ollama pull qwen2.5:14b）
# LLM_PROVIDER=ollama
# OLLAMA_MODEL=qwen2.5:14b

# CORS
CORS_ORIGINS=http://localhost:3000
```

### 1.4 跑测试

```bash
pytest backend/tests/ -v
# 期望：17 passed（chat orchestrator + chat route + 4 provider stream paths）
```

### 1.5 启动 backend

```bash
uvicorn backend.main:app --reload --port 8000
```

> ⚠️ **端口规范**：按 [agent-rules / workflows/local-dev.md](https://github.com/jeffliulab/agent-rules)
> 的端口纪律，启动前先 `lsof -nP -iTCP:8000 -sTCP:LISTEN` 探测。如果 8000 被
> fin-pilot 占着，往后顺移到 8001-8010 + 同时改前端 `NEXT_PUBLIC_API_URL`。

打开 http://localhost:8000/docs 看 OpenAPI 文档；试试：

```bash
curl http://localhost:8000/healthz
# {"status":"ok","version":"0.1.0.dev"}
```

---

## 2. 前端：Next.js

新开一个终端（不要关 backend）：

### 2.1 装依赖

```bash
cd frontend
npm install
```

### 2.2 配 env

```bash
cp .env.example .env.local
# 默认 NEXT_PUBLIC_API_URL=http://localhost:8000，与 backend 默认端口对得上
```

### 2.3 启动 frontend

```bash
npm run dev
# Local: http://localhost:3000
```

> ⚠️ **端口规范**：同样先探测 :3000；被占就 `npm run dev -- --port 3001` +
> 把 3001 加到 backend 的 CORS_ORIGINS 里（通过启动时 env 覆盖，不改 .env）。

---

## 3. 试试

1. 浏览器打开 http://localhost:3000 —— 自动重定向到 `/bookkeeping`（占位页）
2. 左菜单可见 5 个模块：
   - **凭证录入** ⭐（active，目前是占位页）
   - 月结对账 / 财务报表 / 报税申报（disabled，标 v0.2 / v0.3 / v0.4）
   - **法规问答** ⭐（active，目前是占位页）
3. 右栏 ChatPanel 输入框 disabled —— 因为还没实现具体的 workspace 数据流
   （v0.1 待 PRD 决策 A + B 之后实施）
4. 仅可演示形态：三栏布局 / Citation Drawer 框架 / chat 后端 streaming（curl 可测）

要让 chat 真跑起来：

```bash
curl -sS -N http://localhost:8000/api/v1/chat/stream \
  -X POST -H "Content-Type: application/json" \
  -d '{"message":"用一句话解释什么是进项税额","cards":[],"citations":[]}' \
  -w "\n[HTTP %{http_code}]\n"
# 应看到 0:"text" 流 + d:{...} finish part
```

---

## 4. 常见问题

**backend 报 `DEEPSEEK_API_KEY 未设置（LLM_PROVIDER=deepseek）`**
→ `.env` 没填 / 没在虚拟环境里跑。

**前端报 `网络请求失败`**
→ backend 没起来，或端口冲突。`curl http://localhost:8000/healthz` 看 backend
   是否响应。如果改了 backend 端口，记得改 `frontend/.env.local` 的
   `NEXT_PUBLIC_API_URL`。

**端口被 fin-pilot 占着**
→ 用 `lsof -nP -iTCP:<port> -sTCP:LISTEN` 探测，按 8000-8010 / 3000-3010 探测段
   找空闲；启动时通过 env / CLI flag 覆盖默认值。详见 [agent-rules /
   workflows/local-dev.md](https://github.com/jeffliulab/agent-rules)。

---

## 5. 想跑跑代码 / 改改东西？

- 后端三层：[`backend/routes/`](../backend/routes/) → [`backend/services/`](../backend/services/) → [`backend/repositories/`](../backend/repositories/)
- 前端组件：[`frontend/src/components/`](../frontend/src/components/)
- 前端业务（待开发）：[`frontend/src/features/`](../frontend/src/features/)
- v0.1 实施前必读 [`docs/PRD.md`](PRD.md) 决策 A + B
- 后续 v0.2+ 路线图见 [`../VERSIONS.md`](../VERSIONS.md)。
