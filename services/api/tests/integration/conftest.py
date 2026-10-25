from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.database import get_db
from app.core.roles import Role
from app.integrations.cloudinary import get_media_provider
from app.modules.auth.service import DatabaseAuthenticator
from app.modules.users.models import User
from app.seeds.data import user_id
from app.seeds.loader import reset_demo, seed
from tests.integration.phase2_fakes import MediaProvider, TokenVerifier


@dataclass
class Phase2:
    app: FastAPI
    client: httpx.AsyncClient
    media: MediaProvider
    sessions: async_sessionmaker[AsyncSession]

    def headers(self, role: Role = Role.CITIZEN, **extra: str) -> dict[str, str]:
        return {"Authorization": f"Bearer valid:live-test-{role}", **extra}


@pytest.fixture
async def phase2(
    app: FastAPI, db_engine: AsyncEngine, migrated_database: str
) -> AsyncIterator[Phase2]:
    url = make_url(migrated_database)
    settings = Settings(
        _env_file=None,
        database_url=migrated_database,
        environment="staging",
        seed_reset_allowed=True,
        seed_reset_targets=[f"{url.username}@{url.host}:{url.port or 5432}/{url.database}"],
    )
    sessions = async_sessionmaker(db_engine, expire_on_commit=False)
    async with sessions.begin() as session:
        await reset_demo(session, settings)
        await seed(session)
        for role in Role:
            await session.execute(
                update(User)
                .where(User.id == user_id(role))
                .values(
                    firebase_uid=f"live-test-{role}",
                    is_active=True,
                )
            )
    media = MediaProvider()

    async def db() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = db
    app.dependency_overrides[get_media_provider] = lambda: media
    app.state.authenticator = DatabaseAuthenticator(TokenVerifier())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield Phase2(app, client, media, sessions)
    async with sessions.begin() as session:
        await reset_demo(session, settings)
