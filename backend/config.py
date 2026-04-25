"""集中式配置 —— pydantic-settings + .env，按 agent-rules/principles/engineering.md.

配置优先级：CLI 参数 > 环境变量 > config.py 默认值。
所有 env key 在 .env.example 列全；本文件不硬编码任何密钥。

v0.1 范围：LLM provider + CORS + 日志。CFO 模块（OCR / RAG / 报税 / 数据库）
对应字段在各模块上线时增补。
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderType(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"


# === 子配置 ===
class LLMSettings(BaseSettings):
    """LLM provider 配置 —— 与 fin-pilot 共享 4 provider 矩阵。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    provider: LLMProviderType = Field(
        default=LLMProviderType.ANTHROPIC, validation_alias="LLM_PROVIDER"
    )

    # provider-specific API keys
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, validation_alias="OPENAI_BASE_URL")
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    ollama_host: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_HOST")

    # model name overrides per provider（空 = orchestrator 默认）
    anthropic_model: str = Field(default="", validation_alias="ANTHROPIC_MODEL")
    openai_model: str = Field(default="", validation_alias="OPENAI_MODEL")
    deepseek_model: str = Field(default="", validation_alias="DEEPSEEK_MODEL")
    ollama_model: str = Field(default="llama3.1:8b", validation_alias="OLLAMA_MODEL")

    # 通用采样参数
    temperature: float = 0.5
    max_tokens: int = 8192


class APISettings(BaseSettings):
    """FastAPI / HTTP 层配置。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins_raw: str = Field(
        default="http://localhost:3000", validation_alias="CORS_ORIGINS"
    )

    @property
    def cors_origins(self) -> list[str]:
        """逗号分隔的 CORS 白名单 → list；agent-rules 禁通配 *。"""
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


# === 根配置 ===
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    api: APISettings = Field(default_factory=APISettings)

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_file: str = Field(default="logs/agent-as-a-cfo.log", validation_alias="LOG_FILE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor —— 测试要重置就调 ``get_settings.cache_clear()``。"""
    return Settings()
