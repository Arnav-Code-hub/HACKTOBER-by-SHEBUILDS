"""Reset compares the full project identity; credentials never enter messages."""

from sqlalchemy.engine import make_url

from app.core.config import Settings


class SeedResetError(ValueError):
    """Fixed, credential-free refusal messages safe for CLI output."""


def require_reset_allowed(settings: Settings) -> None:
    if settings.is_production or not settings.seed_reset_allowed:
        raise SeedResetError("Seed reset is disabled for this environment.")
    url = make_url(str(settings.database_url))
    host = url.host or ""
    if ":" in host:
        host = f"[{host}]"
    identity = f"{url.username}@{host}:{url.port or 5432}/{url.database}"
    if identity not in settings.seed_reset_targets:
        raise SeedResetError("Seed reset target is not explicitly allowlisted.")
