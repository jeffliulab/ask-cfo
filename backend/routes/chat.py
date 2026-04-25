"""Chat endpoint —— /api/v1/chat/stream（SSE，Vercel AI SDK Data Stream Protocol）.

为什么用 Vercel AI SDK 协议：
- 前端用 ``@ai-sdk/react`` 的 ``useChat`` hook 开箱即用，省 1-2 天 SSE 联调
- 协议格式简单，行级前缀 + JSON：
    - ``0:"text"``     文本 chunk（JSON-encoded string）
    - ``2:[{...}]``    数据 part（JSON 数组）—— 用来传 citations
    - ``d:{...}``      finish part（含 finishReason / usage）
    - ``3:"err"``      错误 part

参考：https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#data-stream-protocol
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.interfaces import Citation
from backend.services.chat.orchestrator import ChatChunk, ChatOrchestrator, ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# === Pydantic request schema ===
class CitationIn(BaseModel):
    label: str
    source_name: str
    url: str


class ChatStreamRequest(BaseModel):
    """``POST /api/v1/chat/stream`` 请求体."""

    message: str = Field(..., description="用户当前这条消息")
    cards: list[dict] = Field(default_factory=list, description="工作区当前卡片快照")
    citations: list[CitationIn] = Field(
        default_factory=list, description="工作区已知的引用源（[N] → URL 映射）"
    )


# === AI SDK Data Stream Protocol 编码 ===
def _encode_text_part(text: str) -> bytes:
    return f"0:{json.dumps(text, ensure_ascii=False)}\n".encode()


def _encode_data_part(data: list[dict]) -> bytes:
    return f"2:{json.dumps(data, ensure_ascii=False)}\n".encode()


def _encode_finish_part(reason: Literal["stop", "max_tokens", "error"]) -> bytes:
    return f"d:{json.dumps({'finishReason': reason, 'usage': {}}, ensure_ascii=False)}\n".encode()


def _encode_error_part(msg: str) -> bytes:
    return f"3:{json.dumps(msg, ensure_ascii=False)}\n".encode()


async def _stream_to_ai_sdk(
    chunk_iter: AsyncIterator[ChatChunk],
) -> AsyncIterator[bytes]:
    """ChatChunk 流 → AI SDK Data Stream Protocol 字节流。"""
    async for chunk in chunk_iter:
        if chunk.type == "delta":
            yield _encode_text_part(chunk.content)
        elif chunk.type == "finish":
            # 先发 citations 数据 part
            if chunk.citations:
                yield _encode_data_part(
                    [{"citations": [asdict(c) for c in chunk.citations]}]
                )
            yield _encode_finish_part(chunk.finish_reason or "stop")  # type: ignore[arg-type]
        elif chunk.type == "error":
            yield _encode_error_part(chunk.content)
            yield _encode_finish_part("error")


@router.post("/stream", summary="Stream chat completion (Vercel AI SDK Data Stream Protocol)")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    """流式 chat —— 输入用户消息 + 工作区快照，返回 AI SDK Data Stream。

    前端用：
        const { messages, sendMessage } = useChat({
            api: 'http://localhost:8000/api/v1/chat/stream',
            // streamProtocol 默认就是 'data'
        })
    """
    try:
        orchestrator = ChatOrchestrator()
    except ValueError as exc:
        # ANTHROPIC_API_KEY 未设置等
        logger.error("ChatOrchestrator init failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    chat_request = ChatRequest(
        message=request.message,
        cards=request.cards,
        citations=[Citation(**c.model_dump()) for c in request.citations],
    )

    return StreamingResponse(
        _stream_to_ai_sdk(orchestrator.stream(chat_request)),
        media_type="text/plain; charset=utf-8",
        headers={"x-vercel-ai-data-stream": "v1"},
    )
