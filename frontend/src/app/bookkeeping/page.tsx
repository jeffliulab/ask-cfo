import { WorkspaceCanvas } from "@/components/WorkspaceCanvas";

export default function BookkeepingPage() {
  return (
    <WorkspaceCanvas
      emptyHint={
        <div className="space-y-3">
          <div className="text-sm font-medium text-foreground">凭证录入</div>
          <div>
            上传发票 / 银行流水截图 / 业务说明 → AI 草拟会计分录 + 引用准则原文。
          </div>
          <div className="text-[11px] text-muted-foreground/70">
            v0.1 待办：决定 OCR provider（Azure / 腾讯云 / 自部署 PaddleOCR）+ 准则
            RAG 数据源 + 输入交互（拖拽 / 粘贴 / 拍照）。详见 docs/PRD.md §4.1
          </div>
        </div>
      }
    />
  );
}
