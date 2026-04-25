"""Chat orchestrator —— LangGraph state 编排 + Anthropic SDK 直接做 streaming.

按 plan §5.2 / docs/architecture.md §3.4 的设计：

- v0.1：单 agent（"个股分析助手"），LangGraph 在这里只起 state 管理 + prompt 渲染
  的脚手架作用；streaming 走 Anthropic SDK 直连，不过 graph
- v0.2+：在同一 graph 里加 "行业对比 agent" / "市场情绪 agent" 节点，自动多 agent
  共识；那时把 streaming 也搬进 LangGraph（用 langchain-anthropic 的 astream_events）

为什么 v0.1 不一上来就把 streaming 放进 graph：
- LangGraph 的原生 streaming 需要绑 langchain-anthropic 的 ChatAnthropic 类，
  跟我们 salvaged 的 LLMProvider 抽象错位
- 一个 LLM 调用没必要走完整 graph 状态机；先把"准备 prompt → 流"这条流水线
  跑稳，v0.2 再扩
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

import anthropic
import httpx
import openai
from jinja2 import Environment, FileSystemLoader, select_autoescape
from langgraph.graph import END, StateGraph

from backend.config import LLMProviderType, LLMSettings, get_settings
from backend.interfaces import Citation

logger = logging.getLogger(__name__)


# === Request / Chunk 类型 ===
@dataclass
class ChatRequest:
    """用户的一条 chat 请求 + 当前工作区快照."""

    message: str
    cards: list[dict]
    citations: list[Citation]


@dataclass
class ChatChunk:
    """流式输出的一个 chunk —— routes 层转成 SSE 协议."""

    type: str  # "delta" | "finish" | "error"
    content: str = ""  # delta 时是文本片段
    citations: list[Citation] | None = None  # finish 时附带
    finish_reason: str | None = None  # finish 时 e.g. "stop" / "max_tokens"


# === LangGraph 状态 ===
class ChatState(TypedDict, total=False):
    user_message: str
    cards: list[dict]
    citations: list[dict]  # serialized for prompt
    rendered_system: str
    rendered_prompt: str


# === Prompt 渲染（LangGraph 节点） ===
_PROMPT_DIR = Path(__file__).parents[2] / "data" / "prompts" / "chat"
_prompt_env = Environment(
    loader=FileSystemLoader(_PROMPT_DIR),
    autoescape=select_autoescape(default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _prepare_node(state: ChatState) -> dict:
    """LangGraph node: render Jinja2 prompts from state.

    把 cards + citations + user_message 喂进模板，返回 system + user prompt。
    """
    system = _prompt_env.get_template("system_prompt.j2").render()
    follow_up = _prompt_env.get_template("follow_up.j2").render(
        cards=state["cards"],
        citations=state["citations"],
        user_message=state["user_message"],
    )
    return {"rendered_system": system, "rendered_prompt": follow_up}


def _build_chat_graph():
    """单节点 graph —— v0.2 加 industry / market agents 时在这里 add_node。"""
    graph = StateGraph(ChatState)
    graph.add_node("prepare", _prepare_node)
    graph.set_entry_point("prepare")
    graph.add_edge("prepare", END)
    return graph.compile()


# 模块级 singleton，避免每次请求都重建
_chat_graph = _build_chat_graph()


# Provider → 默认 model 注册表（仅当 env LLM_xxx_MODEL 没设时用这些）
_DEFAULT_MODEL_BY_PROVIDER: dict[LLMProviderType, str] = {
    LLMProviderType.ANTHROPIC: "claude-3-5-sonnet-latest",
    LLMProviderType.OPENAI: "gpt-4o-mini",  # 便宜快；要更高质量用 OPENAI_MODEL=gpt-4o 覆盖
    LLMProviderType.DEEPSEEK: "deepseek-chat",
    LLMProviderType.OLLAMA: "llama3.1:8b",
}


def _resolve_model(settings: LLMSettings) -> str:
    """根据 provider 取 env 覆盖；空则 fallback 到默认注册表."""
    if settings.provider == LLMProviderType.ANTHROPIC:
        return settings.anthropic_model or _DEFAULT_MODEL_BY_PROVIDER[settings.provider]
    if settings.provider == LLMProviderType.OPENAI:
        return settings.openai_model or _DEFAULT_MODEL_BY_PROVIDER[settings.provider]
    if settings.provider == LLMProviderType.DEEPSEEK:
        return settings.deepseek_model or _DEFAULT_MODEL_BY_PROVIDER[settings.provider]
    if settings.provider == LLMProviderType.OLLAMA:
        return settings.ollama_model or _DEFAULT_MODEL_BY_PROVIDER[settings.provider]
    return ""


# === Orchestrator ===
class ChatOrchestrator:
    """协调 prompt prep + LLM streaming + finish event 三段。

    ``stream(request)`` 返回 async iterator，routes 层逐个 chunk emit 给前端。

    Streaming provider 支持（agent-rules / "类 Cursor 通用框架"）：
      - anthropic（Claude，原生 SDK）
      - openai（gpt-4o-mini / gpt-4o / gpt-4-turbo，OpenAI 原生 SDK；可
        通过 OPENAI_BASE_URL 指任意 OpenAI 兼容端点：Together AI / Groq /
        OpenRouter / Fireworks 等）
      - deepseek（OpenAI 兼容协议，预设 base_url=https://api.deepseek.com）
      - ollama（本地模型，自家 NDJSON 协议 over HTTP）

    Model 默认在 ``_DEFAULT_MODEL_BY_PROVIDER``，可通过 env 覆盖：
      - ANTHROPIC_MODEL / OPENAI_MODEL / DEEPSEEK_MODEL / OLLAMA_MODEL
    """

    def __init__(self, settings: LLMSettings | None = None) -> None:
        if settings is None:
            settings = get_settings().llm
        self._settings = settings
        self._provider = settings.provider
        self._model = _resolve_model(settings)
        self._client: Any = None  # 类型按 provider 不同；下面分支化构造

        # 注：v0.2+ module agent（RegulationAgent / BookkeepingAgent ...）通过
        # ``get_client()`` / ``get_model()`` / ``get_provider()`` 复用 client，
        # 自己组装 tool_use 循环，不重写 orchestrator（plan §A）。

        if self._provider == LLMProviderType.ANTHROPIC:
            if not settings.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY 未设置（LLM_PROVIDER=anthropic）"
                )
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        elif self._provider == LLMProviderType.OPENAI:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY 未设置（LLM_PROVIDER=openai）")
            self._client = openai.AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )

        elif self._provider == LLMProviderType.DEEPSEEK:
            if not settings.deepseek_api_key:
                raise ValueError(
                    "DEEPSEEK_API_KEY 未设置（LLM_PROVIDER=deepseek）"
                )
            # DeepSeek 完全兼容 OpenAI 协议，用 openai SDK + 自家 base_url
            self._client = openai.AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com",
            )

        elif self._provider == LLMProviderType.OLLAMA:
            # Ollama 用自家 HTTP NDJSON 协议，不复用 openai SDK
            # （Ollama 也提供 OpenAI 兼容 endpoint，但默认 native API 字段更全）
            self._client = httpx.AsyncClient(
                base_url=settings.ollama_host,
                timeout=httpx.Timeout(60.0, read=300.0),  # 本地推理可能慢
            )

        else:
            raise ValueError(
                f"未知 provider={self._provider.value}；当前支持 "
                f"anthropic / openai / deepseek / ollama"
            )

    # === Accessors for module-specific agents（v0.1+ tool_use loop）===
    def get_client(self) -> Any:
        """Return the underlying provider client（已构造）。"""
        return self._client

    def get_model(self) -> str:
        """Resolved model name string."""
        return self._model

    def get_provider(self) -> LLMProviderType:
        """Active LLM provider enum."""
        return self._provider

    def get_temperature(self) -> float:
        return self._settings.temperature

    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]:
        """Yield ChatChunk per provider stream event + final finish chunk."""
        # 1. Prepare via LangGraph
        prepared = await _chat_graph.ainvoke(
            {
                "user_message": request.message,
                "cards": request.cards,
                "citations": [
                    {"label": c.label, "source_name": c.source_name, "url": c.url}
                    for c in request.citations
                ],
            }
        )

        logger.debug(
            "chat orchestrator: provider=%s, model=%s, prompt_chars=%d, citations=%d",
            self._provider.value,
            self._model,
            len(prepared["rendered_prompt"]),
            len(request.citations),
        )

        # 2. 按 provider 分支 streaming
        if self._provider == LLMProviderType.ANTHROPIC:
            async for chunk in self._stream_anthropic(prepared, request):
                yield chunk
        elif self._provider == LLMProviderType.OLLAMA:
            async for chunk in self._stream_ollama(prepared, request):
                yield chunk
        else:
            # openai 或 deepseek（同走 openai SDK）
            async for chunk in self._stream_openai(prepared, request):
                yield chunk

    async def _stream_anthropic(
        self, prepared: dict, request: ChatRequest
    ) -> AsyncIterator[ChatChunk]:
        finish_reason: str | None = None
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=2048,
                temperature=self._settings.temperature,
                system=prepared["rendered_system"],
                messages=[{"role": "user", "content": prepared["rendered_prompt"]}],
            ) as stream:
                async for text in stream.text_stream:
                    yield ChatChunk(type="delta", content=text)
                final = await stream.get_final_message()
                finish_reason = final.stop_reason or "stop"
        except anthropic.APIError as exc:
            logger.error("Anthropic API error: %s", exc)
            yield ChatChunk(type="error", content=f"Anthropic API error: {exc}")
            return

        yield ChatChunk(
            type="finish",
            citations=request.citations,
            finish_reason=finish_reason or "stop",
        )

    async def _stream_openai(
        self, prepared: dict, request: ChatRequest
    ) -> AsyncIterator[ChatChunk]:
        finish_reason: str | None = None
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                temperature=self._settings.temperature,
                max_tokens=2048,
                stream=True,
                messages=[
                    {"role": "system", "content": prepared["rendered_system"]},
                    {"role": "user", "content": prepared["rendered_prompt"]},
                ],
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta_content = getattr(choice.delta, "content", None)
                if delta_content:
                    yield ChatChunk(type="delta", content=delta_content)
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
        except openai.APIError as exc:
            logger.error("OpenAI API error: %s", exc)
            yield ChatChunk(type="error", content=f"OpenAI API error: {exc}")
            return

        yield ChatChunk(
            type="finish",
            citations=request.citations,
            finish_reason=finish_reason or "stop",
        )

    async def _stream_ollama(
        self, prepared: dict, request: ChatRequest
    ) -> AsyncIterator[ChatChunk]:
        """Ollama native streaming: POST /api/chat with stream=true → NDJSON.

        Each line: {"model":"...","message":{"role":"assistant","content":"..."},"done":false}
        Final line: {"model":"...","done":true,"done_reason":"stop",...}
        """
        finish_reason: str | None = None
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": prepared["rendered_system"]},
                {"role": "user", "content": prepared["rendered_prompt"]},
            ],
            "stream": True,
            "options": {
                "temperature": self._settings.temperature,
                "num_predict": 2048,
            },
        }
        try:
            async with self._client.stream(
                "POST", "/api/chat", json=body
            ) as response:
                if response.status_code != 200:
                    body_text = await response.aread()
                    yield ChatChunk(
                        type="error",
                        content=f"Ollama HTTP {response.status_code}: {body_text.decode()[:300]}",
                    )
                    return
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = obj.get("message")
                    if msg and isinstance(msg, dict):
                        delta = msg.get("content")
                        if delta:
                            yield ChatChunk(type="delta", content=delta)
                    if obj.get("done"):
                        finish_reason = obj.get("done_reason", "stop")
        except httpx.HTTPError as exc:
            logger.error("Ollama HTTP error: %s", exc)
            yield ChatChunk(type="error", content=f"Ollama HTTP error: {exc}")
            return

        yield ChatChunk(
            type="finish",
            citations=request.citations,
            finish_reason=finish_reason or "stop",
        )
