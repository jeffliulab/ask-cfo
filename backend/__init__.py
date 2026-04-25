"""agent-as-a-cfo backend —— FastAPI 三层架构 + LLM 旁路（4 provider 矩阵）.

按 agent-rules/stacks/python-backend.md 组织。框架壳子从姐妹项目 fin-pilot
v0.1.0 复制（commit ac6f87c）；CFO 业务实现（凭证 / 月结 / 报税 / 法规）
v0.1.0 起从零搭建，详见 docs/PRD.md。
"""

__version__ = "0.1.0.dev"
