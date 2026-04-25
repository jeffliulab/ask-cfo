"""Local Ollama LLM provider.

Ollama exposes an OpenAI-compatible endpoint, so this provider
inherits from OpenAIProvider with sensible defaults for local use.
"""

from .openai_provider import OpenAIProvider

_OLLAMA_DEFAULT_URL = "http://localhost:11434/v1"


class OllamaProvider(OpenAIProvider):
    """Provider for local Ollama models.

    No API key required. Connects to the local Ollama server
    on its default port.
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = _OLLAMA_DEFAULT_URL,
    ) -> None:
        super().__init__(api_key="ollama", model=model, base_url=base_url)

    @property
    def name(self) -> str:
        return f"Ollama ({self._model})"
