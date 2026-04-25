/**
 * CitationDrawer —— 右侧抽屉，载入引用源原文（iframe）+ 头部显源名 + 外链快捷.
 *
 * 注意：很多金融网站（巨潮、东财、SEC EDGAR）设置 X-Frame-Options: DENY，
 * iframe 会显空白。底部固定一条提示 + 右上角 ↗ 按钮一键新标签打开作 fallback.
 */

"use client";

import { ExternalLink } from "lucide-react";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useCitationStore } from "@/stores/citationStore";

export function CitationDrawer() {
  const { isOpen, active, close } = useCitationStore();

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && close()}>
      <SheetContent
        side="right"
        className="flex w-full max-w-2xl flex-col gap-0 p-0 sm:max-w-2xl"
      >
        {active && (
          <>
            <SheetHeader className="border-b border-border px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex min-w-0 flex-col">
                  <SheetTitle className="truncate text-sm">
                    <span className="mr-2 rounded bg-accent px-1.5 py-0.5 text-[10px] font-medium text-accent-foreground">
                      {active.label}
                    </span>
                    {active.source_name}
                  </SheetTitle>
                  <SheetDescription className="truncate text-[11px]">
                    {active.url}
                  </SheetDescription>
                </div>
                {active.url && (
                  <a
                    href={active.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="在新标签打开"
                    className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </div>
            </SheetHeader>

            {/* 正文：iframe 加载原文 */}
            <div className="flex-1 overflow-hidden bg-muted">
              {active.url ? (
                <iframe
                  src={active.url}
                  title={active.source_name}
                  className="h-full w-full border-0"
                  sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
                />
              ) : (
                <div className="flex h-full items-center justify-center px-6 text-center text-sm text-muted-foreground">
                  此引用没有可点击 URL
                </div>
              )}
            </div>

            {/* 底部 fallback 提示 */}
            <div className="border-t border-border bg-muted/30 px-4 py-2 text-[11px] text-muted-foreground">
              提示：若原文未显示（巨潮 / SEC 等设置了 X-Frame-Options 禁嵌入），
              点右上角 <ExternalLink className="inline h-3 w-3" /> 在新标签打开。
              v0.5 上 PDF.js 后改为本地高亮渲染。
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
