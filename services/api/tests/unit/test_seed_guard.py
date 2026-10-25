import pytest
from pydantic import PostgresDsn

from app.core.config import Settings
from app.seeds.guard import require_reset_allowed

TARGET = "postgres.project-a@pooler.example:5432/postgres"


def config(
    url: str = "postgresql+asyncpg://postgres.project-a:secret@pooler.example:5432/postgres",
    **overrides: object,
) -> Settings:
    values = {
        "database_url": PostgresDsn(url),
        "environment": "staging",
        "seed_reset_allowed": True,
        "seed_reset_targets": [TARGET],
        **overrides,
    }
    return Settings.model_validate(values)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://postgres.project-b:secret@pooler.example:5432/postgres",
        "postgresql+asyncpg://postgres.project-a:secret@other.example:5432/postgres",
        "postgresql+asyncpg://postgres.project-a:secret@pooler.example:6543/postgres",
        "postgresql+asyncpg://postgres.project-a:secret@pooler.example:5432/other",
    ],
)
def test_every_target_component_must_match(url: str) -> None:
    with pytest.raises(ValueError, match="allowlisted") as error:
        require_reset_allowed(config(url))
    assert "secret" not in str(error.value)
    assert "postgresql" not in str(error.value)


def test_password_never_affects_target_identity() -> None:
    require_reset_allowed(config())
    require_reset_allowed(
        config(
            "postgresql+asyncpg://postgres.project-a:changed%40password@pooler.example:5432/postgres"
        )
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"environment": "production"},
        {"seed_reset_allowed": False},
        {"seed_reset_targets": []},
    ],
)
def test_reset_requires_all_guards(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        require_reset_allowed(config(**overrides))
