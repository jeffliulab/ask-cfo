"""Chat endpoint —— ``/api/v1/chat/stream``（SSE，Vercel AI SDK Data Stream Protocol）.

为什么用 Vercel AI SDK 协议：
- 前端用 ``@ai-sdk/react`` 的 ``useChat`` hook 开箱即用
- 协议格式简单，行级前缀 + JSON

DSP 编码器抽到 [`_dsp.py`](_dsp.py) 共用 —— v0.1 法规问答 + 后续模块都复用。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.interfaces import Citation
from backend.routes._dsp import (
    encode_citations,
    encode_error_part,
    encode_finish_part,
    encode_text_part,
)
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


async def _stream_to_ai_sdk(
    chunk_iter: AsyncIterator[ChatChunk],
) -> AsyncIterator[bytes]:
    """ChatChunk 流 → AI SDK Data Stream Protocol 字节流。"""
    async for chunk in chunk_iter:
        if chunk.type == "delta":
            yield encode_text_part(chunk.content)
        elif chunk.type == "finish":
            if chunk.citations:
                yield encode_citations(chunk.citations)
            yield encode_finish_part(chunk.finish_reason or "stop")  # type: ignore[arg-type]
        elif chunk.type == "error":
            yield encode_error_part(chunk.content)
            yield encode_finish_part("error")


@router.post("/stream", summary="Stream chat completion (Vercel AI SDK Data Stream Protocol)")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    """流式 chat —— 输入用户消息 + 工作区快照，返回 AI SDK Data Stream。"""
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
