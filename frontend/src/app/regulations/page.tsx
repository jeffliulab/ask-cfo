import { WorkspaceCanvas } from "@/components/WorkspaceCanvas";

export default function RegulationsPage() {
  return (
    <WorkspaceCanvas
      emptyHint={
        <div className="space-y-3">
          <div className="text-sm font-medium text-foreground">法规问答</div>
          <div>
            自然语言提问 → 检索增值税 / 企业所得税 / 会计准则 / 税总公告 →
            返回相关条款 + Citation Drawer 打开原文 PDF。
          </div>
          <div className="text-[11px] text-muted-foreground/70">
            v0.1 待办：决定 RAG 数据源（爬国税总局公告库 / 用第三方法律数据库）+
            chunk 策略 + 引用粒度。详见 docs/PRD.md §4.5
          </div>
        </div>
      }
    />
  );
}
