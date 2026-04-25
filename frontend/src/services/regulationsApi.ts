/**
 * Regulations API service —— v0.1 D5.
 *
 * v0.1 仅一个流式端点（/api/v1/regulations/qa/stream），由 useChatStream +
 * regulationsQAConfig 直接消费；本文件留给后续 non-streaming 辅助 API
 * （如批量预热 / 健康检查），目前作为占位 + 文档。
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** 调试用：检查 backend 法规库是否就绪。 */
export async function checkRegulationsHealth(): Promise<{
  ok: boolean;
  detail?: string;
}> {
  try {
    const resp = await fetch(`${API_BASE_URL}/healthz`, { method: "GET" });
    if (!resp.ok) return { ok: false, detail: `HTTP ${resp.status}` };
    return { ok: true };
  } catch (err) {
    return {
      ok: false,
      detail: err instanceof Error ? err.message : String(err),
    };
  }
}
