/**
 * RegulationCard —— 渲染单条 RegulationSnippetCard.
 * v0.1 D5：标题 + 出处 + 摘要 + Citation drawer 链接 + 折叠的 full_text.
 */

"use client";

import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { useState } from "react";

import { Card } from "@/components/ui/card";
import { CitationLabel } from "@/components/CitationLabel";
import type { RegulationSnippetCard as RegCard } from "@/types/workspace";

const CATEGORY_LABEL: Record<string, string> = {
  VAT: "增值税",
  CIT: "企业所得税",
  IIT: "个人所得税",
  CAS: "会计准则",
};

const CATEGORY_COLOR: Record<string, string> = {
  VAT: "bg-blue-100 text-blue-700",
  CIT: "bg-green-100 text-green-700",
  IIT: "bg-amber-100 text-amber-700",
  CAS: "bg-purple-100 text-purple-700",
};

type Props = {
  card: RegCard;
};

export function RegulationCard({ card }: Props) {
  const [showFull, setShowFull] = useState(false);
  const { payload, citations } = card;
  const catLabel = CATEGORY_LABEL[payload.category] ?? payload.category;
  const catColor =
    CATEGORY_COLOR[payload.category] ?? "bg-muted text-muted-foreground";

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${catColor}`}
            >
              {catLabel}
            </span>
            {citations[0] && <CitationLabel citation={citations[0]} />}
            <span className="text-[11px] text-muted-foreground">
              {payload.chapter} · {payload.article_number}
            </span>
          </div>
          <h3 className="text-sm font-semibold leading-tight">{card.title}</h3>
          <div className="mt-1 text-[11px] text-muted-foreground truncate">
            {payload.source_name}
          </div>
        </div>
        {citations[0]?.url && (
          <a
            href={citations[0].url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground transition"
            title="在新标签打开原文"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
      </div>

      <p className="mt-3 text-sm leading-relaxed text-foreground/90">
        {payload.summary}
      </p>

      <button
        type="button"
        onClick={() => setShowFull((v) => !v)}
        className="mt-3 flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition"
      >
        {showFull ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        {showFull ? "收起完整条款" : "展开完整条款"}
      </button>

      {showFull && (
        <div className="mt-2 rounded border border-border bg-muted/30 px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap text-foreground/80">
          {payload.full_text}
        </div>
      )}
    </Card>
  );
}
