/**
 * Base API client —— 包 fetch + 错误处理 + base URL.
 *
 * 按 stacks/frontend.md：组件不直接 fetch，所有外部请求集中走 services/.
 *
 * NEXT_PUBLIC_API_URL 在 .env.local 配；默认指 localhost:8000（backend FastAPI 默认端口）.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

type FetchOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  signal?: AbortSignal;
};

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const { method = "GET", body, signal } = options;

  let resp: Response;
  try {
    resp = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    // Network error / CORS / backend down
    throw new ApiError(0, `网络请求失败：${(err as Error).message}`);
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const errBody = (await resp.json()) as { detail?: string };
      if (errBody.detail) detail = errBody.detail;
    } catch {
      // body 不是 JSON，吃掉
    }
    throw new ApiError(resp.status, detail);
  }

  return (await resp.json()) as T;
}
