"""Shared Redis connection — cache, rate limits and the ARQ job queue."""

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

_settings = get_settings()
_pool = ConnectionPool.from_url(str(_settings.redis_url), decode_responses=True)


def get_redis() -> Redis:
    return Redis(connection_pool=_pool)
