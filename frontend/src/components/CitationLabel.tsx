/**
 * CitationLabel —— 显示 [N] 上标，点击在右侧抽屉打开原文.
 */

"use client";

import type { Citation } from "@/types/citation";
import { cn } from "@/lib/utils";
import { useCitationStore } from "@/stores/citationStore";

type Props = {
  citation: Citation;
  className?: string;
};

export function CitationLabel({ citation, className }: Props) {
  const open = useCitationStore((s) => s.open);

  return (
    <button
      type="button"
      onClick={() => open(citation)}
      title={citation.source_name}
      className={cn(
        "ml-0.5 inline-flex items-center justify-center rounded-md bg-accent px-1.5 py-0.5 text-[10px] font-medium text-accent-foreground hover:bg-accent/70 hover:underline",
        className,
      )}
    >
      {citation.label}
    </button>
  );
}
