"""Async SQLAlchemy engine, session factory and the declarative base.

PostGIS and pgvector are enabled by the first migration, not here — the schema
is owned entirely by Alembic so a fresh clone and production converge.
"""

from collections.abc import AsyncGenerator
from typing import Any, Final

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

# Deterministic constraint names. Without these, Alembic autogenerate emits
# migrations that drop and recreate constraints under database-assigned names,
# and `downgrade()` cannot find them again.
NAMING_CONVENTION: Final[dict[str, str]] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by every module's models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


_settings = get_settings()

engine = create_async_engine(
    str(_settings.database_url),
    echo=_settings.debug,
    pool_size=_settings.database_pool_size,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    """FastAPI dependency. One session per request, rolled back on error."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
