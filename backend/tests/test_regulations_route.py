"""Tests for backend/routes/regulations.py.

覆盖：
- DSP 编码器正确性（_dsp.py）
- POST /api/v1/regulations/qa/stream 端到端（mock RegulationAgent）
- SSE 字段顺序：text → tool_call → tool_result → card → citations → finish
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.interfaces import Citation, RegulationSnippetPayload, WorkspaceCard
from backend.main import create_app
from backend.routes._dsp import (
    encode_card,
    encode_citations,
    encode_data_part,
    encode_error_part,
    encode_finish_part,
    encode_text_part,
    encode_tool_call,
    encode_tool_result,
)
from backend.services.regulatory.regulation_agent import AgentEvent


# === DSP 编码器单元测试 ===
class TestDSPEncoders:
    def test_text_part_chinese_passthrough(self) -> None:
        out = encode_text_part("你好")
        assert out == '0:"你好"\n'.encode()

    def test_text_part_escapes_quotes(self) -> None:
        out = encode_text_part('hi "world"')
        assert out == b'0:"hi \\"world\\""\n'

    def test_data_part_emits_array(self) -> None:
        out = encode_data_part([{"foo": "bar"}])
        assert out.startswith(b"2:")
        assert out.endswith(b"\n")
        body = json.loads(out[2:-1])
        assert body == [{"foo": "bar"}]

    def test_finish_part_includes_finish_reason(self) -> None:
        out = encode_finish_part("max_rounds")
        body = json.loads(out[2:-1])
        assert body["finishReason"] == "max_rounds"

    def test_tool_call_format(self) -> None:
        out = encode_tool_call(
            name="search_regulations",
            input={"query": "研发"},
            call_id="toolu_1",
        )
        body = json.loads(out[2:-1])
        assert body[0]["type"] == "tool_call"
        assert body[0]["name"] == "search_regulations"
        assert body[0]["input"] == {"query": "研发"}
        assert body[0]["call_id"] == "toolu_1"

    def test_tool_result_format(self) -> None:
        out = encode_tool_result(
            call_id="toolu_1",
            summary="命中 3 条",
            meta={"hits_count": 3},
        )
        body = json.loads(out[2:-1])
        assert body[0]["type"] == "tool_result"
        assert body[0]["call_id"] == "toolu_1"
        assert body[0]["summary"] == "命中 3 条"
        assert body[0]["meta"] == {"hits_count": 3}

    def test_card_format_dataclass_serialized(self) -> None:
        payload = RegulationSnippetPayload(
            reg_id="cit-rd",
            source_name="财税公告",
            chapter="第一条",
            article_number="第一条",
            summary="100% 加计扣除",
            full_text="完整文本",
            category="CIT",
        )
        card = WorkspaceCard(
            workspace_id="regulation-cit-rd",
            card_type="regulation_snippet",
            title="研发加计扣除",
            payload=payload.__dict__,
            citations=[Citation(label="[1]", source_name="财税公告", url="http://x")],
        )
        out = encode_card(card)
        body = json.loads(out[2:-1])
        assert body[0]["type"] == "card"
        assert body[0]["card"]["card_type"] == "regulation_snippet"
        assert body[0]["card"]["title"] == "研发加计扣除"
        assert body[0]["card"]["payload"]["reg_id"] == "cit-rd"

    def test_citations_format(self) -> None:
        out = encode_citations(
            [Citation(label="[1]", source_name="A", url="http://a")]
        )
        body = json.loads(out[2:-1])
        assert body[0]["citations"][0]["label"] == "[1]"

    def test_error_part(self) -> None:
        out = encode_error_part("oops")
        assert out.startswith(b"3:")
        body = json.loads(out[2:-1])
        assert body == "oops"


# === 端到端 ===
@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(create_app())


async def _fake_events() -> AsyncIterator[AgentEvent]:
    """模拟 agent 一次完整的 search → get → final 流程."""
    yield AgentEvent(
        type="tool_call",
        tool_name="search_regulations",
        tool_input={"query": "研发"},
        tool_call_id="toolu_1",
    )
    yield AgentEvent(
        type="tool_result",
        tool_call_id="toolu_1",
        tool_result_summary="命中 1 条：cit-rd",
        tool_result_meta={"hits_count": 1},
    )
    yield AgentEvent(
        type="tool_call",
        tool_name="get_regulation",
        tool_input={"id": "cit-rd"},
        tool_call_id="toolu_2",
    )
    yield AgentEvent(
        type="tool_result",
        tool_call_id="toolu_2",
        tool_result_summary="读取 cit-rd",
    )
    payload = RegulationSnippetPayload(
        reg_id="cit-rd",
        source_name="财税公告",
        chapter="第一条",
        article_number="第一条",
        summary="100% 加计扣除",
        full_text="...",
        category="CIT",
    )
    yield AgentEvent(
        type="card",
        card=WorkspaceCard(
            workspace_id="regulation-cit-rd",
            card_type="regulation_snippet",
            title="研发加计扣除",
            payload=payload.__dict__,
            citations=[Citation(label="[1]", source_name="财税公告", url="http://x")],
        ),
    )
    yield AgentEvent(type="text", content="研发费用按 100% 加计扣除[1]。")
    yield AgentEvent(
        type="finish",
        citations=[Citation(label="[1]", source_name="财税公告", url="http://x")],
        finish_reason="stop",
    )


class _FakeAgent:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[AgentEvent]:
        return _fake_events()


class _FakeAgentNoCall:
    """No tool call, plain text reply."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def _events(self) -> AsyncIterator[AgentEvent]:
        yield AgentEvent(type="text", content="你好。")
        yield AgentEvent(type="finish", finish_reason="stop", citations=[])

    def stream(self, *args: Any, **kwargs: Any) -> AsyncIterator[AgentEvent]:
        return self._events()


class TestRegulationQAEndpoint:
    def test_full_flow_emits_correct_protocol(self, client: TestClient) -> None:
        # patch agent + orchestrator
        with patch(
            "backend.routes.regulations.RegulationAgent", _FakeAgent
        ), patch("backend.routes.regulations.ChatOrchestrator"):
            resp = client.post(
                "/api/v1/regulations/qa/stream",
                json={"message": "研发加计扣除？"},
            )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        assert resp.headers.get("x-vercel-ai-data-stream") == "v1"

        body = resp.text
        lines = [line for line in body.split("\n") if line]

        # 顺序验证：tool_call → tool_result → tool_call → tool_result → card → text → citations → finish
        # = 8 行（不含 final 结尾）
        assert len(lines) == 8

        # 1. tool_call(search)
        assert lines[0].startswith("2:")
        body0 = json.loads(lines[0][2:])
        assert body0[0]["type"] == "tool_call"
        assert body0[0]["name"] == "search_regulations"

        # 2. tool_result(search)
        body1 = json.loads(lines[1][2:])
        assert body1[0]["type"] == "tool_result"
        assert body1[0]["meta"] == {"hits_count": 1}

        # 3. tool_call(get)
        body2 = json.loads(lines[2][2:])
        assert body2[0]["type"] == "tool_call"
        assert body2[0]["name"] == "get_regulation"

        # 4. tool_result(get)
        body3 = json.loads(lines[3][2:])
        assert body3[0]["type"] == "tool_result"

        # 5. card
        body4 = json.loads(lines[4][2:])
        assert body4[0]["type"] == "card"
        assert body4[0]["card"]["title"] == "研发加计扣除"

        # 6. text delta
        assert lines[5].startswith("0:")
        text_body = json.loads(lines[5][2:])
        assert "[1]" in text_body
        assert "100%" in text_body

        # 7. citations
        body6 = json.loads(lines[6][2:])
        assert body6[0]["citations"][0]["label"] == "[1]"

        # 8. finish
        assert lines[7].startswith("d:")
        finish_body = json.loads(lines[7][2:])
        assert finish_body["finishReason"] == "stop"

    def test_text_only_path(self, client: TestClient) -> None:
        with patch(
            "backend.routes.regulations.RegulationAgent", _FakeAgentNoCall
        ), patch("backend.routes.regulations.ChatOrchestrator"):
            resp = client.post(
                "/api/v1/regulations/qa/stream",
                json={"message": "你好"},
            )
        assert resp.status_code == 200
        lines = [line for line in resp.text.split("\n") if line]
        # text + finish (no citations because empty)
        assert lines[0] == '0:"你好。"'
        assert lines[1].startswith("d:")

    def test_init_failure_returns_503(self, client: TestClient) -> None:
        # ChatOrchestrator init 抛 ValueError → 503
        def _raise(*args: Any, **kwargs: Any) -> None:
            raise ValueError("DEEPSEEK_API_KEY 未设置")

        with patch(
            "backend.routes.regulations.ChatOrchestrator", side_effect=_raise
        ):
            resp = client.post(
                "/api/v1/regulations/qa/stream",
                json={"message": "x"},
            )
        assert resp.status_code == 503
        assert "DEEPSEEK_API_KEY" in resp.json()["detail"]

    def test_empty_message_rejected_by_pydantic(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/regulations/qa/stream",
            json={"message": ""},
        )
        # min_length=1 → Pydantic 422
        assert resp.status_code == 422
