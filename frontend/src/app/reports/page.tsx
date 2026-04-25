import { WorkspaceCanvas } from "@/components/WorkspaceCanvas";

export default function ReportsPage() {
  return (
    <WorkspaceCanvas
      emptyHint={
        <div className="space-y-3">
          <div className="text-sm font-medium text-foreground">财务报表（Coming in v0.3）</div>
          <div>
            v0.3 上线：资产负债表 + 利润表 + 现金流量表，含多期对比、关键比率、
            异常自动标注。
          </div>
          <div className="text-[11px] text-muted-foreground/70">
            详见 docs/PRD.md §4.3
          </div>
        </div>
      }
    />
  );
}
