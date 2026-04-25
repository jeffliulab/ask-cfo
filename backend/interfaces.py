"""跨层契约 —— 所有 routes / services / repositories 共用的 dataclass 与 Protocol.

按 agent-rules/principles/architecture.md：跨模块通信优先通过接口契约而不是直接耦合实现。
任何会被多层引用的数据形状都集中在这里，避免循环 import。

v0.1 阶段 CFO 模块（凭证 / 月结 / 报表 / 报税 / 法规）的具体数据形状还在
设计中，本文件先放通用契约（Citation / WorkspaceCard / DataSourceError）；
模块上线时再加具体 schema（如 VoucherCard / MonthEndReportCard 等）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


# === Citation：所有 AI 输出的引用统一格式（与 fin-pilot 一致） ===
@dataclass
class Citation:
    """A pointer to the original source backing an AI claim or a card field.

    Rendered as ``[N]`` superscript inline in chat / cards; clicking opens a
    side drawer with the URL.

    CFO 场景：通常指法规原文（《增值税暂行条例》某条 / 国税总局公告 / 会计准则
    具体编号），抽屉里 iframe 加载相应 PDF 或 HTML 页面。
    """

    label: str  # e.g. "[1]"
    source_name: str  # e.g. "《增值税暂行条例实施细则》第 24 条"
    url: str  # 真实可点击 URL（国税总局 / 法律法规库 / 巨潮财报等）


# === Workspace 卡片基类（v0.1 generic placeholder） ===
@dataclass
class WorkspaceCard:
    """A workspace card rendered as one section in the center pane.

    v0.1 是通用 placeholder，不绑定具体 card_type。具体的 CFO 卡片
    （VoucherDraftCard / TrialBalanceCard / TaxCalcCard / RegulationSnippetCard 等）
    在各 service 模块上线时各自定义 + 注册到此联合类型里。

    payload 的 schema 由 card_type 决定 —— 各模块 service 自由约定。
    """

    workspace_id: str  # e.g. "voucher-2026-04-24-001" / "month-end-2026-03"
    card_type: str  # e.g. "voucher_draft" / "trial_balance" / "regulation_snippet"
    title: str
    payload: dict
    citations: list[Citation] = field(default_factory=list)


# === Repository contract 占位（v0.1 各模块自定） ===
class CFOModuleProvider(Protocol):
    """Stub for v0.1 — each CFO module will define its own provider Protocol.

    Examples (v0.2+):
      - InvoiceOCRProvider: parse_invoice(file) -> InvoiceParsed
      - RegulationSearchProvider: search(query) -> list[RegulationSnippet]
      - TaxCalcProvider: compute_vat(...) -> TaxLiability
    """

    name: str


# === Module-specific WorkspaceCard payloads ===
@dataclass
class RegulationSnippetPayload:
    """``card_type='regulation_snippet'`` 的 payload —— v0.1 法规问答."""

    reg_id: str  # e.g. "cit-rd-superdeduction-100pct-2023"
    source_name: str
    chapter: str
    article_number: str
    summary: str
    full_text: str
    category: str  # "VAT" | "CIT" | "IIT" | "CAS"


# === Errors ===
class DataSourceError(RuntimeError):
    """Raised when an external data source (OCR / RAG / 国税局接口) fails.

    携带原始 exception + 数据源名称，让上层决定降级 / 重试 / 报错给用户。
    """

    def __init__(self, source: str, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(f"[{source}] {message}")
        self.source = source
        self.cause = cause
