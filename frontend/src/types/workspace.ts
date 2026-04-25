/**
 * Workspace state types —— v0.1 D5：generic + 法规模块 discriminated union 起手.
 *
 * 后续模块（凭证 / 月结 / 报表 / 报税）上线时，在 ``CARD_TYPES`` 加 literal 并
 * 给具体 payload type；保持 generic ``WorkspaceCard`` 作为 fallback（其他模块
 * 没特化前都走这条）。
 */

import type { Citation } from "./citation";
import type { RegulationSnippetPayload } from "./regulation";

export type WorkspaceStatus = "idle" | "loading" | "ready" | "error";

/** 当前已知 card_type literal —— 模块上线时扩展. */
export type CardType =
  | "regulation_snippet"
  | "voucher_draft"
  | "tax_risk"
  | "trial_balance"
  | "anomaly"
  | "closing_entry"
  | "income_statement"
  | "balance_sheet"
  | "cash_flow"
  | "ratios"
  | "multi_period_chart"
  | "vat_filing_form"
  | "corp_tax_filing_form"
  | "pit_filing_form"
  | (string & {}); // 允许未来未知 card_type 不破坏类型（fallback）

/** v0.1 法规模块特化：discriminated union 让前端 `switch (card.card_type)` 自动窄化 payload. */
export type RegulationSnippetCard = {
  workspace_id: string;
  card_type: "regulation_snippet";
  title: string;
  payload: RegulationSnippetPayload;
  citations: Citation[];
};

/** 通用 fallback —— 未特化的模块卡片. */
export type GenericWorkspaceCard = {
  workspace_id: string;
  card_type: Exclude<CardType, "regulation_snippet">;
  title: string;
  payload: Record<string, unknown>;
  citations: Citation[];
};

export type WorkspaceCard = RegulationSnippetCard | GenericWorkspaceCard;

/** Module 命名空间 ID —— 与 backend 的 prefix 对齐. */
export type ModuleId =
  | "regulations"
  | "bookkeeping"
  | "month_end"
  | "reports"
  | "tax_filing";

/** 单个 module 的 workspace 子状态. */
export type ModuleWorkspace = {
  status: WorkspaceStatus;
  activeWorkspaceId: string | null;
  cards: WorkspaceCard[];
  errorMessage: string | null;
};
