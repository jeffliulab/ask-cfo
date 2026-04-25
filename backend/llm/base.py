"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None


class LLMProvider(ABC):
    """Abstract interface for LLM completions.

    All providers must implement this interface, ensuring the rest of
    the application is decoupled from any specific LLM vendor.
    """

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.5,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Send a chat completion request and return a standardized response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            temperature: Sampling temperature (0.0 - 1.0).
            max_tokens: Maximum tokens in the response.

        Returns:
            LLMResponse with the generated content.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
