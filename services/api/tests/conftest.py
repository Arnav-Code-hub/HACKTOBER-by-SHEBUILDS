"""Shared pytest fixtures.

Integration tests spin up a real Postgres with PostGIS via testcontainers rather
than mocking the database — the geo queries and the ranking SQL are exactly the
parts worth testing for real.
"""

import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


# TODO(tests): db_engine / db_session / client / authed_client fixtures.
