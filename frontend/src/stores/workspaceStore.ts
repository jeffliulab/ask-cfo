/**
 * workspaceStore —— v0.1 generic in-memory zustand store.
 *
 * v0.1 各 CFO 模块（凭证 / 月结 / 报表 / 报税 / 法规问答）会各自加 action
 * （`createVoucher` / `runMonthEnd` / `searchRegulation` / etc.），都通过
 * `setCards` / `setStatus` 与本 store 通信.
 *
 * v0.4 会迁到持久化（SQLite），加多 workspace 切换、历史等.
 */

import { create } from "zustand";

import type { Workspace, WorkspaceCard, WorkspaceStatus } from "@/types/workspace";

type WorkspaceActions = {
  setCards: (cards: WorkspaceCard[], workspaceId?: string) => void;
  setStatus: (status: WorkspaceStatus, errorMessage?: string | null) => void;
  reset: () => void;
};

const INITIAL_STATE: Workspace = {
  status: "idle",
  activeWorkspaceId: null,
  cards: [],
  errorMessage: null,
};

export const useWorkspaceStore = create<Workspace & WorkspaceActions>((set) => ({
  ...INITIAL_STATE,

  setCards: (cards, workspaceId) =>
    set((s) => ({
      status: "ready",
      cards,
      activeWorkspaceId: workspaceId ?? s.activeWorkspaceId,
      errorMessage: null,
    })),

  setStatus: (status, errorMessage = null) =>
    set({ status, errorMessage }),

  reset: () => set(INITIAL_STATE),
}));

// === Selectors ===
export const selectWorkspaceCards = (s: Workspace): WorkspaceCard[] => s.cards;
export const selectWorkspaceStatus = (s: Workspace): WorkspaceStatus => s.status;
export const selectActiveWorkspaceId = (s: Workspace): string | null =>
  s.activeWorkspaceId;
export const selectWorkspaceError = (s: Workspace): string | null => s.errorMessage;
