/**
 * useChatStream —— 自写的 chat hook，解析 backend 输出的 Vercel AI SDK
 * Data Stream Protocol：
 *   - 0:"text"     文本 chunk（JSON-encoded string）
 *   - 2:[{...}]    数据 part（含 citations）
 *   - d:{...}      finish part
 *   - 3:"err"      错误 part
 *
 * 不用 @ai-sdk/react 的 useChat 是因为 backend ChatStreamRequest 形状是
 * `{message, cards, citations}` 而 useChat 默认发 `{messages: [...]}`，
 * 转译成本不如自己写 80 行直接.
 */

"use client";

import { useCallback, useRef, useState } from "react";

import type { Citation } from "@/types/citation";
import type { WorkspaceCard } from "@/types/workspace";
import type { ChatMessage, ChatStreamStatus } from "@/types/chat";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type SendOptions = {
  cards: WorkspaceCard[];
  citations: Citation[];
};

let _msgCounter = 0;
function newMessageId(): string {
  _msgCounter += 1;
  return `msg-${Date.now()}-${_msgCounter}`;
}

export function useChatStream() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStreamStatus>("idle");
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setMessages([]);
    setStatus("idle");
  }, []);

  const stop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setStatus("done");
  }, []);

  const send = useCallback(
    async (text: string, options: SendOptions) => {
      const trimmed = text.trim();
      if (!trimmed || status === "streaming") return;

      // 先 push user message
      const userMsg: ChatMessage = {
        id: newMessageId(),
        role: "user",
        content: trimmed,
      };
      setMessages((prev) => [...prev, userMsg]);

      // 准备 assistant message 占位
      const assistantId = newMessageId();
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: "" },
      ]);

      setStatus("streaming");

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const resp = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: trimmed,
            cards: options.cards,
            citations: options.citations,
          }),
          signal: controller.signal,
        });

        if (!resp.ok) {
          let detail = `HTTP ${resp.status}`;
          try {
            const j = (await resp.json()) as { detail?: string };
            if (j.detail) detail = j.detail;
          } catch {
            /* ignore */
          }
          throw new Error(detail);
        }

        const reader = resp.body?.getReader();
        if (!reader) throw new Error("response body 不支持流式读取");
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // 按换行切；最后一段可能不完整，留在 buffer
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line) continue;
            const colonAt = line.indexOf(":");
            if (colonAt < 0) continue;
            const prefix = line.slice(0, colonAt);
            const payloadStr = line.slice(colonAt + 1);

            if (prefix === "0") {
              // text part: JSON-encoded string
              try {
                const text = JSON.parse(payloadStr) as string;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: m.content + text }
                      : m,
                  ),
                );
              } catch {
                /* skip malformed */
              }
            } else if (prefix === "2") {
              // data part: JSON array; 我们约定 [{citations: [...]}]
              try {
                const arr = JSON.parse(payloadStr) as Array<{
                  citations?: Citation[];
                }>;
                const citations = arr[0]?.citations;
                if (citations) {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId ? { ...m, citations } : m,
                    ),
                  );
                }
              } catch {
                /* skip */
              }
            } else if (prefix === "d") {
              // finish part — 流结束
              setStatus("done");
            } else if (prefix === "3") {
              // error part
              try {
                const errMsg = JSON.parse(payloadStr) as string;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, role: "error", content: errMsg }
                      : m,
                  ),
                );
                setStatus("error");
              } catch {
                /* skip */
              }
            }
          }
        }

        // 流结束但没看到 d: 也视为 done
        if (status !== "error") setStatus("done");
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "未知错误";
        // 把占位 assistant 替为 error
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, role: "error", content: message }
              : m,
          ),
        );
        setStatus("error");
      } finally {
        abortRef.current = null;
      }
    },
    [status],
  );

  return { messages, status, send, stop, reset };
}
