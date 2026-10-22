"""AI service settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    internal_api_key: str = ""

    llm_provider: Literal["gemini", "openai", "local"] = "gemini"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.0-flash"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2

    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768

    redis_url: RedisDsn | None = None
    cache_ttl_seconds: int = 86_400

    daily_token_budget: int = Field(default=2_000_000, ge=0)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
