# Ask CFO 版本总览

> 按 [agent-rules / workflows/rapid-versioning.md](https://github.com/jeffliulab/agent-rules) 的 pre-1.0 轻量模式。
> 详细任务清单见 [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md)。每个版本的开发日志见 [`docs/versions/`](docs/versions/)。

## 当前开发

```
（v0.1.0 已封版于 2026-04-25；v0.2.0 凭证录入待 ack 启动）
v0.2.0   凭证录入：拍发票 → OCR → AI 草拟分录 + 准则引用 + 税务标记
         OCR provider：腾讯云 + GPT-4o vision fallback
         开始日期：待 ack
```

## 计划中

> 路线图于 2026-04-25 锁定，详见 [完整执行计划](../../.claude/plans/0-1-0-4-0-5-0-6-rag-agent-hidden-russell.md)。
> 全程不引入 vector DB / embedding，v0.5/v0.6 用现代 agent 方法（sub-agents / plan-execute-reflect / skill-based memory / MCP）。

```
v0.2.0P  凭证录入（拍发票 → OCR → AI 草拟分录 + 准则引用 + 税务标记）        7d
         OCR：腾讯云 + GPT-4o vision fallback
v0.3.0P  月结对账（试算平衡 + 4 类异常检测 + 期末结转）                       7d
v0.4.0P  财务报表（三表 + 多期对比 + 比率）+ SQLite 持久化（4 张表）          7d
         凭证 / 科目 / 申报记录占位 / agent 审计日志
v0.5.0P  报税申报（agentic）：sub-agents per tax type + plan-execute-reflect 12d
         + LangGraph checkpointing；computer-use L2 stretch
v0.6.0P  多客户 + 长期记忆：skill-based memory + per-client journal           14d
         + WorkflowAgent + 2 个 MCP servers（regulations / tax_calc）
v0.7.0P  Citation drawer PDF.js 高亮 + Docker 化 + 部署演示站点
v1.0.0P  开源发布 + 文档站 + 第一批用户（升级到 versioning.md 完整规范）
```

## 已完成

```
v0.1.0   全栈骨架 + 法规问答 MVP（agent search 方案）
         BM25 keyword + LLM tool_use 多轮（max 4 + 强制收尾），不引入 embedding / vector DB
         10 条种子条款覆盖增值税 / 企业所得税 / 个税 / CAS
         前端三栏 + AgentTrace 折叠面板 + RegulationSnippetCard + Citation Drawer
         89 backend tests + npm run build 通；/regulations 路由 first-load 105 KB
         归档日期：2026-04-25
         git tag：v0.1.0
         开发日志：docs/versions/v0.1.0.md
```

---

**版本号约定**：`v0.{MINOR}.{PATCH}` SemVer，pre-1.0 阶段 MINOR bump 即一个阶段。
**与 fin-pilot 关系**：framework 壳子从 fin-pilot v0.1.0 (commit `ac6f87c`) 复制；
两个项目独立演进，未来如果共享代码超过 2-3 处再考虑抽 npm/pip 包。
