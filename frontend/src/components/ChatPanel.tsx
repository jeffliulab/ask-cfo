/**
 * ChatPanel —— 右栏：自然语言追问 + 流式回答 + [N] 角标 → CitationLabel.
 *
 * v0.1 D5：模块感知 —— 根据 pathname 推断 moduleId，选择正确 stream config：
 * - /regulations → regulationsQAConfig（agent search + tool_use）
 * - 其他（v0.2+ 占位）→ 默认 chat config，但 v0.1 期间禁用
 *
 * 与 page-level sample buttons 通过 ``pendingQuery`` 桥接。
 */

"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Send, Square } from "lucide-react";
import { usePathname } from "next/navigation";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatStream } from "@/features/chat/ChatStream";
import {
  defaultChatConfig,
  regulationsQAConfig,
  StreamConfig,
  useChatStream,
} from "@/hooks/useChatStream";
import {
  selectModuleActiveWorkspaceId,
  selectModuleCards,
  selectPendingQuery,
  useWorkspaceStore,
} from "@/stores/workspaceStore";
import type { ModuleId } from "@/types/workspace";

const MODULE_BY_PATH: Record<string, ModuleId> = {
  "/regulations": "regulations",
  "/bookkeeping": "bookkeeping",
  "/month-end": "month_end",
  "/reports": "reports",
  "/tax-filing": "tax_filing",
};

const ACTIVE_MODULES: ReadonlySet<ModuleId> = new Set<ModuleId>(["regulations"]);

function deriveConfig(pathname: string): {
  moduleId: ModuleId | null;
  config: StreamConfig;
  active: boolean;
  placeholderHint: string;
} {
  // 找到 prefix 匹配（避免 ?query / 子路由问题）
  const matchEntry = Object.entries(MODULE_BY_PATH).find(([prefix]) =>
    pathname.startsWith(prefix),
  );
  if (!matchEntry) {
    return {
      moduleId: null,
      config: defaultChatConfig,
      active: false,
      placeholderHint: "从左侧选一个模块开始...",
    };
  }
  const [, moduleId] = matchEntry;
  const active = ACTIVE_MODULES.has(moduleId);

  if (moduleId === "regulations") {
    return {
      moduleId,
      config: regulationsQAConfig,
      active: true,
      placeholderHint: "问一个税务/会计问题...",
    };
  }
  return {
    moduleId,
    config: { ...defaultChatConfig, moduleId },
    active,
    placeholderHint: active
      ? "问一个问题..."
      : `${moduleId} 模块在 v0.2+ 启用`,
  };
}

export function ChatPanel() {
  const pathname = usePathname();

  // 必须 memoize：deriveConfig 每次返回新 config 对象 → 下游 useChatStream 的
  // useCallback(send) 依赖 config → 每次 render 新 send 身份 → pendingQuery
  // effect 死循环。pathname 变才重算。
  const { moduleId, config, active, placeholderHint } = useMemo(
    () => deriveConfig(pathname),
    [pathname],
  );

  const { messages, status, send, stop, reset } = useChatStream(config);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // 直接传 moduleId（可为 null）；selector 内部 null-safe + 稳定空数组兜底
  const cards = useWorkspaceStore(selectModuleCards(moduleId));
  const activeWorkspaceId = useWorkspaceStore(selectModuleActiveWorkspaceId(moduleId));
  const pendingQuery = useWorkspaceStore(selectPendingQuery);
  const setPendingQuery = useWorkspaceStore((s) => s.setPendingQuery);

  // 切模块时清对话
  useEffect(() => {
    reset();
    setInput("");
  }, [pathname, reset]);

  // 来自 SampleQueries 的 pendingQuery → 自动 send + 清空
  useEffect(() => {
    if (!pendingQuery || !active) return;
    const q = pendingQuery;
    setPendingQuery(null);
    if (status === "streaming") return;
    void send(q, { cards });
  }, [pendingQuery, active, status, cards, send, setPendingQuery]);

  // 新消息自动滚到底
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const isStreaming = status === "streaming";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !active || isStreaming) return;
    const text = input;
    setInput("");
    await send(text, { cards });
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
          <ChatStream
            messages={messages}
            isStreaming={isStreaming}
            moduleActive={active}
          />
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
          placeholder={placeholderHint}
          disabled={!active || isStreaming}
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
            disabled={!active || !input.trim()}
            title="发送"
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
      </form>
    </div>
  );
}
