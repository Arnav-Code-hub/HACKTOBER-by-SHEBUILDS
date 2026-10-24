"""Shared Redis connection — cache, rate limits and the ARQ job queue."""

from typing import cast

from redis.asyncio import Redis

from app.core.config import get_settings


def get_redis() -> Redis:
    """Explicit opt-in for legacy callers; importing this module does no work.

    The caller owns and closes this client. Prototype API code does not use it.
    """
    url = get_settings().redis_url
    if url is None:
        raise RuntimeError("Redis is disabled in the prototype")
    return cast(Redis, Redis.from_url(str(url), decode_responses=True))
