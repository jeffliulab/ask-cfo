"""Anthropic Claude LLM provider."""

import logging

import anthropic

from .base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """Provider for Anthropic Claude API.

    Handles the difference between OpenAI and Anthropic message formats:
    Claude requires system prompts to be passed separately.
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.5,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        # Separate system messages from user/assistant messages
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        chat_messages = [m for m in messages if m["role"] != "system"]
        system_text = "\n\n".join(system_parts) if system_parts else ""

        logger.debug("Claude request: model=%s, messages=%d", self._model, len(chat_messages))

        kwargs: dict = {
            "model": self._model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_text:
            kwargs["system"] = system_text

        response = self._client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
            raw=response,
        )

    @property
    def name(self) -> str:
        return f"Claude ({self._model})"
