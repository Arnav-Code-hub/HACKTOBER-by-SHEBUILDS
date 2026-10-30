"""Typed application settings.

Every environment variable the API reads is declared here. Nothing else in the
codebase may call ``os.getenv`` — a typo in a variable name should fail at
startup, not at 2am in the middle of a demo.
"""

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Environment = "development"
    port: int = Field(default=8000, ge=1, le=65535)
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
    firebase_credentials_json: SecretStr = SecretStr("")

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: SecretStr = SecretStr("")
    cloudinary_folder: str = "janmaang"
    cloudinary_upload_preset: str = ""
    media_upload_ttl_seconds: int = Field(default=900, ge=60, le=3600)

    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = ""
    gemini_timeout_seconds: int = Field(default=8, ge=1, le=60)
    # 0 turns thinking off (Flash models); -1 is the model's dynamic default.
    # Models that cannot disable thinking need a small positive budget.
    gemini_thinking_budget: int = Field(default=0, ge=-1, le=8192)

    maps_api_key: str = ""

    council_enabled: bool = False
    council_url: str = ""
    council_service_key: SecretStr = SecretStr("")
    council_allow_simulation: bool = False

    @model_validator(mode="after")
    def _council_configuration(self) -> "Settings":
        if self.council_enabled:
            parsed = urlsplit(self.council_url)
            if (
                (
                    parsed.scheme != "https"
                    and not (
                        parsed.scheme == "http"
                        and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
                    )
                )
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("COUNCIL_URL must be an HTTPS origin (localhost HTTP is allowed).")
            if len(self.council_service_key.get_secret_value()) < 32:
                raise ValueError("COUNCIL_SERVICE_KEY must contain at least 32 characters.")
        return self

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("cloudinary_folder")
    @classmethod
    def _safe_folder(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", value):
            raise ValueError("CLOUDINARY_FOLDER must be a relative folder without traversal")
        return value

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
