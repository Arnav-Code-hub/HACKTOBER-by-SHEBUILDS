"""Hermetic API tests; only tests requesting postgres_url start a container."""

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

# Import-time settings must not require real secrets, Firebase or Redis.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@127.0.0.1:5432/test")
os.environ.setdefault("AUTH_SECRET", "test-only-not-a-real-secret")

from app.core.config import get_settings
from app.core.roles import Role
from app.core.security import Principal, get_current_principal
from app.main import create_app

SERVICE_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app() -> Iterator[FastAPI]:
    get_settings.cache_clear()
    application = create_app()
    yield application
    application.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


@pytest.fixture
def principals() -> dict[Role, Principal]:
    return {
        role: Principal(
            user_id=uuid5(NAMESPACE_URL, f"janmaang/test/{role}"),
            firebase_uid=f"test-{role}",
            role=role,
            district_id=uuid5(NAMESPACE_URL, "janmaang/test/district"),
            department_id=uuid5(NAMESPACE_URL, "janmaang/test/department"),
            institute_id=uuid5(NAMESPACE_URL, "janmaang/test/institute"),
        )
        for role in Role
    }


@pytest.fixture
def principal(request: pytest.FixtureRequest, principals: dict[Role, Principal]) -> Principal:
    # @pytest.mark.parametrize("principal", [Role.OFFICER], indirect=True)
    return principals[getattr(request, "param", Role.CITIZEN)]


@pytest.fixture
async def authed_client(app: FastAPI, principal: Principal) -> AsyncIterator[httpx.AsyncClient]:
    app.dependency_overrides[get_current_principal] = lambda: principal
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    """Use an explicitly designated test DB, or isolated plain PostgreSQL.

    Missing Docker is a failure, never a silent skip of the Phase 0 gate.
    A production DATABASE_URL is never reused automatically.
    """
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        parsed = make_url(explicit).set(drivername="postgresql+asyncpg")
        yield parsed.render_as_string(hide_password=False)
        return
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as postgres:
        parsed = make_url(postgres.get_connection_url()).set(drivername="postgresql+asyncpg")
        yield parsed.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def migrated_database(postgres_url: str) -> str:
    env = dict(os.environ, DATABASE_URL=postgres_url, ENVIRONMENT="staging")
    env.pop("REDIS_URL", None)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=SERVICE_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        pytest.fail("Alembic could not apply the test migration chain")
    return postgres_url


@pytest.fixture
async def db_engine(migrated_database: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
        await transaction.rollback()


@pytest.fixture
def fake_cloudinary() -> object:
    from tests.fakes import FakeCloudinary

    return FakeCloudinary()


@pytest.fixture
def fake_gemini() -> object:
    from tests.fakes import FakeGemini

    return FakeGemini()
