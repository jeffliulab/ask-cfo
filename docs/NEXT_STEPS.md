# 当前任务清单

> 按 [agent-rules / workflows/rapid-versioning.md](https://github.com/jeffliulab/agent-rules/blob/main/agent-rules/workflows/rapid-versioning.md) 轻量模式。
> 完整路线图见 [`.claude/plans/0-1-0-4-0-5-0-6-rag-agent-hidden-russell.md`](../.claude/plans/0-1-0-4-0-5-0-6-rag-agent-hidden-russell.md)（含 v0.1-v0.6 day-by-day）。
> 版本总览 → [`../VERSIONS.md`](../VERSIONS.md)；版本日志 → [`versions/`](versions/)。

## 当前状态

- ✅ **v0.1.0 已封版**（2026-04-25，git tag `v0.1.0`）—— 详见 [versions/v0.1.0-封版.md](versions/v0.1.0-封版.md)
- ⏳ **v0.2.0 凭证录入** —— 待 ack 启动；任务清单 + 日志 [versions/v0.2.0-开发中.md](versions/v0.2.0-开发中.md)；macro plan 见 [.claude/plans/](../.claude/plans/0-1-0-4-0-5-0-6-rag-agent-hidden-russell.md) §v0.2.0
- 全程 north star：不引入 vector DB / embedding（v0.1-v0.6 均不上）

## v0.2.0 概要（计划，未启动）

**模块**：凭证录入（bookkeeping）—— 拍发票 / 写一句业务说明 → AI 草拟会计分录 + 税务标记 + 准则引用

**关键技术决策**（v0.2 D1 启动时落地）：
- OCR provider：腾讯云 `VatInvoiceOCR` 主用 + GPT-4o vision fallback
- 凭证 schema：`VoucherDraftPayload(entries, summary, business_desc)` 必须 v0.2 release 前稳定（v0.4 SQLite 列结构来源 + v0.3 月结输入）
- 复用 v0.1 立下的契约：`routes/_dsp.py` / agent loop 模板 / `WorkspaceCard` discriminated union / workspaceStore namespace

**预期工期**：7 天（D1-D7）。详细任务清单见 plan 文件。

**新依赖**：`tencentcloud-sdk-python-ocr` / `python-multipart` / `Pillow` / `react-dropzone`

**Done 定义**：
- ≥50 backend tests（OCR adapter mock + agent flow + 编辑流）全绿
- 3 类发票端到端跑通（增值税专票 / 普票 / 餐饮票）
- `npm run build` 通 + 用户可在 `/bookkeeping` 拖入发票看到 voucher draft + tax risk + 引用卡片
- `git tag v0.2.0`

## 已完成

- ✅ 2026-04-24 Day 0 — Framework 从 fin-pilot v0.1.0 复制 + CFO 化适配
- ✅ 2026-04-25 Day 0.5 — 项目改名 ask-cfo + agent search 决策 + v0.1-v0.6 完整路线图锁定
- ✅ 2026-04-25 Day 1-7 — v0.1.0 法规问答完整实现 + 89 tests 全绿 + frontend 编译通过

## 阻塞

- 无

## v0.3+ 预告（不阻塞 v0.2）

| 版本 | 模块 | 核心 pattern | 工期 |
|---|---|---|---|
| v0.3 | 月结对账 | tool_use + heuristic + LLM 混合 | 7d |
| v0.4 | 财务报表 + SQLite | tool_use + drill-down | 7d |
| v0.5 | 报税申报 | sub-agents + plan-execute-reflect + LangGraph checkpoint | 12d |
| v0.6 | 多客户 + 长期记忆 | skill-based memory + journal + WorkflowAgent + MCP | 14d |
