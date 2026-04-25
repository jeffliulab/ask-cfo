# v0.1.0 任务清单

> 按 [agent-rules / workflows/rapid-versioning.md](https://github.com/jeffliulab/agent-rules) 的轻量模式。
> 完成的勾上 `[x]`，新发现的任务即时追加。版本总览见 [`../VERSIONS.md`](../VERSIONS.md)。

## 进行中

### Day 0 — Framework 复制 + 初版规划（2026-04-24 完成）

- [x] 把 wencfo 旧代码（brain / backend / tax_service）移到 `legacy/wencfo/` 作参考
- [x] 从 fin-pilot v0.1.0 (commit `ac6f87c`) 复制全栈骨架（rsync 选择性复制，剔除 stock 专属）
- [x] 适配 backend：`interfaces.py` 改为 generic（Citation + WorkspaceCard + DataSourceError），`config.py` 删 StockDataSettings，`main.py` 注销 stock router，chat orchestrator 的 prompt path 改 `data/prompts/chat/`
- [x] 写 CFO 版 chat prompt：`system_prompt.j2`（CFO 助手身份、引用 [N] 强制、不出投资建议）+ `follow_up.j2`（generic cards JSON 注入）
- [x] 适配 frontend：`LeftMenu` 改为 5 个 CFO 模块（凭证 / 月结 / 报表 / 报税 / 法规问答；凭证 + 法规 active，其他 disabled），`app/page.tsx` 重定向 `/bookkeeping`，5 个模块占位页，`workspaceStore` / `types/workspace.ts` 改为 generic placeholder
- [x] 适配 root：`pyproject.toml` 改名 `agent-as-a-cfo`，删 akshare/yfinance；`.env.example` 加 OCR / RAG 占位字段
- [x] 写文档：`AGENTS.md`、`VERSIONS.md`、`docs/PRD.md`（CFO 域 5 模块 + 6 个待你定决策）、`docs/architecture.md`、`docs/QUICKSTART.md`、`docs/NEXT_STEPS.md`、`docs/versions/v0.1.0.md`、`README.md` 双语
- [x] 测试：17 backend tests 全绿（chat orchestrator + chat route + 协议编码，与 fin-pilot 一致）；frontend `npm run build` 通（6 个静态路由）

### Day 1+ — v0.1 模块开发（待用户决策）

> ⚠️ **阻塞 PRD §9 的 6 个决策**。最关键 2 个：
>
> **A. v0.1 做几个模块？**（1 个 vs 2 个）
> **B. 先做哪个？**（凭证录入 vs 法规问答）
>
> 我推荐：**先做"法规问答"**，理由：
> 1. 不需要 OCR provider 决策，依赖更少
> 2. RAG 流程通了之后，凭证录入复用同一套引用机制
> 3. 演示效果最直接（输入问题 → 答案 + 角标 → 抽屉看法规原文，30 秒可演完）
> 4. 凭证录入的"准则依据卡"本质上是法规问答的子集

待你 ack 之后，Day 1+ 任务展开为：

#### 如果先做"法规问答"（推荐）
- [ ] **决策 D**：选法规数据源（建议起手手工 30-50 条种子数据 + 财政部/税总公告 PDF 链接）
- [ ] 选 embedding model（推荐 BGE-large-zh，开源 + 中文专用）
- [ ] 选 vector store（推荐 chromadb，本地零运维）
- [ ] backend：写 `services/regulatory/regulation_search.py`（RAG）+ `routes/regulations.py`
- [ ] backend：写 `repositories/regulations/{seed_loader,vector_store}.py`
- [ ] frontend：`features/regulations/{QueryInput,ResultsView}.tsx`
- [ ] frontend：写 `RegulationSnippetCard.tsx` 组件
- [ ] frontend：法规问答页面接通 store + chat
- [ ] 端到端：用户问 → 检索 → 渲染卡片 → chat 追问 → 点 [N] 看原文

#### 如果先做"凭证录入"
- [ ] **决策 C**：选 OCR provider（推荐腾讯云 OCR 起手）
- [ ] **决策 D**：法规数据源（同上，但凭证场景对法规依赖更深）
- [ ] backend：`services/bookkeeping/{voucher_drafter, ocr_adapter}.py`
- [ ] backend：`routes/bookkeeping.py`
- [ ] frontend：拖拽上传 / 粘贴截图组件
- [ ] frontend：`VoucherDraftCard.tsx`
- [ ] 端到端：上传 → OCR → AI 草拟分录 → 用户确认（v0.1 仅显示，不入库）

## 已完成

（v0.1 模块未启动；Day 0 framework 已完成）

## 阻塞

- [ ] **PRD §9 的决策 A + B**（v0.1 模块数 + 优先级）—— **最高优先级，等你 ack**
