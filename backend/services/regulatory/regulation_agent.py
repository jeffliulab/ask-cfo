"""RegulationAgent —— Day 3 of v0.1.0.

LLM tool_use 多轮 agent，让 agent 自己用 ``search_regulations`` /
``get_regulation`` 工具在法规库里定位条款，再生成带 ``[N]`` 引用的中文答案。

关键设计（与 plan 对齐）：

- **不重写 ChatOrchestrator**：通过 ``orchestrator.get_client()/get_model()``
  复用 client，自己组 tool_use 循环
- **provider 兼容**：Anthropic 原生 tool_use；OpenAI / DeepSeek 走 OpenAI
  function calling 协议；Ollama raise NotImplementedError（v0.1 punt）
- **max_tool_rounds=4** 硬上限：4 轮内若仍想继续 tool_call，强制最后一轮
  无 tools 收尾，让 LLM 必须基于已有信息给最终答案
- **Citations 注入**：每次 ``get_regulation`` 命中一个新 id → 按出场顺序
  分配 ``[N]`` 标签 → 同步生成 ``card`` event（RegulationSnippetCard）+
  累计 Citation；finish 时附完整 list

事件流（``AgentEvent``）：
- ``text``：assistant 文本 delta（流式）
- ``tool_call``：agent 调用工具
- ``tool_result``：工具返回摘要
- ``card``：新条款卡片（携带 RegulationSnippetPayload）
- ``finish``：终止（含 citations + finish_reason）
- ``error``：致命错误
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import anthropic
import openai
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.config import LLMProviderType
from backend.interfaces import Citation, RegulationSnippetPayload, WorkspaceCard
from backend.repositories.regulations.keyword_search import KeywordIndex
from backend.repositories.regulations.seed_loader import load_seed
from backend.repositories.regulations.tools import (
    GET_TOOL_NAME,
    SEARCH_TOOL_NAME,
    anthropic_schema,
    dispatch,
    openai_schema,
)
from backend.services.chat.orchestrator import ChatOrchestrator

logger = logging.getLogger(__name__)


# === Event 类型 ===
@dataclass
class AgentEvent:
    """RegulationAgent.stream 产生的一种事件 —— routes 层转 SSE."""

    type: Literal["text", "tool_call", "tool_result", "card", "finish", "error"]
    content: str = ""  # type=text/error 时是文本片段
    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    tool_call_id: str = ""
    tool_result_summary: str = ""  # type=tool_result 时一行摘要
    tool_result_meta: dict[str, Any] = field(default_factory=dict)  # 例如 hits_count
    card: WorkspaceCard | None = None
    citations: list[Citation] | None = None
    finish_reason: str | None = None  # "stop" / "max_rounds" / "error"


# === Prompt 渲染 ===
_PROMPT_DIR = Path(__file__).parents[2] / "data" / "prompts" / "regulations"
_prompt_env = Environment(
    loader=FileSystemLoader(_PROMPT_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _render_system_prompt() -> str:
    return _prompt_env.get_template("qa_system_prompt.j2").render()


# === Citation 状态 ===
class _CitationsState:
    """累计 citations，按 reg_id 去重，按出场顺序编号 [1] [2] ..."""

    def __init__(self) -> None:
        self._by_id: dict[str, Citation] = {}
        self._order: list[str] = []

    def add_if_new(self, reg: dict[str, Any]) -> Citation | None:
        """添加新 reg 引用；已存在返回 None。"""
        reg_id = reg["id"]
        if reg_id in self._by_id:
            return None
        label = f"[{len(self._order) + 1}]"
        cit = Citation(
            label=label,
            source_name=reg["source_name"],
            url=reg["source_url"],
        )
        self._by_id[reg_id] = cit
        self._order.append(reg_id)
        return cit

    def get_label(self, reg_id: str) -> str | None:
        cit = self._by_id.get(reg_id)
        return cit.label if cit else None

    def to_list(self) -> list[Citation]:
        return [self._by_id[i] for i in self._order]


def _make_regulation_card(reg: dict[str, Any], label: str) -> WorkspaceCard:
    """根据 get_regulation 返回的 reg dict 构建 RegulationSnippetCard."""
    payload = RegulationSnippetPayload(
        reg_id=reg["id"],
        source_name=reg["source_name"],
        chapter=reg["chapter"],
        article_number=reg["article_number"],
        summary=reg["summary"],
        full_text=reg["full_text"],
        category=reg["category"],
    )
    citation = Citation(
        label=label,
        source_name=reg["source_name"],
        url=reg["source_url"],
    )
    return WorkspaceCard(
        workspace_id=f"regulation-{reg['id']}",
        card_type="regulation_snippet",
        title=reg["title"],
        payload=payload.__dict__,
        citations=[citation],
    )


def _summarize_result(name: str, result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """把 dispatch 返回值压成一行摘要 + 元数据，给前端 tool_result 事件展示."""
    if name == SEARCH_TOOL_NAME:
        hits = result.get("hits", [])
        summary = f"命中 {len(hits)} 条"
        if hits:
            summary += "：" + " / ".join(h["id"] for h in hits[:3])
            if len(hits) > 3:
                summary += " ..."
        return summary, {"hits_count": len(hits)}
    if name == GET_TOOL_NAME:
        if result.get("regulation"):
            reg = result["regulation"]
            return f"读取 {reg['id']}：{reg['title']}", {"reg_id": reg["id"]}
        return f"id 不存在: {result.get('error', '')}", {}
    if "error" in result:
        return f"错误：{result['error']}", {}
    return "ok", {}


# === RegulationAgent ===
class RegulationAgent:
    """LLM tool_use 多轮 agent for 法规问答。

    用法：
        agent = RegulationAgent(orchestrator)  # index 默认懒加载 seed
        async for event in agent.stream("研发费用加计扣除比例"):
            # routes 层转成 SSE
    """

    def __init__(
        self,
        orchestrator: ChatOrchestrator,
        *,
        max_tool_rounds: int = 4,
        index: KeywordIndex | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._max_tool_rounds = max_tool_rounds
        # index 依赖注入；测试可传 mock
        self._index = index if index is not None else KeywordIndex(load_seed())

    async def stream(
        self,
        query: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """主入口 —— 按 provider 分支."""
        provider = self._orchestrator.get_provider()

        try:
            if provider == LLMProviderType.OLLAMA:
                yield AgentEvent(
                    type="error",
                    content="v0.1 不支持 Ollama tool_use；请切到 anthropic / deepseek / openai",
                    finish_reason="error",
                )
                yield AgentEvent(type="finish", finish_reason="error")
                return

            if provider == LLMProviderType.ANTHROPIC:
                async for ev in self._stream_anthropic(query, history):
                    yield ev
            else:
                # openai 或 deepseek（同走 openai SDK）
                async for ev in self._stream_openai_compat(query, history):
                    yield ev
        except Exception as exc:  # noqa: BLE001
            logger.exception("RegulationAgent error")
            yield AgentEvent(type="error", content=f"agent error: {exc}", finish_reason="error")
            yield AgentEvent(type="finish", finish_reason="error")

    # ----- Anthropic -----
    async def _stream_anthropic(
        self,
        query: str,
        history: list[dict[str, Any]] | None,
    ) -> AsyncIterator[AgentEvent]:
        client = self._orchestrator.get_client()
        model = self._orchestrator.get_model()
        temp = self._orchestrator.get_temperature()
        system_prompt = _render_system_prompt()

        messages: list[dict[str, Any]] = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": query})

        citations = _CitationsState()
        tools = anthropic_schema()

        for round_idx in range(self._max_tool_rounds):
            logger.info("[regulation-agent] anthropic round %d", round_idx + 1)
            try:
                async with client.messages.stream(
                    model=model,
                    max_tokens=2048,
                    temperature=temp,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                ) as stream:
                    async for text in stream.text_stream:
                        yield AgentEvent(type="text", content=text)
                    final = await stream.get_final_message()
            except anthropic.APIError as exc:
                logger.error("Anthropic API error: %s", exc)
                yield AgentEvent(
                    type="error", content=f"Anthropic API error: {exc}", finish_reason="error"
                )
                yield AgentEvent(type="finish", finish_reason="error")
                return

            tool_uses = [b for b in final.content if getattr(b, "type", "") == "tool_use"]
            stop_reason = getattr(final, "stop_reason", None) or "stop"

            if not tool_uses:
                # 没有更多工具调用 → 终止
                yield AgentEvent(
                    type="finish",
                    citations=citations.to_list(),
                    finish_reason=stop_reason,
                )
                return

            # 把 assistant turn（含 tool_use blocks）加回 messages
            assistant_content = []
            for block in final.content:
                if hasattr(block, "model_dump"):
                    assistant_content.append(block.model_dump())
                else:
                    assistant_content.append(dict(block))
            messages.append({"role": "assistant", "content": assistant_content})

            # 执行 tools
            tool_results_msg: list[dict[str, Any]] = []
            for tu in tool_uses:
                tu_input = dict(tu.input) if tu.input else {}
                yield AgentEvent(
                    type="tool_call",
                    tool_name=tu.name,
                    tool_input=tu_input,
                    tool_call_id=tu.id,
                )
                try:
                    result = dispatch(tu.name, tu_input, self._index)
                except ValueError as exc:
                    result = {"error": str(exc)}

                summary, meta = _summarize_result(tu.name, result)
                yield AgentEvent(
                    type="tool_result",
                    tool_call_id=tu.id,
                    tool_result_summary=summary,
                    tool_result_meta=meta,
                )

                # get_regulation 命中 → 出 card + citation
                if tu.name == GET_TOOL_NAME:
                    reg = result.get("regulation")
                    if reg:
                        new_cit = citations.add_if_new(reg)
                        if new_cit is not None:
                            yield AgentEvent(
                                type="card",
                                card=_make_regulation_card(reg, new_cit.label),
                            )

                tool_results_msg.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

            messages.append({"role": "user", "content": tool_results_msg})

        # 达到 max_rounds —— 强制无 tools 收尾
        async for ev in self._final_round_anthropic(
            client, model, temp, system_prompt, messages, citations
        ):
            yield ev

    async def _final_round_anthropic(
        self,
        client: Any,
        model: str,
        temp: float,
        system_prompt: str,
        messages: list[dict[str, Any]],
        citations: _CitationsState,
    ) -> AsyncIterator[AgentEvent]:
        """达到 max_rounds 后强制一轮无 tools 收尾."""
        forced_messages = messages + [
            {
                "role": "user",
                "content": (
                    "请基于上述检索结果立即给出最终答案，不要再调用工具。"
                    "答案必须用 [N] 角标引用已读取的条款。"
                ),
            }
        ]
        yield AgentEvent(type="text", content="\n\n（达到工具调用上限，基于已收集信息总结）\n\n")
        try:
            async with client.messages.stream(
                model=model,
                max_tokens=2048,
                temperature=temp,
                system=system_prompt,
                messages=forced_messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield AgentEvent(type="text", content=text)
        except anthropic.APIError as exc:
            yield AgentEvent(type="error", content=f"Anthropic API error: {exc}")

        yield AgentEvent(
            type="finish",
            citations=citations.to_list(),
            finish_reason="max_rounds",
        )

    # ----- OpenAI / DeepSeek -----
    async def _stream_openai_compat(
        self,
        query: str,
        history: list[dict[str, Any]] | None,
    ) -> AsyncIterator[AgentEvent]:
        client = self._orchestrator.get_client()
        model = self._orchestrator.get_model()
        temp = self._orchestrator.get_temperature()
        system_prompt = _render_system_prompt()

        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": query})

        citations = _CitationsState()
        tools = openai_schema()

        for round_idx in range(self._max_tool_rounds):
            logger.info("[regulation-agent] openai-compat round %d", round_idx + 1)

            text_parts: list[str] = []
            # idx → {id, name, arguments_str}
            tool_calls_acc: dict[int, dict[str, str]] = {}
            finish_reason: str | None = None

            try:
                stream = await client.chat.completions.create(
                    model=model,
                    temperature=temp,
                    max_tokens=2048,
                    stream=True,
                    messages=messages,
                    tools=tools,
                )
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    delta = choice.delta
                    text_delta = getattr(delta, "content", None)
                    if text_delta:
                        yield AgentEvent(type="text", content=text_delta)
                        text_parts.append(text_delta)

                    tool_call_deltas = getattr(delta, "tool_calls", None) or []
                    for tcd in tool_call_deltas:
                        idx = getattr(tcd, "index", 0)
                        slot = tool_calls_acc.setdefault(
                            idx, {"id": "", "name": "", "arguments": ""}
                        )
                        if getattr(tcd, "id", None):
                            slot["id"] = tcd.id
                        fn = getattr(tcd, "function", None)
                        if fn is not None:
                            if getattr(fn, "name", None):
                                slot["name"] = fn.name
                            if getattr(fn, "arguments", None):
                                slot["arguments"] += fn.arguments

                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
            except openai.APIError as exc:
                logger.error("OpenAI/DeepSeek API error: %s", exc)
                yield AgentEvent(
                    type="error",
                    content=f"OpenAI/DeepSeek API error: {exc}",
                    finish_reason="error",
                )
                yield AgentEvent(type="finish", finish_reason="error")
                return

            if finish_reason != "tool_calls" or not tool_calls_acc:
                yield AgentEvent(
                    type="finish",
                    citations=citations.to_list(),
                    finish_reason=finish_reason or "stop",
                )
                return

            # Append assistant turn with tool_calls
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": "".join(text_parts) or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in tool_calls_acc.values()
                ],
            }
            messages.append(assistant_msg)

            # Execute tools
            for tc in tool_calls_acc.values():
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}

                yield AgentEvent(
                    type="tool_call",
                    tool_name=tc["name"],
                    tool_input=args,
                    tool_call_id=tc["id"],
                )
                try:
                    result = dispatch(tc["name"], args, self._index)
                except ValueError as exc:
                    result = {"error": str(exc)}

                summary, meta = _summarize_result(tc["name"], result)
                yield AgentEvent(
                    type="tool_result",
                    tool_call_id=tc["id"],
                    tool_result_summary=summary,
                    tool_result_meta=meta,
                )

                if tc["name"] == GET_TOOL_NAME:
                    reg = result.get("regulation")
                    if reg:
                        new_cit = citations.add_if_new(reg)
                        if new_cit is not None:
                            yield AgentEvent(
                                type="card",
                                card=_make_regulation_card(reg, new_cit.label),
                            )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

        # 达 max_rounds → 强制无 tools 收尾
        async for ev in self._final_round_openai(
            client, model, temp, messages, citations
        ):
            yield ev

    async def _final_round_openai(
        self,
        client: Any,
        model: str,
        temp: float,
        messages: list[dict[str, Any]],
        citations: _CitationsState,
    ) -> AsyncIterator[AgentEvent]:
        """达 max_rounds 后强制无 tools 收尾（OpenAI/DeepSeek 路径）."""
        forced_messages = messages + [
            {
                "role": "user",
                "content": (
                    "请基于上述检索结果立即给出最终答案，不要再调用工具。"
                    "答案必须用 [N] 角标引用已读取的条款。"
                ),
            }
        ]
        yield AgentEvent(type="text", content="\n\n（达到工具调用上限，基于已收集信息总结）\n\n")
        try:
            stream = await client.chat.completions.create(
                model=model,
                temperature=temp,
                max_tokens=2048,
                stream=True,
                messages=forced_messages,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                content = getattr(choice.delta, "content", None)
                if content:
                    yield AgentEvent(type="text", content=content)
        except openai.APIError as exc:
            yield AgentEvent(type="error", content=f"OpenAI/DeepSeek API error: {exc}")

        yield AgentEvent(
            type="finish",
            citations=citations.to_list(),
            finish_reason="max_rounds",
        )
