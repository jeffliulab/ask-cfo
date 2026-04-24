# agent-as-a-cfo · 财务记账与报税 Agent

> 把 CFO 的日常工作 —— 记账、对账、报税、合规审查 —— 做成 Agent 工作流。

**定位**：面向中小企业 / 个体工商户的**财务自动化 Agent**。
**不做**：投资分析、研报、市场行情 —— 这些在姐妹项目 [`../fin-pilot/`](../fin-pilot/) 里。

## 来源

本项目由前身 5 个已封存（archived）GitHub 仓库中**财务相关**部分整合而来：

| 旧仓库（archived） | 贡献 |
|--------|------|
| [jeffliulab/wencfo](https://github.com/jeffliulab/wencfo) | 主体：`brain/`（LangGraph 多 Agent）+ `backend/`（FastAPI + 鉴权）+ `tax_service/`（Playwright 报税自动化） |
| [jeffliulab/financial_advisor](https://github.com/jeffliulab/financial_advisor) | 旧版 budget_planner 工具 + JWT 鉴权范式（参考） |
| [jeffliulab/cfoknows-system](https://github.com/jeffliulab/cfoknows-system) | .NET 10 + Azure AD B2C 后端架构参考（不主动维护） |

详见 [docs/SALVAGE_MAP.md](docs/SALVAGE_MAP.md)。

## 仓库结构

```
agent-as-a-cfo/
├── docs/                       规划文档
├── brain/                      LangGraph / LangChain 多 Agent 大脑（来自 wencfo）
│   └── app/                    FastAPI 入口、CORS、健康检查
├── backend/                    业务后端（来自 wencfo）：用户、鉴权、Alembic 迁移
│   └── app/
└── tax_service/                报税自动化微服务（来自 wencfo）
    └── app/services/           browser_tax_service / api_tax_service / factory
```

旧仓库的原始拷贝不在树内 —— 如需追溯原文件，去对应的 archived GitHub repo（详见 [docs/SALVAGE_MAP.md](docs/SALVAGE_MAP.md)）。

## 状态

🚧 早期脚手架。代码继承自 wencfo / financial_advisor，**尚未跑通也未做依赖收敛**。建议下一步：

1. 进入 `brain/`，跑通 LangGraph 最小 demo（一个工具：发票识别 OR 凭证录入）；
2. 评估 `tax_service/` 中浏览器自动化的可维护性 —— 国地税官网改版频繁，需要决定是 keep / fork / 重写；
3. 决定要不要把 `backend/` 与 `brain/` 合并（wencfo 的过度服务拆分曾是技术债来源）；
4. 写 PRD：明确目标用户（个体工商户？小微企业财务？外包代账公司？）。
