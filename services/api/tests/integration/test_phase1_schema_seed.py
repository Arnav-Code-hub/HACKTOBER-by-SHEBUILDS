import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.database import Base
from app.core.roles import Role
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.departments.models import DepartmentCategory
from app.modules.files import models as files_models  # noqa: F401
from app.modules.funding.models import Allocation
from app.modules.problems.models import Cluster, Report, Support, Verification, WorkOrder
from app.modules.projects.models import Review, Submission
from app.modules.users.models import User
from app.seeds import DEMO_DIR
from app.seeds.data import seed_id, user_id
from app.seeds.loader import RESET_TABLES, seed
from tests.conftest import SERVICE_ROOT

pytestmark = pytest.mark.integration


def alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=SERVICE_ROOT,
        env=dict(os.environ, DATABASE_URL=database_url),
        capture_output=True,
        text=True,
        check=False,
    )


async def test_migration_discovers_every_table_without_schema_drift(
    db_engine: AsyncEngine,
    migrated_database: str,
) -> None:
    async with db_engine.connect() as connection:
        tables = await connection.run_sync(lambda conn: set(inspect(conn).get_table_names()))
        assert tables == {*RESET_TABLES, "alembic_version"}
        assert set(Base.metadata.tables) == set(RESET_TABLES)
        columns = await connection.run_sync(lambda conn: inspect(conn).get_columns("work_orders"))
        assert "status" not in {column["name"] for column in columns}
        fk = await connection.run_sync(lambda conn: inspect(conn).get_foreign_keys("reports"))
        assert any(key["name"] == "fk_reports_cluster_id_clusters" for key in fk)
    checked = alembic(migrated_database, "check")
    assert checked.returncode == 0, checked.stdout + checked.stderr


async def test_migration_upgrade_downgrade_upgrade_is_repeatable(postgres_url: str) -> None:
    # A separate database protects other tests' migration state. Testcontainer
    # and CI PostgreSQL users have CREATEDB; never reuse the application URL.
    name = f"phase1_migration_{uuid4().hex}"
    admin = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
    target = make_url(postgres_url).set(database=name).render_as_string(hide_password=False)
    try:
        async with admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{name}"'))
        for command in (
            ("upgrade", "head"),
            ("downgrade", "base"),
            ("upgrade", "head"),
            ("check",),
        ):
            result = alembic(target, *command)
            assert result.returncode == 0, result.stdout + result.stderr
        for _ in range(2):
            seeded = subprocess.run(
                [sys.executable, "-m", "app.seeds"],
                cwd=SERVICE_ROOT,
                env=dict(os.environ, DATABASE_URL=target, ENVIRONMENT="staging"),
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            assert seeded.returncode == 0, seeded.stdout + seeded.stderr
            assert "Demo seed committed" in seeded.stdout
    finally:
        async with admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await admin.dispose()


async def test_seed_rerun_is_identical_and_does_not_rewind_demo(db_session: AsyncSession) -> None:
    await seed(db_session)

    async def snapshot() -> dict[str, list[dict[str, object]]]:
        return {
            table: [
                dict(row)
                for row in (
                    await db_session.execute(text(f'SELECT * FROM "{table}" ORDER BY id'))
                ).mappings()
            ]
            for table in RESET_TABLES
        }

    first = await snapshot()
    await seed(db_session)
    assert await snapshot() == first
    assert len(first["users"]) == 10
    assert all(row["is_demo"] for rows in first.values() for row in rows)
    assert all(not row["is_active"] for row in first["users"])
    assert all(row["firebase_uid"].startswith("unprovisioned:") for row in first["users"])
    report = await db_session.get(Report, seed_id("report/reported"))
    report.title = "Edited during review"
    await db_session.flush()
    await seed(db_session)
    await db_session.refresh(report)
    assert report.title == "Edited during review"
    assert await db_session.scalar(select(func.count()).select_from(Support)) == 2


async def test_real_uid_file_can_provision_placeholders_without_rewriting_scope(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    await seed(db_session)
    config = json.loads((DEMO_DIR / "users.json").read_text())
    for account in config:
        account["firebase_uid"] = f"test-real-firebase-{account['role']}"
    path = tmp_path / "users.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    await seed(db_session, users_path=path)
    user = await db_session.get(User, user_id(Role.CITIZEN))
    assert user.is_active
    assert user.firebase_uid == "test-real-firebase-citizen"
    user.is_active = False
    await db_session.flush()
    await seed(db_session, users_path=path)
    await db_session.refresh(user)
    assert not user.is_active  # re-seeding must not undo an administrative disable


async def test_reference_only_performs_no_demo_writes(db_session: AsyncSession) -> None:
    await seed(db_session, reference_only=True)
    assert await db_session.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("case", ["allocation", "support", "category", "verification", "review"])
async def test_business_uniqueness_is_enforced_by_postgres(
    db_session: AsyncSession,
    case: str,
) -> None:
    await seed(db_session)
    if case == "allocation":
        record = Allocation(
            cluster_id=seed_id("cluster/in_progress"),
            work_order_id=seed_id("work-order"),
            amount_paise=10,
            allocated_by=user_id(Role.DEPARTMENT),
        )
    elif case == "support":
        record = Support(cluster_id=seed_id("cluster/prioritised"), user_id=user_id(Role.CITIZEN))
    elif case == "category":
        record = DepartmentCategory(
            district_id=seed_id("district/yadgir"),
            department_id=seed_id("department/civic"),
            category="water",
        )
    elif case == "verification":
        db_session.add(
            Verification(
                work_order_id=seed_id("work-order"),
                round=1,
                citizen_id=user_id(Role.CITIZEN),
                verdict=False,
            )
        )
        await db_session.flush()
        record = Verification(
            work_order_id=seed_id("work-order"),
            round=1,
            citizen_id=user_id(Role.CITIZEN),
            verdict=True,
        )
    else:
        db_session.add(
            Review(
                submission_id=seed_id("submission"),
                reviewer_id=user_id(Role.FACULTY),
                score=4,
                comment="First",
            )
        )
        await db_session.flush()
        record = Review(
            submission_id=seed_id("submission"),
            reviewer_id=user_id(Role.FACULTY),
            score=5,
            comment="Duplicate",
        )
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(record)
            await db_session.flush()


@pytest.mark.parametrize("case", ["paise", "cluster_status", "report_status", "link", "round"])
async def test_invalid_business_values_are_rejected_by_postgres(
    db_session: AsyncSession, case: str
) -> None:
    await seed(db_session)
    model, identity, field, value = {
        "paise": (Allocation, seed_id("allocation"), "amount_paise", -1),
        "cluster_status": (Cluster, seed_id("cluster/in_progress"), "status", "reported"),
        "report_status": (Report, seed_id("report/reported"), "status", "citizen_verified"),
        "link": (Submission, seed_id("submission"), "link", "javascript:alert(1)"),
        "round": (WorkOrder, seed_id("work-order"), "round", 0),
    }[case]
    record = await db_session.get(model, identity)
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            setattr(record, field, value)
            await db_session.flush()
