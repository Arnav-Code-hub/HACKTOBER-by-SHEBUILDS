"""Alembic environment.

Reads DATABASE_URL from app settings rather than alembic.ini, so migrations and
the application can never disagree about which database they mean.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.core.database import Base

# Importing every module's models registers them on Base.metadata so
# --autogenerate sees the full schema. Add new modules here.
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.council import models as council_models  # noqa: F401
from app.modules.departments import models as departments_models  # noqa: F401
from app.modules.files import models as files_models  # noqa: F401
from app.modules.funding import models as funding_models  # noqa: F401
from app.modules.notifications import models as notifications_models  # noqa: F401
from app.modules.problem_statements import models as statement_models  # noqa: F401
from app.modules.problems import models as problems_models  # noqa: F401
from app.modules.projects import models as projects_models  # noqa: F401
from app.modules.rbac import models as rbac_models  # noqa: F401
from app.modules.teams import models as teams_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ConfigParser interpolation must not reinterpret percent-encoded passwords.
config.set_main_option("sqlalchemy.url", str(get_settings().database_url).replace("%", "%%"))
target_metadata = Base.metadata


def _include_object(obj, name, type_, reflected, compare_to) -> bool:  # type: ignore[no-untyped-def]
    """Skip PostGIS's own bookkeeping tables so autogenerate ignores them."""
    return not (
        type_ == "table" and name in {"spatial_ref_sys", "geography_columns", "geometry_columns"}
    )


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=_include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=_include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
