import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@pytest.mark.integration
async def test_postgres_and_migration_version(db_session: AsyncSession) -> None:
    assert await db_session.scalar(text("SELECT 1")) == 1
    assert await db_session.scalar(text("SELECT to_regclass('public.alembic_version')")) is not None


@pytest.mark.integration
async def test_commits_inside_savepoints_do_not_escape_the_outer_transaction(
    db_engine: AsyncEngine,
) -> None:
    async with db_engine.connect() as connection:
        outer = await connection.begin()
        async with AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint"
        ) as session:
            await session.execute(text("CREATE TABLE phase0_probe (value integer)"))
            await session.execute(text("INSERT INTO phase0_probe VALUES (1)"))
            await session.commit()
            assert await session.scalar(text("SELECT count(*) FROM phase0_probe")) == 1
        await outer.rollback()
    async with db_engine.connect() as connection:
        assert await connection.scalar(text("SELECT to_regclass('public.phase0_probe')")) is None
