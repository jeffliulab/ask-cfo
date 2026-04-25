/**
 * citationStore —— 控制 CitationDrawer 的开/合 + 当前展示的 citation.
 *
 * v0.1：单 drawer 单时刻一个 citation；v0.5 评估"多 drawer pinning"（同时挂多个）.
 */

import { create } from "zustand";

import type { Citation } from "@/types/citation";

type CitationStore = {
  isOpen: boolean;
  active: Citation | null;
  open: (citation: Citation) => void;
  close: () => void;
};

export const useCitationStore = create<CitationStore>((set) => ({
  isOpen: false,
  active: null,
  open: (citation: Citation) => set({ isOpen: true, active: citation }),
  close: () => set({ isOpen: false }),
}));
