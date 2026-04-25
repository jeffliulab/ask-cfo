"""Tests for backend/routes/chat.py.

Splits coverage：
- AI SDK Data Stream Protocol 编码（_encode_text_part / _encode_data_part / _encode_finish_part）
- POST /api/v1/chat/stream 端到端：mock 整个 ChatOrchestrator
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.interfaces import Citation
from backend.main import create_app
from backend.routes._dsp import (
    encode_data_part as _encode_data_part,
    encode_finish_part as _encode_finish_part,
    encode_text_part as _encode_text_part,
)
from backend.services.chat.orchestrator import ChatChunk


# === 协议编码 ===
class TestProtocolEncoders:
    def test_text_part_json_escapes_quotes(self) -> None:
        assert _encode_text_part('hi "world"') == b'0:"hi \\"world\\""\n'

    def test_text_part_chinese_passthrough(self) -> None:
        # ensure_ascii=False，中文不转义
        assert _encode_text_part("你好") == '0:"你好"\n'.encode()

    def test_data_part_emits_array(self) -> None:
        out = _encode_data_part([{"citations": [{"label": "[1]"}]}])
        assert out.startswith(b"2:")
        assert out.endswith(b"\n")
        body = json.loads(out[2:-1])
        assert body[0]["citations"][0]["label"] == "[1]"

    @pytest.mark.parametrize("reason", ["stop", "max_tokens", "error"])
    def test_finish_part_includes_finish_reason(self, reason: str) -> None:
        out = _encode_finish_part(reason)  # type: ignore[arg-type]
        assert out.startswith(b"d:")
        body = json.loads(out[2:-1])
        assert body["finishReason"] == reason


# === 端到端 ===
@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(create_app())


async def _fake_chunks() -> AsyncIterator[ChatChunk]:
    yield ChatChunk(type="delta", content="Hello, ")
    yield ChatChunk(type="delta", content="茅台")
    yield ChatChunk(
        type="finish",
        citations=[Citation(label="[1]", source_name="AKShare", url="http://x/1")],
        finish_reason="stop",
    )


class _FakeOrchestrator:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def stream(self, request: Any) -> AsyncIterator[ChatChunk]:
        return _fake_chunks()


class TestChatStreamEndpoint:
    def test_happy_path_emits_protocol_lines(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # patch ChatOrchestrator 在 chat route 模块里的引用
        with patch("backend.routes.chat.ChatOrchestrator", _FakeOrchestrator):
            resp = client.post(
                "/api/v1/chat/stream",
                json={"message": "现金流为何下滑", "cards": [], "citations": []},
            )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        assert resp.headers.get("x-vercel-ai-data-stream") == "v1"

        body = resp.text
        # 三段：两个 text part + 一个 data part + 一个 finish part
        lines = [l for l in body.split("\n") if l]
        assert lines[0] == '0:"Hello, "'
        assert lines[1] == '0:"茅台"'
        assert lines[2].startswith("2:")  # citations data
        assert lines[3].startswith("d:")  # finish
        assert "[1]" in lines[2]
        assert "AKShare" in lines[2]

    def test_init_failure_returns_503(self, client: TestClient) -> None:
        # 显式让 ChatOrchestrator() 抛 ValueError —— 模拟 API key 缺失场景
        # 不依赖实际 env 状态（dev 机器上可能配了某个 provider key）
        def _raise_init(*args: Any, **kwargs: Any) -> None:
            raise ValueError("ANTHROPIC_API_KEY 未设置（LLM_PROVIDER=anthropic）")

        with patch(
            "backend.routes.chat.ChatOrchestrator", side_effect=_raise_init
        ):
            resp = client.post(
                "/api/v1/chat/stream",
                json={"message": "hi", "cards": [], "citations": []},
            )
        assert resp.status_code == 503
        assert "ANTHROPIC_API_KEY" in resp.json()["detail"]
