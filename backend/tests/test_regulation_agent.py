"""Tests for backend/services/regulatory/regulation_agent.py.

Cover：
- Ollama 报错路径
- Anthropic：单轮（无 tool_use）/ 多轮（search → get → final）/ 错误路径
- OpenAI/DeepSeek：tool_calls delta 累积 + 多轮
- citations 编号 / 去重 / card 生成
- max_rounds 强制收尾
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.config import LLMProviderType
from backend.interfaces import RegulationSnippetPayload
from backend.repositories.regulations.keyword_search import KeywordIndex
from backend.repositories.regulations.models import Regulation
from backend.repositories.regulations.registry import reset_registry, set_registry
from backend.repositories.regulations.seed_loader import reset_cache
from backend.services.regulatory.regulation_agent import (
    AgentEvent,
    RegulationAgent,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    reset_cache()
    reset_registry()
    yield
    reset_cache()
    reset_registry()


# === 测试用语料 + index ===
def _make_regs() -> list[Regulation]:
    return [
        Regulation(
            id="vat-rd",
            category="VAT",
            source_name="财税公告 2023 年第 7 号",
            source_url="http://example.com/vat-rd",
            chapter="第一条",
            article_number="第一条",
            title="增值税加计抵减",
            summary="集成电路企业 15% 加计抵减进项",
            full_text="完整：当期可抵扣进项税额加计 15% ...",
            tags=["增值税", "加计抵减", "集成电路"],
        ),
        Regulation(
            id="cit-rd",
            category="CIT",
            source_name="财税公告 2023 年第 7 号 - 研发费用",
            source_url="http://example.com/cit-rd",
            chapter="第一条",
            article_number="第一条",
            title="研发费用 100% 加计扣除",
            summary="2023 年起所有行业研发费用 100% 加计扣除",
            full_text="完整：未形成无形资产计入当期损益的，按 100% 加计扣除 ...",
            tags=["企业所得税", "研发费用", "加计扣除", "100%"],
        ),
        Regulation(
            id="iit-deduct",
            category="IIT",
            source_name="个税法第六条",
            source_url="http://example.com/iit",
            chapter="第二章",
            article_number="第六条",
            title="综合所得 6 万元基本减除",
            summary="居民个人综合所得每年减除 6 万元",
            full_text="完整：综合所得以年收入额减除费用六万元 ...",
            tags=["个人所得税", "综合所得", "减除费用", "6 万"],
        ),
    ]


@pytest.fixture
def index() -> KeywordIndex:
    regs = _make_regs()
    # 同步 registry 缓存：agent dispatch 中 get_regulation 走 registry，
    # 搜索走 KeywordIndex；两边必须用同一组 regs 才能 round-trip。
    set_registry(regs)
    return KeywordIndex(regs)


# === Mock Anthropic ===
class _AnthBlock:
    """Anthropic content block —— mock 替代 anthropic SDK 的 ContentBlock."""

    def __init__(self, type_: str, **fields: Any) -> None:
        self.type = type_
        for k, v in fields.items():
            setattr(self, k, v)

    def model_dump(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type}
        for k, v in self.__dict__.items():
            if k == "type":
                continue
            out[k] = v
        return out


class _FakeAnthropicStream:
    """Mock ``async with client.messages.stream(...)`` 上下文 + text_stream + get_final_message."""

    def __init__(
        self,
        text_chunks: list[str],
        final_blocks: list[_AnthBlock],
        stop_reason: str = "end_turn",
    ) -> None:
        self._text_chunks = text_chunks
        self._final_blocks = final_blocks
        self._stop_reason = stop_reason

    async def __aenter__(self) -> "_FakeAnthropicStream":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    @property
    def text_stream(self) -> AsyncIterator[str]:
        async def gen() -> AsyncIterator[str]:
            for c in self._text_chunks:
                yield c

        return gen()

    async def get_final_message(self) -> Any:
        msg = MagicMock()
        msg.content = self._final_blocks
        msg.stop_reason = self._stop_reason
        return msg


class _FakeAnthropicClient:
    """每次调 messages.stream 返回下一个预置的 _FakeAnthropicStream（顺序消费）."""

    def __init__(self, round_streams: list[_FakeAnthropicStream]) -> None:
        self._rounds = list(round_streams)
        self.messages = MagicMock()
        self.messages.stream = MagicMock(side_effect=lambda **kwargs: self._next())

    def _next(self) -> _FakeAnthropicStream:
        if not self._rounds:
            raise RuntimeError("Mock anthropic ran out of pre-configured rounds")
        return self._rounds.pop(0)


def _fake_orchestrator(provider: LLMProviderType, client: Any) -> Any:
    """构造 ``ChatOrchestrator``-like mock，只暴露 agent 需要的 4 个 accessor."""
    orch = MagicMock()
    orch.get_client = MagicMock(return_value=client)
    orch.get_model = MagicMock(return_value="mock-model")
    orch.get_provider = MagicMock(return_value=provider)
    orch.get_temperature = MagicMock(return_value=0.5)
    return orch


# === 1. Ollama 不支持 ===
class TestOllamaUnsupported:
    @pytest.mark.asyncio
    async def test_ollama_returns_error_event(self, index: KeywordIndex) -> None:
        orch = _fake_orchestrator(LLMProviderType.OLLAMA, client=None)
        agent = RegulationAgent(orch, index=index)
        events = [ev async for ev in agent.stream("研发加计扣除")]

        assert events[0].type == "error"
        assert "Ollama" in events[0].content
        assert events[-1].type == "finish"
        assert events[-1].finish_reason == "error"


# === 2. Anthropic 路径 ===
class TestAnthropicSingleRound:
    @pytest.mark.asyncio
    async def test_no_tool_use_yields_text_then_finish(self, index: KeywordIndex) -> None:
        # 单轮：LLM 直接回答，不 call tool
        client = _FakeAnthropicClient(
            [
                _FakeAnthropicStream(
                    text_chunks=["你好，", "请告诉我具体问题。"],
                    final_blocks=[_AnthBlock("text", text="你好，请告诉我具体问题。")],
                    stop_reason="end_turn",
                )
            ]
        )
        orch = _fake_orchestrator(LLMProviderType.ANTHROPIC, client)
        agent = RegulationAgent(orch, index=index)
        events = [ev async for ev in agent.stream("hi")]

        text_events = [e for e in events if e.type == "text"]
        assert "".join(e.content for e in text_events) == "你好，请告诉我具体问题。"
        assert events[-1].type == "finish"
        assert events[-1].finish_reason == "end_turn"
        assert events[-1].citations == []


class TestAnthropicMultiRound:
    @pytest.mark.asyncio
    async def test_search_then_get_then_final(self, index: KeywordIndex) -> None:
        # Round 1: LLM 决定调 search_regulations
        round1 = _FakeAnthropicStream(
            text_chunks=[],
            final_blocks=[
                _AnthBlock(
                    "tool_use",
                    id="toolu_1",
                    name="search_regulations",
                    input={"query": "研发加计扣除"},
                )
            ],
            stop_reason="tool_use",
        )
        # Round 2: LLM 看到 search 结果后调 get_regulation
        round2 = _FakeAnthropicStream(
            text_chunks=[],
            final_blocks=[
                _AnthBlock(
                    "tool_use",
                    id="toolu_2",
                    name="get_regulation",
                    input={"id": "cit-rd"},
                )
            ],
            stop_reason="tool_use",
        )
        # Round 3: LLM 给最终答案
        round3 = _FakeAnthropicStream(
            text_chunks=["研发费用按 100% 加计扣除[1]。"],
            final_blocks=[_AnthBlock("text", text="研发费用按 100% 加计扣除[1]。")],
            stop_reason="end_turn",
        )
        client = _FakeAnthropicClient([round1, round2, round3])
        orch = _fake_orchestrator(LLMProviderType.ANTHROPIC, client)
        agent = RegulationAgent(orch, index=index)
        events = [ev async for ev in agent.stream("研发费用加计扣除？")]

        # 事件序：tool_call(search) → tool_result(search) → tool_call(get) → tool_result(get) → card → text(final) → finish
        types = [e.type for e in events]
        assert types[0] == "tool_call"
        assert events[0].tool_name == "search_regulations"
        assert types[1] == "tool_result"
        assert events[1].tool_call_id == "toolu_1"

        assert types[2] == "tool_call"
        assert events[2].tool_name == "get_regulation"
        assert events[2].tool_input == {"id": "cit-rd"}
        assert types[3] == "tool_result"

        # card 紧跟在 get_regulation tool_result 之后
        card_events = [e for e in events if e.type == "card"]
        assert len(card_events) == 1
        card = card_events[0].card
        assert card is not None
        assert card.card_type == "regulation_snippet"
        assert card.title == "研发费用 100% 加计扣除"

        # text 最终答案 + finish 携带 citation
        finish = events[-1]
        assert finish.type == "finish"
        assert finish.finish_reason == "end_turn"
        assert finish.citations is not None
        assert len(finish.citations) == 1
        assert finish.citations[0].label == "[1]"
        assert finish.citations[0].url == "http://example.com/cit-rd"

    @pytest.mark.asyncio
    async def test_get_regulation_unknown_id_no_card(self, index: KeywordIndex) -> None:
        # LLM 调 get_regulation 但 id 不存在 → 不产 card / 不加 citation
        round1 = _FakeAnthropicStream(
            text_chunks=[],
            final_blocks=[
                _AnthBlock(
                    "tool_use",
                    id="toolu_1",
                    name="get_regulation",
                    input={"id": "nonexistent-zz"},
                )
            ],
            stop_reason="tool_use",
        )
        round2 = _FakeAnthropicStream(
            text_chunks=["未找到该条款。"],
            final_blocks=[_AnthBlock("text", text="未找到该条款。")],
            stop_reason="end_turn",
        )
        client = _FakeAnthropicClient([round1, round2])
        orch = _fake_orchestrator(LLMProviderType.ANTHROPIC, client)
        agent = RegulationAgent(orch, index=index)
        events = [ev async for ev in agent.stream("xxx")]

        assert not [e for e in events if e.type == "card"]
        assert events[-1].citations == []

    @pytest.mark.asyncio
    async def test_duplicate_get_does_not_double_count_citation(
        self, index: KeywordIndex
    ) -> None:
        # LLM 不小心 get 同一个 id 两次 → 只产生一张 card / 一个 citation
        get_block = _AnthBlock(
            "tool_use",
            id="toolu_a",
            name="get_regulation",
            input={"id": "cit-rd"},
        )
        round1 = _FakeAnthropicStream(
            text_chunks=[],
            final_blocks=[get_block],
            stop_reason="tool_use",
        )
        round2 = _FakeAnthropicStream(
            text_chunks=[],
            final_blocks=[
                _AnthBlock(
                    "tool_use",
                    id="toolu_b",
                    name="get_regulation",
                    input={"id": "cit-rd"},  # 同 id
                )
            ],
            stop_reason="tool_use",
        )
        round3 = _FakeAnthropicStream(
            text_chunks=["研发加计扣除[1]。"],
            final_blocks=[_AnthBlock("text", text="研发加计扣除[1]。")],
            stop_reason="end_turn",
        )
        client = _FakeAnthropicClient([round1, round2, round3])
        orch = _fake_orchestrator(LLMProviderType.ANTHROPIC, client)
        agent = RegulationAgent(orch, index=index)
        events = [ev async for ev in agent.stream("xxx")]

        cards = [e for e in events if e.type == "card"]
        assert len(cards) == 1, "重复 get 同 id 不应重复产 card"
        assert events[-1].citations is not None
        assert len(events[-1].citations) == 1


class TestAnthropicMaxRounds:
    @pytest.mark.asyncio
    async def test_force_final_round_when_max_reached(self, index: KeywordIndex) -> None:
        # 4 轮全是 tool_use → 第 5 轮被强制无 tools 收尾
        rounds = [
            _FakeAnthropicStream(
                text_chunks=[],
                final_blocks=[
                    _AnthBlock(
                        "tool_use",
                        id=f"toolu_{i}",
                        name="search_regulations",
                        input={"query": "x"},
                    )
                ],
                stop_reason="tool_use",
            )
            for i in range(4)
        ]
        # 第 5 轮（强制收尾）：无 tools，输出 final 文本
        final_round = _FakeAnthropicStream(
            text_chunks=["最终总结。"],
            final_blocks=[_AnthBlock("text", text="最终总结。")],
            stop_reason="end_turn",
        )
        client = _FakeAnthropicClient(rounds + [final_round])
        orch = _fake_orchestrator(LLMProviderType.ANTHROPIC, client, )
        agent = RegulationAgent(orch, index=index, max_tool_rounds=4)
        events = [ev async for ev in agent.stream("xxx")]

        # 应该消耗了 5 个 stream（4 + 1 强制收尾）
        assert client.messages.stream.call_count == 5

        # 最后 finish 标 max_rounds
        finish = events[-1]
        assert finish.type == "finish"
        assert finish.finish_reason == "max_rounds"

        # 倒数第二/三个事件包含强制提示文本
        text_concat = "".join(e.content for e in events if e.type == "text")
        assert "工具调用上限" in text_concat
        assert "最终总结" in text_concat


# === 3. OpenAI / DeepSeek 路径 ===
class _OACDelta:
    """Mock OpenAI ChunkDelta 的字段."""

    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[Any] | None = None,
    ) -> None:
        self.content = content
        self.tool_calls = tool_calls


class _OACToolCallDelta:
    def __init__(
        self,
        index: int,
        id: str | None = None,
        name: str | None = None,
        arguments: str | None = None,
    ) -> None:
        self.index = index
        self.id = id
        self.function = MagicMock()
        self.function.name = name
        self.function.arguments = arguments


class _OACChunk:
    def __init__(
        self,
        content: str | None = None,
        tool_calls: list[_OACToolCallDelta] | None = None,
        finish_reason: str | None = None,
    ) -> None:
        choice = MagicMock()
        choice.delta = _OACDelta(content=content, tool_calls=tool_calls)
        choice.finish_reason = finish_reason
        self.choices = [choice]


async def _oac_stream(chunks: list[_OACChunk]) -> AsyncIterator[_OACChunk]:
    for c in chunks:
        yield c


class _FakeOpenAIClient:
    """Mock OpenAI / DeepSeek client.chat.completions.create 的多轮顺序返回."""

    def __init__(self, rounds: list[list[_OACChunk]]) -> None:
        self._rounds = list(rounds)
        self.chat = MagicMock()
        self.chat.completions = MagicMock()

        async def _create(**kwargs: Any) -> AsyncIterator[_OACChunk]:
            if not self._rounds:
                raise RuntimeError("Mock openai ran out of pre-configured rounds")
            chunks = self._rounds.pop(0)
            return _oac_stream(chunks)

        self.chat.completions.create = _create  # type: ignore[assignment]

    @property
    def remaining_rounds(self) -> int:
        return len(self._rounds)


class TestOpenAISingleRound:
    @pytest.mark.asyncio
    async def test_text_only_stream(self, index: KeywordIndex) -> None:
        round1 = [
            _OACChunk(content="你好"),
            _OACChunk(content="，请讲。", finish_reason="stop"),
        ]
        client = _FakeOpenAIClient([round1])
        orch = _fake_orchestrator(LLMProviderType.OPENAI, client)
        agent = RegulationAgent(orch, index=index)
        events = [ev async for ev in agent.stream("hi")]

        text_concat = "".join(e.content for e in events if e.type == "text")
        assert text_concat == "你好，请讲。"
        assert events[-1].type == "finish"
        assert events[-1].finish_reason == "stop"


class TestOpenAIMultiRound:
    @pytest.mark.asyncio
    async def test_tool_calls_assembled_across_chunks(self, index: KeywordIndex) -> None:
        # Round 1: tool_calls 分多个 chunk 累积（典型 OpenAI 行为）
        round1 = [
            _OACChunk(
                tool_calls=[
                    _OACToolCallDelta(index=0, id="call_1", name="search_regulations")
                ]
            ),
            _OACChunk(
                tool_calls=[_OACToolCallDelta(index=0, arguments='{"query":')]
            ),
            _OACChunk(
                tool_calls=[_OACToolCallDelta(index=0, arguments='"研发"')]
            ),
            _OACChunk(
                tool_calls=[_OACToolCallDelta(index=0, arguments="}")],
                finish_reason="tool_calls",
            ),
        ]
        # Round 2: get_regulation
        round2 = [
            _OACChunk(
                tool_calls=[
                    _OACToolCallDelta(
                        index=0,
                        id="call_2",
                        name="get_regulation",
                        arguments='{"id":"cit-rd"}',
                    )
                ],
                finish_reason="tool_calls",
            )
        ]
        # Round 3: 最终文本
        round3 = [
            _OACChunk(content="研发 100% 加计扣除[1]。", finish_reason="stop"),
        ]
        client = _FakeOpenAIClient([round1, round2, round3])
        orch = _fake_orchestrator(LLMProviderType.DEEPSEEK, client)
        agent = RegulationAgent(orch, index=index)
        events = [ev async for ev in agent.stream("研发？")]

        # tool_calls 应该被正确累积
        tool_calls = [e for e in events if e.type == "tool_call"]
        assert len(tool_calls) == 2
        assert tool_calls[0].tool_name == "search_regulations"
        assert tool_calls[0].tool_input == {"query": "研发"}
        assert tool_calls[1].tool_name == "get_regulation"
        assert tool_calls[1].tool_input == {"id": "cit-rd"}

        # 最终 finish 带 citation + card 已生成
        cards = [e for e in events if e.type == "card"]
        assert len(cards) == 1
        finish = events[-1]
        assert finish.type == "finish"
        assert finish.finish_reason == "stop"
        assert finish.citations is not None
        assert len(finish.citations) == 1


class TestOpenAIMaxRounds:
    @pytest.mark.asyncio
    async def test_force_final_round_when_max_reached(self, index: KeywordIndex) -> None:
        # 4 轮全 tool_calls → 第 5 轮强制无 tools 收尾
        tool_round = lambda i: [
            _OACChunk(
                tool_calls=[
                    _OACToolCallDelta(
                        index=0,
                        id=f"call_{i}",
                        name="search_regulations",
                        arguments='{"query":"x"}',
                    )
                ],
                finish_reason="tool_calls",
            )
        ]
        rounds = [tool_round(i) for i in range(4)]
        final_round = [_OACChunk(content="总结完毕。", finish_reason="stop")]
        client = _FakeOpenAIClient(rounds + [final_round])
        orch = _fake_orchestrator(LLMProviderType.OPENAI, client)
        agent = RegulationAgent(orch, index=index, max_tool_rounds=4)
        events = [ev async for ev in agent.stream("xxx")]

        # 5 轮全部消费完
        assert client.remaining_rounds == 0
        finish = events[-1]
        assert finish.type == "finish"
        assert finish.finish_reason == "max_rounds"
        text_concat = "".join(e.content for e in events if e.type == "text")
        assert "工具调用上限" in text_concat
        assert "总结完毕" in text_concat


# === 4. RegulationSnippetPayload 校验 ===
class TestCardPayload:
    @pytest.mark.asyncio
    async def test_card_payload_matches_dataclass_schema(
        self, index: KeywordIndex
    ) -> None:
        round1 = _FakeAnthropicStream(
            text_chunks=[],
            final_blocks=[
                _AnthBlock(
                    "tool_use",
                    id="toolu_1",
                    name="get_regulation",
                    input={"id": "vat-rd"},
                )
            ],
            stop_reason="tool_use",
        )
        round2 = _FakeAnthropicStream(
            text_chunks=["[1]"],
            final_blocks=[_AnthBlock("text", text="[1]")],
            stop_reason="end_turn",
        )
        client = _FakeAnthropicClient([round1, round2])
        orch = _fake_orchestrator(LLMProviderType.ANTHROPIC, client)
        agent = RegulationAgent(orch, index=index)
        events = [ev async for ev in agent.stream("xxx")]

        card_event = next(e for e in events if e.type == "card")
        card = card_event.card
        assert card is not None

        # payload 应该匹配 RegulationSnippetPayload 字段
        payload = card.payload
        expected_fields = {
            "reg_id",
            "source_name",
            "chapter",
            "article_number",
            "summary",
            "full_text",
            "category",
        }
        assert set(payload.keys()) == expected_fields
        assert payload["reg_id"] == "vat-rd"
        assert payload["category"] == "VAT"
        # 可被还原成 dataclass
        rsp = RegulationSnippetPayload(**payload)
        assert rsp.reg_id == "vat-rd"
