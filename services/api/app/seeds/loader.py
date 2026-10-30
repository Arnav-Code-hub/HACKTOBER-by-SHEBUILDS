"""Insert-only demo fixtures preserve changes made during a demonstration.

Provisioning is separate from seeding: resetting demo data is explicit and
guarded. No passwords, fake tokens or authentication bypass are generated.
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings
from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.modules.departments.models import DepartmentCategory, Organization
from app.modules.funding.models import Allocation
from app.modules.problem_statements.models import ProblemStatement
from app.modules.problems.models import Cluster, Report, Support, WorkOrder
from app.modules.projects.models import Submission
from app.modules.teams.models import Team, TeamMember
from app.modules.users.models import User
from app.seeds import DEMO_DIR
from app.seeds.data import ORGANIZATIONS, SEED_AT, seed_id, user_id
from app.seeds.guard import require_reset_allowed
from app.shared.categories import Category

# Explicit application tables. Never drop a schema, authentication tables,
# extensions, or unrelated tables belonging to a hosted Postgres project.
RESET_TABLES = (
    "council_assessments",
    "team_supervisors",
    "notifications",
    "upload_intents",
    "idempotency_keys",
    "audit_events",
    "sponsorships",
    "reviews",
    "submissions",
    "team_members",
    "teams",
    "problem_statements",
    "verifications",
    "allocations",
    "media_assets",
    "work_orders",
    "supports",
    "clusters",
    "reports",
    "users",
    "department_categories",
    "organizations",
)


async def reset_demo(session: AsyncSession, settings: Settings) -> None:
    require_reset_allowed(settings)
    # No CASCADE: an unexpected external FK must make reset fail safely.
    await session.execute(
        text("TRUNCATE " + ", ".join(f'public."{table}"' for table in RESET_TABLES))
    )
    # Report codes are deliberately not reused, even across demo resets.


async def _insert(session: AsyncSession, model: type[DeclarativeBase], **values: Any) -> bool:
    values.update(created_at=SEED_AT, updated_at=SEED_AT, is_demo=True)
    result = await session.scalar(
        insert(model)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["id"])
        .returning(model.__table__.c.id)
    )
    return result is not None


def read_users(path: Path) -> dict[Role, dict[str, Any]]:
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list) or len(items) != len(Role):
        raise ValueError("The seed users file must contain exactly one entry per role.")
    result: dict[Role, dict[str, Any]] = {}
    seen_uids: set[str] = set()
    for entry in items:
        if not isinstance(entry, dict):
            raise ValueError("Every seed user must be an object.")
        role = Role(entry["role"])
        uid = entry.get("firebase_uid")
        if role in result or (
            uid is not None
            and (not isinstance(uid, str) or not uid.strip() or len(uid) > 128 or uid in seen_uids)
        ):
            raise ValueError("Seed roles and nonempty Firebase UIDs must be unique.")
        if uid:
            seen_uids.add(uid)
        result[role] = {
            "firebase_uid": uid or f"unprovisioned:{role}",
            "email": entry["email"],
            "display_name": entry["display_name"],
            "is_active": uid is not None,
        }
    if set(result) != set(Role):
        raise ValueError("A seed account is required for every role.")
    return result


async def seed(
    session: AsyncSession,
    *,
    reference_only: bool = False,
    users_path: Path | None = None,
) -> None:
    """The prototype has no imported reference dataset. Demo rows are opt-in."""
    if reference_only:
        return
    accounts = read_users(users_path or DEMO_DIR / "users.json")
    district = seed_id("district/yadgir")
    department = seed_id("department/civic")
    institute = seed_id("institute")
    for entry in ORGANIZATIONS:
        values = {key: value for key, value in entry.items() if key != "key"}
        await _insert(
            session,
            Organization,
            id=seed_id(entry["key"]),
            parent_id=None if entry["type"] == "district" else district,
            **values,
        )
    for category in Category:
        await _insert(
            session,
            DepartmentCategory,
            id=seed_id(f"category/{category}"),
            district_id=district,
            department_id=department,
            category=category,
        )
    for role, account in accounts.items():
        await _insert(
            session,
            User,
            id=user_id(role),
            role=role,
            district_id=None if role == Role.SUPER_ADMIN else district,
            department_id=department if role in {Role.DEPARTMENT, Role.OFFICER} else None,
            institute_id=institute
            if role in {Role.INSTITUTE, Role.FACULTY, Role.STUDENT}
            else None,
            organization_id=seed_id("industry") if role == Role.INDUSTRY else None,
            **account,
        )
        # Only explicit real-UID configuration provisions an existing placeholder.
        # Already provisioned users' role/scope/active state are never reset here.
        if account["is_active"]:
            user = await session.get(User, user_id(role))
            if user is not None and user.firebase_uid.startswith("unprovisioned:"):
                user.firebase_uid = account["firebase_uid"]
                user.email = account["email"]
                user.display_name = account["display_name"]
                user.is_active = True
                await session.flush()
    for case in ("reported", "prioritised", "in_progress"):
        report_id = seed_id(f"report/{case}")
        inserted = await _insert(
            session,
            Report,
            id=report_id,
            reporter_id=user_id(Role.CITIZEN),
            district_id=district,
            title=f"DEMO: {case.replace('_', ' ')} handpump case",
            transcript="Demonstration report: the public handpump needs repair.",
            summary="Synthetic hackathon case; no actual repair or adoption is claimed.",
            category="water",
            severity="high",
            status="reported" if case == "reported" else "verified",
            status_changed_at=SEED_AT,
            latitude=16.76,
            longitude=77.14,
            location_label="Demonstration Ward 4, Yadgir",
            channel="text",
        )
        if case == "reported":
            continue
        cluster_id = seed_id(f"cluster/{case}")
        await _insert(
            session,
            Cluster,
            id=cluster_id,
            district_id=district,
            category="water",
            anchor_report_id=report_id,
            status=case,
            status_changed_at=SEED_AT,
            infrastructure_gap=None,
            equity_index=None,
            inputs_are_demo=True,
        )
        if inserted:
            report = await session.get(Report, report_id)
            assert report is not None
            report.cluster_id = cluster_id
            await session.flush()
        # There is only one seeded citizen. One support is honest; staff/student
        # accounts are not counted as additional citizen supporters.
        await _insert(
            session,
            Support,
            id=seed_id(f"support/{case}"),
            cluster_id=cluster_id,
            user_id=user_id(Role.CITIZEN),
        )
        if case == "in_progress":
            await _insert(
                session,
                WorkOrder,
                id=seed_id("work-order"),
                cluster_id=cluster_id,
                district_id=district,
                department_id=department,
                officer_id=user_id(Role.OFFICER),
                round=1,
                assigned_at=SEED_AT,
                notes="DEMO: inspection started.",
                instructions="Demonstration repair only.",
            )
            await _insert(
                session,
                Allocation,
                id=seed_id("allocation"),
                cluster_id=cluster_id,
                work_order_id=seed_id("work-order"),
                amount_paise=250000,
                allocated_by=user_id(Role.DEPARTMENT),
            )
    await _insert(
        session,
        ProblemStatement,
        id=seed_id("statement"),
        department_id=department,
        district_id=district,
        created_by=user_id(Role.DEPARTMENT),
        cluster_id=seed_id("cluster/prioritised"),
        title="DEMO: reliable public handpumps",
        body="Propose a maintenance alert system. This is not an approved public repair.",
        status="published",
        published_at=SEED_AT,
    )
    await _insert(
        session,
        Team,
        id=seed_id("team"),
        name="Demonstration student team",
        institute_id=institute,
        statement_id=seed_id("statement"),
        created_by=user_id(Role.STUDENT),
        institute_approved=True,
        approved_by=user_id(Role.INSTITUTE),
        approved_at=SEED_AT,
    )
    await _insert(
        session,
        TeamMember,
        id=seed_id("team-member"),
        team_id=seed_id("team"),
        user_id=user_id(Role.STUDENT),
    )
    await _insert(
        session,
        Submission,
        id=seed_id("submission"),
        team_id=seed_id("team"),
        statement_id=seed_id("statement"),
        submitted_by=user_id(Role.STUDENT),
        title="DEMO: maintenance alert proposal",
        summary="Synthetic proposal for review.",
        link=None,
        submitted_at=SEED_AT,
    )
    await _insert(
        session,
        AuditEventRecord,
        id=seed_id("seed-audit"),
        actor_id=user_id(Role.SUPER_ADMIN),
        actor_role=Role.SUPER_ADMIN,
        action="demo.seeded",
        entity_type="organization",
        entity_id=district,
        district_id=district,
        before=None,
        after={"is_demo": True},
        reason="Synthetic starting fixtures, not historical user actions.",
    )


async def seed_counts(session: AsyncSession) -> dict[str, int]:
    """Only aggregate counts are printed; no database URL, UID or credential."""
    from sqlalchemy import func

    return {
        name: int(await session.scalar(select(func.count()).select_from(model)) or 0)
        for name, model in {
            "users": User,
            "reports": Report,
            "clusters": Cluster,
            "work_orders": WorkOrder,
        }.items()
    }
