"""Factory for creating LLM provider instances from configuration.

按 agent-rules/principles/architecture.md 的"注册表 / 工厂模式"：新 provider = 加一行
注册表条目，不改分发分支。

v0.1 默认 anthropic / claude-3-5-sonnet-latest；可通过 LLM_PROVIDER env 切换。
"""

from __future__ import annotations

import logging

from backend.config import LLMProviderType, LLMSettings, Settings, get_settings

from .base import LLMProvider
from .claude_provider import ClaudeProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


# 各 provider 的默认 model（用户可在 provider 实例化后改）
_DEFAULT_MODELS: dict[LLMProviderType, str] = {
    LLMProviderType.ANTHROPIC: "claude-3-5-sonnet-latest",
    LLMProviderType.OPENAI: "gpt-4o",
    LLMProviderType.DEEPSEEK: "deepseek-chat",
    LLMProviderType.OLLAMA: "llama3.1:8b",
}


def get_llm(settings: LLMSettings | None = None) -> LLMProvider:
    """Create an LLM provider from settings.

    Args:
        settings: LLMSettings; 默认从 ``get_settings().llm`` 拿单例

    Raises:
        ValueError: provider 字段未知 / 对应 API key 缺失
    """
    if settings is None:
        settings = get_settings().llm

    provider = settings.provider
    model = _DEFAULT_MODELS[provider]

    if provider == LLMProviderType.ANTHROPIC:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY 未设置（LLM_PROVIDER=anthropic）")
        return ClaudeProvider(api_key=settings.anthropic_api_key, model=model)

    if provider == LLMProviderType.OPENAI:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY 未设置（LLM_PROVIDER=openai）")
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=model,
            base_url=settings.openai_base_url,
        )

    if provider == LLMProviderType.DEEPSEEK:
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY 未设置（LLM_PROVIDER=deepseek）")
        # DeepSeek 用 OpenAI 兼容 API
        return OpenAIProvider(
            api_key=settings.deepseek_api_key,
            model=model,
            base_url="https://api.deepseek.com",
        )

    if provider == LLMProviderType.OLLAMA:
        return OllamaProvider(model=settings.ollama_model, base_url=settings.ollama_host)

    raise ValueError(f"Unknown LLM provider: {provider}")


def get_default_llm() -> LLMProvider:
    """Convenience：用根 settings 单例创建 provider。"""
    return get_llm(get_settings().llm)


__all__ = ["get_llm", "get_default_llm"]


# 兼容旧 import：让 `from backend.llm import get_llm` 不破
def _ensure_compat() -> None:
    _ = (Settings,)  # 防止 lint 报 unused


_ensure_compat()
