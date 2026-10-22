"""Typed application settings.

Every environment variable the API reads is declared here. Nothing else in the
codebase may call ``os.getenv`` — a typo in a variable name should fail at
startup, not at 2am in the middle of a demo.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Environment = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: PostgresDsn
    database_pool_size: int = 10
    redis_url: RedisDsn

    ai_service_url: str = "http://localhost:8001"
    ai_service_key: str = ""
    ai_request_timeout_seconds: int = 30

    firebase_project_id: str = ""
    firebase_credentials_path: str = ""
    firebase_credentials_json: str = ""

    storage_provider: Literal["firebase", "s3"] = "firebase"
    storage_bucket: str = ""
    storage_signed_url_ttl_seconds: int = 3600

    maps_api_key: str = ""

    auth_secret: str = Field(min_length=16)
    access_token_ttl_minutes: int = 60

    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached so the file is parsed once per process."""
    return Settings()
