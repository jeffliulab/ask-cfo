/**
 * AgentTrace —— 折叠展示 RegulationAgent 的 search/get 调用过程.
 *
 * v0.1 D5：让用户看到 agent search 的"思考路径"，区别于黑盒 RAG。
 * 默认折叠，点击展开看时间线。
 */

"use client";

import { ChevronDown, ChevronRight, Search, BookOpen } from "lucide-react";
import { useState } from "react";

import type { AgentTraceEvent } from "@/types/chat";

type Props = {
  events: AgentTraceEvent[];
};

export function AgentTrace({ events }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (events.length === 0) return null;

  // 把 tool_call + tool_result 按 callId 配对
  const pairs: Array<{
    call?: AgentTraceEvent;
    result?: AgentTraceEvent;
  }> = [];
  const byId = new Map<string, { call?: AgentTraceEvent; result?: AgentTraceEvent }>();
  for (const ev of events) {
    const slot = byId.get(ev.callId) ?? {};
    if (ev.kind === "tool_call") slot.call = ev;
    else slot.result = ev;
    byId.set(ev.callId, slot);
  }
  for (const ev of events) {
    if (ev.kind === "tool_call") pairs.push(byId.get(ev.callId)!);
  }

  return (
    <div className="rounded border border-border bg-muted/20">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-foreground/80 hover:bg-muted/40 transition"
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          <span>Agent 检索轨迹</span>
          <span className="text-muted-foreground">
            （{pairs.length} 步）
          </span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border px-3 py-2">
          <ol className="space-y-2 text-[11px]">
            {pairs.map((p, i) => (
              <li key={p.call?.callId ?? i} className="flex items-start gap-2">
                <span className="mt-0.5 text-muted-foreground">{i + 1}.</span>
                <div className="flex-1 space-y-1">
                  {p.call && p.call.kind === "tool_call" && (
                    <div className="flex items-center gap-1.5 font-mono">
                      {p.call.name === "search_regulations" ? (
                        <Search className="h-3 w-3 text-blue-600" />
                      ) : (
                        <BookOpen className="h-3 w-3 text-purple-600" />
                      )}
                      <span className="font-medium">{p.call.name}</span>
                      <span className="text-muted-foreground">
                        ({renderInput(p.call.input)})
                      </span>
                    </div>
                  )}
                  {p.result && p.result.kind === "tool_result" && (
                    <div className="ml-5 text-muted-foreground">
                      → {p.result.summary}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function renderInput(input: Record<string, unknown>): string {
  return Object.entries(input)
    .map(([k, v]) => `${k}=${typeof v === "string" ? `"${v}"` : v}`)
    .join(", ");
}
