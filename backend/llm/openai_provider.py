"""OpenAI-compatible LLM provider.

Supports OpenAI, DeepSeek, and any API that implements the
OpenAI chat completions interface.
"""

import logging

from openai import OpenAI

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI-compatible APIs.

    Works with OpenAI, DeepSeek, and other compatible endpoints
    by overriding the base_url.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
    ) -> None:
        self._model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._base_url = base_url

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.5,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        logger.debug("OpenAI request: model=%s, messages=%d", self._model, len(messages))

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }

        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            usage=usage,
            raw=response,
        )

    @property
    def name(self) -> str:
        label = "OpenAI"
        if self._base_url and "deepseek" in self._base_url:
            label = "DeepSeek"
        return f"{label} ({self._model})"
