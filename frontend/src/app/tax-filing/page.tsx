import { WorkspaceCanvas } from "@/components/WorkspaceCanvas";

export default function TaxFilingPage() {
  return (
    <WorkspaceCanvas
      emptyHint={
        <div className="space-y-3">
          <div className="text-sm font-medium text-foreground">报税申报（Coming in v0.4）</div>
          <div>
            v0.4 上线：增值税 / 企业所得税 / 个税自动计算 + 预填申报表。
            参考 legacy/wencfo/tax_service 中的 Playwright 自动化方案（仅参考，不维护）。
          </div>
          <div className="text-[11px] text-muted-foreground/70">
            合规 / 牌照风险评估在 v0.4 启动前必须做完。详见 docs/PRD.md §4.4
          </div>
        </div>
      }
    />
  );
}
