/**
 * Chat message + agent trace types —— v0.1 D5.
 *
 * 不直接复用 Vercel AI SDK 的 UIMessage —— 我们自己解析 backend 的
 * Data Stream Protocol（0:"text" / 2:[{type:..., ...}] / d:{...}），格式更简单.
 */

import type { Citation } from "./citation";

export type ChatRole = "user" | "assistant" | "error";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  /** 主体文本；assistant 流式追加；error 时是错误描述 */
  content: string;
  /** 仅 assistant 消息有；从 backend finish chunk 的 data part 解析得到 */
  citations?: Citation[];
};

export type ChatStreamStatus = "idle" | "streaming" | "done" | "error";

/** Agent trace 事件 —— backend ``2:[{type:"tool_call"|"tool_result", ...}]`` 解析得到. */
export type AgentTraceEvent =
  | {
      kind: "tool_call";
      callId: string;
      name: string;
      input: Record<string, unknown>;
      ts: number;
    }
  | {
      kind: "tool_result";
      callId: string;
      summary: string;
      meta: Record<string, unknown>;
      ts: number;
    };
