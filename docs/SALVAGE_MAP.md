# Salvage Map — 旧仓库 → agent-as-a-cfo

记录 2026-04-24 从 5 个已封存的旧 GitHub 仓库中搬运了哪些"财务"相关资产。
原始仓库均已 archived 但仍可公开只读访问，需要追溯直接去 GitHub 看：

- https://github.com/jeffliulab/wencfo *(archived)*
- https://github.com/jeffliulab/financial_advisor *(archived)*
- https://github.com/jeffliulab/cfoknows-system *(archived)*

## 当前位置

> 2026-04-24 Day 0：原 `brain/` `backend/` `tax_service/` 三个目录从根目录
> `git mv` 到 `legacy/wencfo/`（参考用，**不维护**），给 fin-pilot 复制过来的
> 全栈 framework（v0.1.0 commit ac6f87c）让位。

### `legacy/wencfo/brain/` ← 原 `wencfo/brain/`
- `app/main.py` —— FastAPI lifespan、CORS、健康检查脚手架
- `requirements.txt` —— LangChain / LangGraph / OpenAI / pypdf2 / python-docx
- **复用价值**：v0.5+ 真做 RAG 时参考 `pypdf2/python-docx` PDF 解析

### `legacy/wencfo/backend/` ← 原 `wencfo/backend/`
- `app/` —— DB 模型、用户体系、鉴权（python-jose / passlib）、用户上下文中间件
- Alembic 迁移、Pydantic v2、SQLAlchemy ORM
- **复用价值**：v0.4 引入持久化 + v0.6 多用户/代账权限隔离时参考鉴权范式

### `legacy/wencfo/tax_service/` ← 原 `wencfo/tax_service/`
- `app/services/`：
  - `base_tax_service.py` —— 抽象基类
  - `browser_tax_service.py` —— Playwright / Selenium 浏览器自动化（应对国地税官网）
  - `api_tax_service.py` —— 直连 API 实现
  - `tax_service_factory.py` —— 工厂模式按地区/税种切换
- `app/api/v1/api.py` —— REST 接口
- 依赖：Playwright + Celery + openpyxl/xlsxwriter
- **复用价值**：v0.4 报税申报模块的核心参考（国地税电子税务局自动化）

## 曾经一度保留、现已删除的参考资产

最初一并搬过来一份 `salvaged/` 缓冲目录，2026-04-24 当天清理掉 ——
理念已抽到主代码 + 本文档；要看原始文件去 archived GitHub repo 即可。当时保留过的内容：

- `wencfo_extras/`：原 `wencfo/{database,nginx,scripts,docs}` —— Postgres 初始化、nginx 配置、部署脚本、设计文档
- `financial_advisor/`：原 `financial_advisor/{server,brain}` —— JWT 鉴权、FastAPI 聊天端点、`budget_planner.py`（如需 budget 逻辑去原 repo 拿）
- `cfoknows_dotnet/`：完整 .NET 10 工程 —— DI / EF migrations / Azure Blob / Azure AD B2C 样板

## 不与"金融"混淆

下列内容已留在 `../fin-pilot/`，不属于本项目：

- 行情 / 新闻 / 研报 / 投资分析（来自 `AI_Financial_Advisor`）
- OpenManus 通用 Agent 框架（来自 `Financial_Agent_Try`）

如未来需要把"投资类财务规划"做进 CFO 工作流，请考虑在 `fin-pilot` 里以 module 形式开放，而不是把市场数据塞回这里。
