# agent-as-a-cfo — Cursor for Accountants & CFOs

> "财务版 Cursor" — three-pane AI workspace for bookkeeping, month-end close,
> tax filing, and regulation lookup. Borrows the proven UI shell from
> sibling project [`fin-pilot`](https://github.com/jeffliulab/fin-pilot)
> (which is the same form for financial market analysts).

> 🇨🇳 中文版 README → [`README_zh.md`](README_zh.md)

## What it is

Fullstack AI copilot (FastAPI + Next.js) for Chinese small businesses,
sole proprietors, and bookkeeping firms. 5 modules in v0.x roadmap:

| # | Module | v0.1 status |
|---|---|---|
| 1 | **凭证录入** (Bookkeeping) — invoice → AI voucher draft + accounting standard citations | ⭐ v0.1 candidate |
| 2 | **法规问答** (Regulations) — RAG search over tax law / accounting standards / official notices, citation drawer opens original PDF | ⭐ v0.1 candidate |
| 3 | 月结对账 (Month-end close) — voucher review + trial balance + period-end transfers | v0.2 |
| 4 | 财务报表 (Reports) — 3 statements + multi-period comparison + key ratios | v0.3 |
| 5 | 报税申报 (Tax filing) — VAT / corporate income tax / personal income tax auto-calc + pre-fill forms | v0.4 |

See [docs/PRD.md](docs/PRD.md) for design rationale, OCR/RAG provider
research, and the **6 open decisions** awaiting user input before v0.1
implementation kickoff.

## Why three-pane

Same as fin-pilot: workspace as first-class citizen, chat as trigger,
citations open as side drawers without leaving the page. CFO scenario
makes the citation pattern even more valuable — accountants need to
look up "what does the regulation actually say" multiple times per day.

## Tech stack (shared with fin-pilot)

- **Backend**: FastAPI + Python 3.11 + LangGraph + 4 LLM providers
  (anthropic / openai / deepseek / ollama)
- **Frontend**: Next.js 14 + TypeScript strict + Tailwind + shadcn/ui +
  Zustand + TanStack Query + Vercel AI SDK Data Stream Protocol
- **LLM**: DeepSeek recommended for CFO (Chinese + cheap), Claude / GPT
  via env switch
- **Storage**: in-memory in v0.1; SQLite in v0.4

## Repo layout

```
agent-as-a-cfo/
├── AGENTS.md / CLAUDE.md         agent rules entry
├── VERSIONS.md                   version overview (rapid-versioning)
├── README.md / README_zh.md      English / Chinese
├── pyproject.toml                backend deps
├── .env.example                  required env keys (LLM_PROVIDER + key)
├── docs/
│   ├── PRD.md                    ⭐ product requirements + open decisions
│   ├── architecture.md           three-pane + data flow
│   ├── QUICKSTART.md             local setup walkthrough
│   ├── NEXT_STEPS.md             current v0.1 task list
│   ├── SALVAGE_MAP.md            old wencfo code provenance
│   └── versions/v0.1.0.md        per-version dev log
├── backend/                      FastAPI three-layer (routes/services/repositories)
├── frontend/                     Next.js shell with 5 module pages
└── legacy/wencfo/                old wencfo project (reference, not maintained)
```

## Status

🚧 **v0.1.0 in development** (started 2026-04-24). Framework shell
copied from fin-pilot v0.1.0 (commit `ac6f87c`); CFO business modules
to be designed (see [docs/PRD.md §9](docs/PRD.md) for the 6 open
decisions blocking Day 1 implementation).

## Quick start

See [docs/QUICKSTART.md](docs/QUICKSTART.md). TL;DR:

```bash
# Backend
conda create -n agent-as-a-cfo python=3.11 -y && conda activate agent-as-a-cfo
pip install -e ".[dev]"
cp .env.example .env  # set LLM_PROVIDER + key (DeepSeek recommended for CFO)
uvicorn backend.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend && npm install
cp .env.example .env.local
npm run dev  # http://localhost:3000
```

Then open http://localhost:3000 → defaults to `/bookkeeping` (placeholder).
v0.1 module implementation pending PRD decisions A + B (which module to
build first).

## License

TBD.
