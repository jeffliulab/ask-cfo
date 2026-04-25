/**
 * Workspace state types —— v0.1 generic placeholder.
 *
 * v0.1 各 CFO 模块（凭证 / 月结 / 报表 / 报税 / 法规问答）会各自定义具体
 * card_type 及其 payload schema；本文件先放通用 Workspace + WorkspaceCard
 * 占位，等模块上线时各自扩展（discriminated union over card_type，参考
 * fin-pilot 的 stock.ts 写法）。
 */

import type { Citation } from "./citation";

export type WorkspaceStatus = "idle" | "loading" | "ready" | "error";

/** Generic workspace card — payload schema depends on card_type. */
export type WorkspaceCard = {
  workspace_id: string;
  card_type: string; // e.g. "voucher_draft" / "trial_balance" / "regulation_snippet"
  title: string;
  payload: Record<string, unknown>;
  citations: Citation[];
};

export type Workspace = {
  status: WorkspaceStatus;
  /** 当前激活的工作区 ID（凭证号 / 月份 / 检索查询等，由各模块定） */
  activeWorkspaceId: string | null;
  cards: WorkspaceCard[];
  errorMessage: string | null;
};
