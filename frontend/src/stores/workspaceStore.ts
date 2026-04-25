/**
 * workspaceStore —— v0.1 D5 namespaced by moduleId.
 *
 * 每个 module（regulations / bookkeeping / month_end / reports / tax_filing）
 * 有自己独立的 workspace 子状态，避免跨模块 setCards 互覆。
 *
 * v0.4 持久化（SQLite）时不动这层；store 只缓存当前 session 内的 workspace
 * 视图，refresh 后从 backend 重读。
 */

import { create } from "zustand";

import type {
  ModuleId,
  ModuleWorkspace,
  WorkspaceCard,
  WorkspaceStatus,
} from "@/types/workspace";
import type { AgentTraceEvent } from "@/types/chat";

type State = {
  /** module → workspace 子状态 */
  workspaces: Record<string, ModuleWorkspace>;
  /** module → agent trace 事件序列 */
  agentTrace: Record<string, AgentTraceEvent[]>;
  /** 全局当前 module（最近 setActiveModule） */
  activeModuleId: ModuleId | null;
  /** Page 级 sample buttons → ChatPanel 输入框桥接（v0.1 D5）.
   * Page 调 setPendingQuery；ChatPanel useEffect 读取 + 自动 send + 清空. */
  pendingQuery: string | null;
};

type Actions = {
  setActiveModule: (moduleId: ModuleId | null) => void;
  setCards: (
    moduleId: ModuleId,
    cards: WorkspaceCard[],
    workspaceId?: string | null,
  ) => void;
  appendCard: (moduleId: ModuleId, card: WorkspaceCard) => void;
  setStatus: (
    moduleId: ModuleId,
    status: WorkspaceStatus,
    errorMessage?: string | null,
  ) => void;
  appendAgentTrace: (moduleId: ModuleId, event: AgentTraceEvent) => void;
  clearAgentTrace: (moduleId: ModuleId) => void;
  resetModule: (moduleId: ModuleId) => void;
  resetAll: () => void;
  setPendingQuery: (q: string | null) => void;
};

const EMPTY_MODULE: ModuleWorkspace = {
  status: "idle",
  activeWorkspaceId: null,
  cards: [],
  errorMessage: null,
};

const INITIAL_STATE: State = {
  workspaces: {},
  agentTrace: {},
  activeModuleId: null,
  pendingQuery: null,
};

function ensureModule(
  state: State,
  moduleId: ModuleId,
): ModuleWorkspace {
  return state.workspaces[moduleId] ?? EMPTY_MODULE;
}

export const useWorkspaceStore = create<State & Actions>((set) => ({
  ...INITIAL_STATE,

  setActiveModule: (moduleId) => set({ activeModuleId: moduleId }),

  setCards: (moduleId, cards, workspaceId) =>
    set((s) => ({
      workspaces: {
        ...s.workspaces,
        [moduleId]: {
          ...ensureModule(s, moduleId),
          status: "ready",
          cards,
          activeWorkspaceId:
            workspaceId !== undefined
              ? workspaceId
              : ensureModule(s, moduleId).activeWorkspaceId,
          errorMessage: null,
        },
      },
    })),

  appendCard: (moduleId, card) =>
    set((s) => {
      const cur = ensureModule(s, moduleId);
      return {
        workspaces: {
          ...s.workspaces,
          [moduleId]: {
            ...cur,
            status: "ready",
            cards: [...cur.cards, card],
          },
        },
      };
    }),

  setStatus: (moduleId, status, errorMessage = null) =>
    set((s) => ({
      workspaces: {
        ...s.workspaces,
        [moduleId]: {
          ...ensureModule(s, moduleId),
          status,
          errorMessage,
        },
      },
    })),

  appendAgentTrace: (moduleId, event) =>
    set((s) => ({
      agentTrace: {
        ...s.agentTrace,
        [moduleId]: [...(s.agentTrace[moduleId] ?? []), event],
      },
    })),

  clearAgentTrace: (moduleId) =>
    set((s) => ({
      agentTrace: { ...s.agentTrace, [moduleId]: [] },
    })),

  resetModule: (moduleId) =>
    set((s) => ({
      workspaces: { ...s.workspaces, [moduleId]: EMPTY_MODULE },
      agentTrace: { ...s.agentTrace, [moduleId]: [] },
    })),

  resetAll: () => set(INITIAL_STATE),

  setPendingQuery: (pendingQuery) => set({ pendingQuery }),
}));

// === Selectors（factory，按 moduleId 取） ===
//
// ⚠️ 稳定引用：所有"未初始化"分支返回的空数组 / null **必须**用模块级常量；
// 否则 zustand 用 Object.is 比较新旧值，每次 `?? []` 产生新数组 → 视为
// "状态变化" → 触发 re-render → 重新调用 selector → 新数组 → 死循环
// （Maximum update depth exceeded）。

const EMPTY_CARDS: ReadonlyArray<WorkspaceCard> = [];
const EMPTY_TRACE: ReadonlyArray<AgentTraceEvent> = [];

export const selectModuleCards =
  (moduleId: ModuleId | null) =>
  (s: State): WorkspaceCard[] => {
    if (!moduleId) return EMPTY_CARDS as WorkspaceCard[];
    const m = s.workspaces[moduleId];
    return m?.cards ?? (EMPTY_CARDS as WorkspaceCard[]);
  };

export const selectModuleStatus =
  (moduleId: ModuleId | null) =>
  (s: State): WorkspaceStatus => {
    if (!moduleId) return "idle";
    return s.workspaces[moduleId]?.status ?? "idle";
  };

export const selectModuleActiveWorkspaceId =
  (moduleId: ModuleId | null) =>
  (s: State): string | null => {
    if (!moduleId) return null;
    return s.workspaces[moduleId]?.activeWorkspaceId ?? null;
  };

export const selectModuleError =
  (moduleId: ModuleId | null) =>
  (s: State): string | null => {
    if (!moduleId) return null;
    return s.workspaces[moduleId]?.errorMessage ?? null;
  };

export const selectModuleAgentTrace =
  (moduleId: ModuleId | null) =>
  (s: State): AgentTraceEvent[] => {
    if (!moduleId) return EMPTY_TRACE as AgentTraceEvent[];
    return s.agentTrace[moduleId] ?? (EMPTY_TRACE as AgentTraceEvent[]);
  };

export const selectActiveModuleId = (s: State): ModuleId | null =>
  s.activeModuleId;

export const selectPendingQuery = (s: State): string | null => s.pendingQuery;
