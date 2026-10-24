"""Typed application settings.

Every environment variable the API reads is declared here. Nothing else in the
codebase may call ``os.getenv`` — a typo in a variable name should fail at
startup, not at 2am in the middle of a demo.
"""

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Environment = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: PostgresDsn
    database_pool_size: int = Field(default=5, ge=1, le=20)
    seed_reset_allowed: bool = False
    seed_reset_targets: Annotated[list[str], NoDecode] = Field(default_factory=list)
    # Reserved for legacy tools. The prototype never requires Redis at startup.
    redis_url: RedisDsn | None = None

    firebase_project_id: str = ""
    firebase_credentials_path: str = ""
    firebase_credentials_json: str = ""

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: SecretStr = SecretStr("")
    cloudinary_folder: str = "janmaang"

    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = ""
    gemini_timeout_seconds: int = Field(default=8, ge=1, le=60)

    maps_api_key: str = ""

    auth_secret: SecretStr = Field(min_length=16)
    access_token_ttl_minutes: int = 60

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("seed_reset_targets", mode="before")
    @classmethod
    def _split_reset_targets(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [entry.strip() for entry in value.split(",") if entry.strip()]
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            v = [o.strip() for o in v.split(",") if o.strip()]
        for origin in v:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in origin
            ):
                raise ValueError("CORS_ORIGINS must contain exact HTTP(S) origins without paths")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached so the file is parsed once per process."""
    return Settings()
