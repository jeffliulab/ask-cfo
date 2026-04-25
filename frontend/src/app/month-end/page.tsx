import { WorkspaceCanvas } from "@/components/WorkspaceCanvas";

export default function MonthEndPage() {
  return (
    <WorkspaceCanvas
      emptyHint={
        <div className="space-y-3">
          <div className="text-sm font-medium text-foreground">月结对账（Coming in v0.2）</div>
          <div>
            v0.2 上线：本月凭证审核 → 试算平衡 → 待结转项检查 → 出三大报表草稿。
          </div>
          <div className="text-[11px] text-muted-foreground/70">
            依赖 v0.1 的凭证录入打通 + 数据持久化。详见 docs/PRD.md §4.2
          </div>
        </div>
      }
    />
  );
}
