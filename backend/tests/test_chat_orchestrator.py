"""Tests for backend/services/chat/orchestrator.py.

Splits coverage：
- _prepare_node：纯 prompt 渲染，无 mock
- ChatOrchestrator.stream：mock Anthropic AsyncAnthropic（streaming context manager + text_stream）
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.config import LLMProviderType
from backend.interfaces import Citation
from backend.services.chat.orchestrator import (
    ChatChunk,
    ChatOrchestrator,
    ChatRequest,
    _prepare_node,
)


class TestPrepareNode:
    def test_renders_system_and_user_prompts(self) -> None:
        state = {
            "user_message": "这笔餐饮发票能抵扣进项税吗？",
            "cards": [
                {
                    "workspace_id": "voucher-2026-04-24-001",
                    "title": "凭证草稿",
                    "card_type": "voucher_draft",
                    "payload": {
                        "vendor": "某某餐饮有限公司",
                        "amount": 530.00,
                        "tax": 30.00,
                        "summary": "员工聚餐 5 人",
                    },
                },
            ],
            "citations": [
                {
                    "label": "[1]",
                    "source_name": "《增值税暂行条例》第 10 条",
                    "url": "http://example.com/vat",
                }
            ],
        }
        result = _prepare_node(state)
        assert "rendered_system" in result
        assert "rendered_prompt" in result
        # system prompt 关键词（CFO 助手）
        assert "agent-as-a-cfo" in result["rendered_system"]
        assert "[N]" in result["rendered_system"]
        # follow_up 包含工作区 + 引用 + 用户问题
        prompt = result["rendered_prompt"]
        assert "餐饮发票" in prompt
        assert "voucher_draft" in prompt
        assert "[1]" in prompt
        assert "增值税暂行条例" in prompt

    def test_handles_empty_cards_and_citations(self) -> None:
        state = {"user_message": "你好", "cards": [], "citations": []}
        result = _prepare_node(state)
        assert "你好" in result["rendered_prompt"]


# === ChatOrchestrator streaming ===
class _FakeAnthropicStream:
    """Mocks ``async with client.messages.stream(...) as stream`` 的最小行为."""

    def __init__(self, chunks: list[str], finish_reason: str = "stop") -> None:
        self._chunks = chunks
        self._finish_reason = finish_reason

    async def __aenter__(self) -> "_FakeAnthropicStream":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    @property
    def text_stream(self) -> AsyncIterator[str]:
        async def gen() -> AsyncIterator[str]:
            for c in self._chunks:
                yield c

        return gen()

    async def get_final_message(self) -> Any:
        msg = MagicMock()
        msg.stop_reason = self._finish_reason
        return msg


class _FakeAsyncAnthropic:
    """Drop-in for anthropic.AsyncAnthropic with a controllable stream."""

    def __init__(self, chunks: list[str], finish_reason: str = "stop") -> None:
        self._chunks = chunks
        self._finish_reason = finish_reason
        self.messages = MagicMock()
        # `messages.stream(...)` 必须返回 _FakeAnthropicStream（NOT awaited，是 sync 工厂）
        self.messages.stream = MagicMock(
            return_value=_FakeAnthropicStream(self._chunks, self._finish_reason)
        )


@pytest.fixture
def orchestrator_with_chunks() -> Any:
    def _factory(chunks: list[str], finish_reason: str = "stop") -> ChatOrchestrator:
        # 跳过 Settings 校验：直接造对象再注入
        orch = ChatOrchestrator.__new__(ChatOrchestrator)
        orch._settings = MagicMock()
        orch._settings.temperature = 0.5
        orch._provider = LLMProviderType.ANTHROPIC
        orch._client = _FakeAsyncAnthropic(chunks, finish_reason)
        orch._model = "claude-test"
        return orch

    return _factory


class TestStream:
    @pytest.mark.asyncio
    async def test_emits_delta_chunks_then_finish(
        self, orchestrator_with_chunks
    ) -> None:
        orch = orchestrator_with_chunks(["Hello, ", "world", "!"])
        request = ChatRequest(
            message="hi",
            cards=[],
            citations=[Citation(label="[1]", source_name="src", url="http://x")],
        )
        chunks: list[ChatChunk] = []
        async for chunk in orch.stream(request):
            chunks.append(chunk)

        # 3 个 delta + 1 个 finish
        assert len(chunks) == 4
        assert [c.type for c in chunks] == ["delta", "delta", "delta", "finish"]
        assert "".join(c.content for c in chunks if c.type == "delta") == "Hello, world!"
        # finish chunk 携带 citations
        finish = chunks[-1]
        assert finish.finish_reason == "stop"
        assert finish.citations is not None
        assert finish.citations[0].label == "[1]"

    @pytest.mark.asyncio
    async def test_no_chunks_still_yields_finish(self, orchestrator_with_chunks) -> None:
        orch = orchestrator_with_chunks([], finish_reason="end_turn")
        request = ChatRequest(message="hi", cards=[], citations=[])
        chunks = [c async for c in orch.stream(request)]
        assert len(chunks) == 1
        assert chunks[0].type == "finish"
        assert chunks[0].finish_reason == "end_turn"


# === OpenAI / DeepSeek path ===
class _FakeOpenAIChunk:
    """Mocks one chunk from openai client.chat.completions.create stream."""

    def __init__(self, content: str | None, finish_reason: str | None = None) -> None:
        delta = MagicMock()
        delta.content = content
        choice = MagicMock()
        choice.delta = delta
        choice.finish_reason = finish_reason
        self.choices = [choice]


async def _fake_openai_stream(chunks: list[_FakeOpenAIChunk]) -> AsyncIterator[_FakeOpenAIChunk]:
    for c in chunks:
        yield c


class _FakeAsyncOpenAI:
    """Drop-in for openai.AsyncOpenAI."""

    def __init__(self, chunks: list[_FakeOpenAIChunk]) -> None:
        self._chunks = chunks
        self.chat = MagicMock()
        self.chat.completions = MagicMock()

        async def _create(**_: Any) -> AsyncIterator[_FakeOpenAIChunk]:
            return _fake_openai_stream(self._chunks)

        self.chat.completions.create = _create  # type: ignore[assignment]


@pytest.fixture
def openai_orchestrator() -> Any:
    def _factory(chunks: list[_FakeOpenAIChunk]) -> ChatOrchestrator:
        orch = ChatOrchestrator.__new__(ChatOrchestrator)
        orch._settings = MagicMock()
        orch._settings.temperature = 0.5
        orch._provider = LLMProviderType.OPENAI
        orch._client = _FakeAsyncOpenAI(chunks)
        orch._model = "gpt-test"
        return orch

    return _factory


class TestOpenAIStream:
    @pytest.mark.asyncio
    async def test_streams_deltas_and_finishes(self, openai_orchestrator) -> None:
        chunks = [
            _FakeOpenAIChunk("Hello, "),
            _FakeOpenAIChunk("world"),
            _FakeOpenAIChunk("!", finish_reason="stop"),
        ]
        orch = openai_orchestrator(chunks)
        request = ChatRequest(
            message="hi",
            cards=[],
            citations=[Citation(label="[1]", source_name="src", url="http://x")],
        )
        out = [c async for c in orch.stream(request)]
        # 3 deltas + finish
        assert len(out) == 4
        assert [c.type for c in out[:3]] == ["delta"] * 3
        assert "".join(c.content for c in out[:3]) == "Hello, world!"
        assert out[-1].type == "finish"
        assert out[-1].finish_reason == "stop"
        assert out[-1].citations is not None
        assert out[-1].citations[0].label == "[1]"

    @pytest.mark.asyncio
    async def test_skips_empty_delta(self, openai_orchestrator) -> None:
        chunks = [
            _FakeOpenAIChunk(None),  # 没 content，跳过
            _FakeOpenAIChunk("text", finish_reason="stop"),
        ]
        orch = openai_orchestrator(chunks)
        request = ChatRequest(message="hi", cards=[], citations=[])
        out = [c async for c in orch.stream(request)]
        # 1 delta + 1 finish
        assert len(out) == 2
        assert out[0].type == "delta"
        assert out[0].content == "text"
        assert out[1].type == "finish"


# === Ollama path ===
class _FakeOllamaResponse:
    def __init__(self, lines: list[str], status_code: int = 200) -> None:
        self._lines = lines
        self.status_code = status_code

    async def __aenter__(self) -> "_FakeOllamaResponse":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line

    async def aread(self) -> bytes:
        return b"\n".join(line.encode() for line in self._lines)


class _FakeOllamaClient:
    """Drop-in for httpx.AsyncClient."""

    def __init__(self, lines: list[str], status_code: int = 200) -> None:
        self._lines = lines
        self._status_code = status_code

    def stream(self, method: str, url: str, **_: Any) -> _FakeOllamaResponse:  # noqa: ARG002
        return _FakeOllamaResponse(self._lines, status_code=self._status_code)


@pytest.fixture
def ollama_orchestrator() -> Any:
    def _factory(lines: list[str], status_code: int = 200) -> ChatOrchestrator:
        orch = ChatOrchestrator.__new__(ChatOrchestrator)
        orch._settings = MagicMock()
        orch._settings.temperature = 0.5
        orch._provider = LLMProviderType.OLLAMA
        orch._client = _FakeOllamaClient(lines, status_code=status_code)
        orch._model = "llama-test"
        return orch

    return _factory


class TestOllamaStream:
    @pytest.mark.asyncio
    async def test_streams_ndjson_chunks(self, ollama_orchestrator) -> None:
        lines = [
            '{"model":"x","message":{"role":"assistant","content":"Hello, "},"done":false}',
            '{"model":"x","message":{"role":"assistant","content":"茅台"},"done":false}',
            '{"model":"x","done":true,"done_reason":"stop"}',
        ]
        orch = ollama_orchestrator(lines)
        request = ChatRequest(message="hi", cards=[], citations=[])
        out = [c async for c in orch.stream(request)]
        assert [c.type for c in out] == ["delta", "delta", "finish"]
        assert out[0].content == "Hello, "
        assert out[1].content == "茅台"
        assert out[-1].finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_handles_non_200_status(self, ollama_orchestrator) -> None:
        orch = ollama_orchestrator(["model not found"], status_code=404)
        request = ChatRequest(message="hi", cards=[], citations=[])
        out = [c async for c in orch.stream(request)]
        assert out[0].type == "error"
        assert "404" in out[0].content

    @pytest.mark.asyncio
    async def test_skips_malformed_json_line(self, ollama_orchestrator) -> None:
        lines = [
            '{"model":"x","message":{"role":"assistant","content":"hi"},"done":false}',
            "this is not JSON",
            '{"model":"x","done":true}',
        ]
        orch = ollama_orchestrator(lines)
        request = ChatRequest(message="hi", cards=[], citations=[])
        out = [c async for c in orch.stream(request)]
        # 1 delta（"hi") + 1 finish (因 done=true)；malformed line 跳过不抛
        assert [c.type for c in out] == ["delta", "finish"]
        assert out[0].content == "hi"
