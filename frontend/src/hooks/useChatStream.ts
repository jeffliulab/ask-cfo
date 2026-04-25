/**
 * useChatStream —— v0.1 D5: 重构成"按 module 配置 + 解析多 type DSP".
 *
 * 解析 backend Vercel AI SDK Data Stream Protocol：
 *   - 0:"text"     文本 chunk（JSON-encoded string）
 *   - 2:[{type, ...}]   data part：
 *       - {citations: [...]}                                          既有
 *       - {type:"tool_call", name, input, call_id}                    v0.1 D4 新增
 *       - {type:"tool_result", call_id, summary, meta}                v0.1 D4 新增
 *       - {type:"card", card: WorkspaceCard}                          v0.1 D4 新增
 *   - d:{...}      finish part
 *   - 3:"err"      错误 part
 *
 * Hook 接受一个 ``StreamConfig``，决定 endpoint / request body / 关联的
 * moduleId（card 流式注入 workspaceStore 的命名空间）。
 *
 * 默认配置（``defaultChatConfig``）走 ``/api/v1/chat/stream``，body 为 v0.0
 * 形态 ``{message, cards, citations}``，moduleId="bookkeeping" 占位（未来调用方
 * 可显式覆盖）。
 */

"use client";

import { useCallback, useRef, useState } from "react";

import {
  useWorkspaceStore,
} from "@/stores/workspaceStore";
import type { Citation } from "@/types/citation";
import type { ModuleId, WorkspaceCard } from "@/types/workspace";
import type {
  AgentTraceEvent,
  ChatMessage,
  ChatStreamStatus,
} from "@/types/chat";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type StreamConfig = {
  /** 调用的 endpoint，相对于 ``NEXT_PUBLIC_API_URL`` */
  endpoint: string;
  /** 把用户输入 + options 转成 backend body */
  buildBody: (text: string, options: SendOptions) => unknown;
  /** card / agent_trace 写到哪个 module 的 workspace */
  moduleId: ModuleId;
};

export type SendOptions = {
  cards?: WorkspaceCard[];
  citations?: Citation[];
  history?: unknown[];
};

/** 默认 chat 配置 —— 兼容 v0.0 ChatPanel 用法. */
export const defaultChatConfig: StreamConfig = {
  endpoint: "/api/v1/chat/stream",
  buildBody: (text, opts) => ({
    message: text,
    cards: opts.cards ?? [],
    citations: opts.citations ?? [],
  }),
  moduleId: "bookkeeping", // 占位；调用方应显式传 moduleId
};

/** 法规问答 endpoint 配置. */
export const regulationsQAConfig: StreamConfig = {
  endpoint: "/api/v1/regulations/qa/stream",
  buildBody: (text, opts) => ({
    message: text,
    history: opts.history ?? [],
  }),
  moduleId: "regulations",
};

let _msgCounter = 0;
function newMessageId(): string {
  _msgCounter += 1;
  return `msg-${Date.now()}-${_msgCounter}`;
}

export function useChatStream(config: StreamConfig = defaultChatConfig) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStreamStatus>("idle");
  const abortRef = useRef<AbortController | null>(null);

  const appendCard = useWorkspaceStore((s) => s.appendCard);
  const appendAgentTrace = useWorkspaceStore((s) => s.appendAgentTrace);
  const clearAgentTrace = useWorkspaceStore((s) => s.clearAgentTrace);
  const setModuleStatus = useWorkspaceStore((s) => s.setStatus);

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
    async (text: string, options: SendOptions = {}) => {
      const trimmed = text.trim();
      if (!trimmed || status === "streaming") return;

      // Push user message + assistant 占位
      const userMsg: ChatMessage = {
        id: newMessageId(),
        role: "user",
        content: trimmed,
      };
      const assistantId = newMessageId();
      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: assistantId, role: "assistant", content: "" },
      ]);

      // 清空当前 module 的 agent trace（新一轮提问开始）
      clearAgentTrace(config.moduleId);
      setModuleStatus(config.moduleId, "loading");
      setStatus("streaming");

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const resp = await fetch(`${API_BASE_URL}${config.endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(config.buildBody(trimmed, options)),
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

          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line) continue;
            const colonAt = line.indexOf(":");
            if (colonAt < 0) continue;
            const prefix = line.slice(0, colonAt);
            const payloadStr = line.slice(colonAt + 1);

            if (prefix === "0") {
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
              try {
                const arr = JSON.parse(payloadStr) as Array<
                  | { citations: Citation[] }
                  | {
                      type: "tool_call";
                      name: string;
                      input: Record<string, unknown>;
                      call_id: string;
                    }
                  | {
                      type: "tool_result";
                      call_id: string;
                      summary: string;
                      meta: Record<string, unknown>;
                    }
                  | { type: "card"; card: WorkspaceCard }
                >;
                const entry = arr[0];
                if (!entry) continue;

                if ("citations" in entry) {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId
                        ? { ...m, citations: entry.citations }
                        : m,
                    ),
                  );
                } else if (entry.type === "tool_call") {
                  const ev: AgentTraceEvent = {
                    kind: "tool_call",
                    callId: entry.call_id,
                    name: entry.name,
                    input: entry.input,
                    ts: Date.now(),
                  };
                  appendAgentTrace(config.moduleId, ev);
                } else if (entry.type === "tool_result") {
                  const ev: AgentTraceEvent = {
                    kind: "tool_result",
                    callId: entry.call_id,
                    summary: entry.summary,
                    meta: entry.meta,
                    ts: Date.now(),
                  };
                  appendAgentTrace(config.moduleId, ev);
                } else if (entry.type === "card") {
                  appendCard(config.moduleId, entry.card);
                }
              } catch {
                /* skip */
              }
            } else if (prefix === "d") {
              setStatus("done");
              setModuleStatus(config.moduleId, "ready");
            } else if (prefix === "3") {
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
                setModuleStatus(config.moduleId, "error", errMsg);
              } catch {
                /* skip */
              }
            }
          }
        }

        if (status !== "error") {
          setStatus("done");
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "未知错误";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, role: "error", content: message }
              : m,
          ),
        );
        setStatus("error");
        setModuleStatus(config.moduleId, "error", message);
      } finally {
        abortRef.current = null;
      }
    },
    [
      status,
      config,
      appendCard,
      appendAgentTrace,
      clearAgentTrace,
      setModuleStatus,
    ],
  );

  return { messages, status, send, stop, reset };
}
