"""Regulations Q&A endpoint —— ``POST /api/v1/regulations/qa/stream``.

v0.1 法规问答主路由。RegulationAgent 多轮 tool_use 的 AgentEvent 流 →
Vercel AI SDK DSP（含 v0.1 D4 新增的 tool_call / tool_result / card type tags）。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.routes._dsp import (
    encode_card,
    encode_citations,
    encode_error_part,
    encode_finish_part,
    encode_text_part,
    encode_tool_call,
    encode_tool_result,
)
from backend.services.chat.orchestrator import ChatOrchestrator
from backend.services.regulatory.regulation_agent import (
    AgentEvent,
    RegulationAgent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/regulations", tags=["regulations"])


class RegulationQARequest(BaseModel):
    """``POST /api/v1/regulations/qa/stream`` 请求体."""

    message: str = Field(..., min_length=1, description="用户的法规问题")
    history: list[dict] = Field(
        default_factory=list,
        description="先前对话历史；v0.1 仅 single-turn，传空数组即可",
    )


async def _stream_to_ai_sdk(events: AsyncIterator[AgentEvent]) -> AsyncIterator[bytes]:
    """AgentEvent → DSP bytes."""
    async for ev in events:
        if ev.type == "text":
            if ev.content:
                yield encode_text_part(ev.content)
        elif ev.type == "tool_call":
            yield encode_tool_call(
                name=ev.tool_name,
                input=ev.tool_input,
                call_id=ev.tool_call_id,
            )
        elif ev.type == "tool_result":
            yield encode_tool_result(
                call_id=ev.tool_call_id,
                summary=ev.tool_result_summary,
                meta=ev.tool_result_meta,
            )
        elif ev.type == "card":
            if ev.card is not None:
                yield encode_card(ev.card)
        elif ev.type == "finish":
            if ev.citations:
                yield encode_citations(ev.citations)
            yield encode_finish_part(ev.finish_reason or "stop")  # type: ignore[arg-type]
        elif ev.type == "error":
            yield encode_error_part(ev.content)


@router.post(
    "/qa/stream",
    summary="法规问答 streaming（agent search + tool_use）",
)
async def regulation_qa_stream(request: RegulationQARequest) -> StreamingResponse:
    try:
        orchestrator = ChatOrchestrator()
    except ValueError as exc:
        logger.error("ChatOrchestrator init failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    agent = RegulationAgent(orchestrator)
    return StreamingResponse(
        _stream_to_ai_sdk(agent.stream(request.message, request.history or None)),
        media_type="text/plain; charset=utf-8",
        headers={"x-vercel-ai-data-stream": "v1"},
    )
