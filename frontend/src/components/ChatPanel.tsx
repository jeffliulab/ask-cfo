/**
 * ChatPanel —— 右栏：自然语言追问 + 流式回答 + [N] 角标 → CitationLabel.
 *
 * 数据来源：
 * - workspaceStore.cards / citations（推断当前 workspace 上下文喂给 LLM）
 * - useChatStream hook 管理 messages + 流状态
 */

"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Send, Square } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatStream } from "@/features/chat/ChatStream";
import { useChatStream } from "@/hooks/useChatStream";
import {
  selectActiveWorkspaceId,
  selectWorkspaceCards,
  selectWorkspaceStatus,
  useWorkspaceStore,
} from "@/stores/workspaceStore";
import type { Citation } from "@/types/citation";

/** 从 workspace 卡片里聚合所有 citations，去重，重新打 [N] 标签. */
function collectCitations(cards: ReturnType<typeof selectWorkspaceCards>): Citation[] {
  const seen = new Map<string, Citation>();
  for (const card of cards) {
    for (const cite of card.citations) {
      const key = cite.url || cite.source_name;
      if (!seen.has(key)) seen.set(key, cite);
    }
  }
  // 重新编号 [1] [2] [3] ...
  return Array.from(seen.values()).map((c, idx) => ({
    ...c,
    label: `[${idx + 1}]`,
  }));
}

export function ChatPanel() {
  const cards = useWorkspaceStore(selectWorkspaceCards);
  const activeWorkspaceId = useWorkspaceStore(selectActiveWorkspaceId);
  const wsStatus = useWorkspaceStore(selectWorkspaceStatus);
  const { messages, status, send, stop, reset } = useChatStream();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // 切换工作区（activeWorkspaceId 变了）时清空对话
  useEffect(() => {
    reset();
    setInput("");
  }, [activeWorkspaceId, reset]);

  // 新消息时自动滚到底
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const isStreaming = status === "streaming";
  const isReady = wsStatus === "ready" && cards.length > 0;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !isReady) return;
    const text = input;
    setInput("");
    const citations = collectCitations(cards);
    await send(text, { cards, citations });
  };

  return (
    <div className="flex h-full flex-col">
      {/* 头部 */}
      <div className="flex h-12 items-center justify-between border-b border-border px-4">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          对话
        </div>
        {activeWorkspaceId && (
          <div className="text-[11px] text-muted-foreground">
            上下文：{activeWorkspaceId}
          </div>
        )}
      </div>

      {/* 消息流 */}
      <ScrollArea className="flex-1">
        <div ref={scrollRef} className="px-4 py-4">
          <ChatStream messages={messages} isStreaming={isStreaming} />
        </div>
      </ScrollArea>

      {/* 输入框 */}
      <form
        className="flex items-center gap-2 border-t border-border px-3 py-3"
        onSubmit={handleSubmit}
      >
        <Input
          name="message"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            isReady ? "问一个问题..." : "工作区还没数据，先去左侧菜单选模块..."
          }
          disabled={!isReady || isStreaming}
          className="flex-1"
        />
        {isStreaming ? (
          <Button
            type="button"
            size="icon"
            variant="secondary"
            onClick={stop}
            title="停止生成"
          >
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            type="submit"
            size="icon"
            disabled={!isReady || !input.trim()}
            title="发送"
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
      </form>
    </div>
  );
}
