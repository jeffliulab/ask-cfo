/**
 * WorkspaceCanvas —— 中栏：用户当前任务的工作区.
 *
 * v0.1 个股模块：渲染 3 张 CompanyCard（财务 KPI / 公告 / 研报）.
 * v0.2 行业模块：5×8 Generative Grid.
 * v0.3 市场模块：行情 / 资金面 dashboard.
 *
 * 这一层只是容器 —— 不感知卡片内容，children 由路由页面提供.
 */

import { ReactNode } from "react";

type Props = {
  children?: ReactNode;
  /** 当 children 为空时显示的占位文案（如初始空状态）。 */
  emptyHint?: ReactNode;
};

export function WorkspaceCanvas({ children, emptyHint }: Props) {
  const hasContent = children !== undefined && children !== null && children !== false;

  return (
    <div className="flex h-full flex-col gap-4 px-6 py-5">
      {hasContent ? (
        children
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <div className="max-w-md text-center text-sm text-muted-foreground">
            {emptyHint ?? "工作区为空。从上方输入开始。"}
          </div>
        </div>
      )}
    </div>
  );
}
