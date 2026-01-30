"""Application settings."""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = 'anthropic'
    OPENAI = 'openai'


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # LLM Settings
    llm_provider: Optional[LLMProvider] = None
    claude_model: str = 'claude-sonnet-4-20250514'
    openai_model: str = 'gpt-4o'

    # Storage Settings
    data_dir: Path = Path.home() / '.paper-bartender'
    data_file: str = 'data.json'
    default_task_hours: float = 2.0

    model_config = SettingsConfigDict(
        env_prefix='PAPER_BARTENDER_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    @property
    def data_path(self) -> Path:
        """Get the full path to the data file."""
        return self.data_dir / self.data_file

    def get_provider(self) -> LLMProvider:
        """Get the LLM provider to use.

        If explicitly set, use that. Otherwise, auto-detect based on available API keys.
        Prefers Anthropic if both keys are available.
        """
        if self.llm_provider:
            return self.llm_provider

        if self.anthropic_api_key:
            return LLMProvider.ANTHROPIC
        if self.openai_api_key:
            return LLMProvider.OPENAI

        raise ValueError(
            'No LLM API key configured. Set one of:\n'
            '  - PAPER_BARTENDER_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY\n'
            '  - PAPER_BARTENDER_OPENAI_API_KEY or OPENAI_API_KEY'
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
