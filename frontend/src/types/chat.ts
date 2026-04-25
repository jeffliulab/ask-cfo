/**
 * Chat message types —— frontend 内部用的简化模型.
 *
 * 不直接复用 Vercel AI SDK 的 UIMessage —— 我们自己解析 backend 的
 * Data Stream Protocol（0:"text" / 2:[{...}] / d:{...}），格式更简单.
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
