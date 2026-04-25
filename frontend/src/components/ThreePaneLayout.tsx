/**
 * ThreePaneLayout —— "金融版 Cursor" 的三栏壳：左菜单 + 中工作区 + 右聊天.
 *
 * 按 docs/architecture.md §1 的 ASCII 草图。固定全屏高度，三栏自横向分配宽度，
 * 各栏内部独立滚动。
 *
 * Layout 数值（v0.1 hard-code，v0.2 评估是否抽 CSS variable）：
 *   - 左：240px 固定
 *   - 中：flex 1（自适应）
 *   - 右：420px 固定
 *
 * 按 stacks/frontend.md：components/ 只负责展示，不直接 fetch / 不持业务逻辑。
 */

import { ReactNode } from "react";

type Props = {
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
};

export function ThreePaneLayout({ left, center, right }: Props) {
  return (
    <div className="grid h-screen w-screen grid-cols-[240px_1fr_420px] overflow-hidden bg-background text-foreground">
      <aside className="flex h-full flex-col overflow-y-auto border-r border-border bg-muted/30">
        {left}
      </aside>
      <main className="flex h-full flex-col overflow-y-auto">{center}</main>
      <aside className="flex h-full flex-col overflow-hidden border-l border-border bg-muted/10">
        {right}
      </aside>
    </div>
  );
}
