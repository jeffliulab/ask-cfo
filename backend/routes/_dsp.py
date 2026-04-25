"""Vercel AI SDK Data Stream Protocol 编码器 —— v0.1 D4 抽出共用.

参考：https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#data-stream-protocol

行级前缀：
- ``0:"text"``      文本 chunk（JSON-encoded string）
- ``2:[{...}]``     数据 part（JSON 数组）
- ``d:{...}``       finish part（含 finishReason / usage）
- ``3:"err"``       错误 part

v0.1 起在 ``2:`` data part 内**约定 type tag**承载多种事件类型：
- ``[{"citations": [...]}]``                既有
- ``[{"type":"tool_call", "name":"...", "input":{...}, "call_id":"..."}]``
- ``[{"type":"tool_result", "call_id":"...", "summary":"...", "meta":{...}}]``
- ``[{"type":"card", "card": {...}}]``
- v0.5 起加 ``plan_step`` / ``step_status``

为什么不引入新前缀：保留与 Vercel AI SDK ``useChat`` 协议兼容，前端只需在
``2:`` 分支按 ``arr[0].type`` 路由到不同 reducer 即可。
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Literal

FinishReason = Literal["stop", "max_tokens", "max_rounds", "error", "tool_use"]


def _to_jsonable(obj: Any) -> Any:
    """递归把 dataclass 转 dict（嵌套 dataclass 也展开）."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    return obj


def encode_text_part(text: str) -> bytes:
    return f"0:{json.dumps(text, ensure_ascii=False)}\n".encode()


def encode_data_part(data: list[dict[str, Any]]) -> bytes:
    """通用 ``2:`` data part —— 调用方传 dict list."""
    return f"2:{json.dumps(_to_jsonable(data), ensure_ascii=False)}\n".encode()


def encode_finish_part(reason: FinishReason) -> bytes:
    return f"d:{json.dumps({'finishReason': reason, 'usage': {}}, ensure_ascii=False)}\n".encode()


def encode_error_part(msg: str) -> bytes:
    return f"3:{json.dumps(msg, ensure_ascii=False)}\n".encode()


# === v0.1 type-tagged data parts（约定）===
def encode_citations(citations: list[Any]) -> bytes:
    """``2:[{"citations": [...]}]`` —— 沿用 v0.0 既有约定."""
    return encode_data_part([{"citations": _to_jsonable(citations)}])


def encode_tool_call(
    *, name: str, input: dict[str, Any], call_id: str
) -> bytes:
    """``2:[{"type":"tool_call", ...}]`` —— v0.1 D4 加."""
    return encode_data_part(
        [
            {
                "type": "tool_call",
                "name": name,
                "input": input,
                "call_id": call_id,
            }
        ]
    )


def encode_tool_result(
    *, call_id: str, summary: str, meta: dict[str, Any] | None = None
) -> bytes:
    """``2:[{"type":"tool_result", ...}]`` —— v0.1 D4 加."""
    return encode_data_part(
        [
            {
                "type": "tool_result",
                "call_id": call_id,
                "summary": summary,
                "meta": meta or {},
            }
        ]
    )


def encode_card(card: Any) -> bytes:
    """``2:[{"type":"card", "card": {...}}]`` —— v0.1 D4 加。
    card 可以是 dataclass 或 dict。
    """
    return encode_data_part([{"type": "card", "card": _to_jsonable(card)}])
