/**
 * ChatStream —— 渲染 chat messages，识别 [N] 角标转成 CitationLabel.
 *
 * 解析方式：正则按 [数字] 切分文本，匹配的部分查 citations 表，未匹配的
 * 直接 text node 渲染.
 */

"use client";

import { Loader2 } from "lucide-react";

import { CitationLabel } from "@/components/CitationLabel";
import type { Citation } from "@/types/citation";
import type { ChatMessage } from "@/types/chat";

type Props = {
  messages: ChatMessage[];
  isStreaming: boolean;
  /** 当前 module 是否激活（v0.1 仅 regulations）。影响空状态文案. */
  moduleActive?: boolean;
};

const CITATION_REGEX = /\[(\d+)\]/g;

function renderTextWithCitations(text: string, citations: Citation[]) {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  // 重置 regex.lastIndex
  CITATION_REGEX.lastIndex = 0;

  while ((match = CITATION_REGEX.exec(text)) !== null) {
    const before = text.slice(lastIndex, match.index);
    if (before) parts.push(before);

    const label = match[0]; // "[1]"
    const cite = citations.find((c) => c.label === label);
    if (cite) {
      parts.push(<CitationLabel key={`cite-${match.index}`} citation={cite} />);
    } else {
      // 未匹配的 [N] 当文本渲（也许 LLM 引用了不存在的源）
      parts.push(label);
    }
    lastIndex = match.index + label.length;
  }

  const tail = text.slice(lastIndex);
  if (tail) parts.push(tail);

  return parts.length > 0 ? parts : [text];
}

function MessageBubble({ msg, isLast, isStreaming }: { msg: ChatMessage; isLast: boolean; isStreaming: boolean }) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
          {msg.content}
        </div>
      </div>
    );
  }

  if (msg.role === "error") {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
        <div className="font-medium">出错了</div>
        <div className="mt-1 break-all">{msg.content}</div>
      </div>
    );
  }

  // assistant
  const showSpinner = isLast && isStreaming && !msg.content;
  return (
    <div className="flex flex-col gap-1">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        Ask CFO
      </div>
      <div className="text-sm leading-relaxed whitespace-pre-wrap">
        {showSpinner ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : (
          renderTextWithCitations(msg.content, msg.citations ?? [])
        )}
      </div>
    </div>
  );
}

export function ChatStream({ messages, isStreaming, moduleActive = true }: Props) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 pt-12 text-center">
        <div className="text-sm text-muted-foreground">
          {moduleActive
            ? "在下方输入框提问，或点工作区的示例查询。"
            : "本模块在 v0.2+ 启用。先去法规问答试试 →"}
        </div>
        <div className="text-[11px] text-muted-foreground/70">
          回答带 [N] 角标，点开右侧抽屉看法规原文
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {messages.map((msg, idx) => (
        <MessageBubble
          key={msg.id}
          msg={msg}
          isLast={idx === messages.length - 1}
          isStreaming={isStreaming}
        />
      ))}
    </div>
  );
}
