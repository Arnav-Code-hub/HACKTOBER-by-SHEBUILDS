"""Real PostgreSQL partner workflows, concurrency, scope and audit rollback."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.modules.departments.models import Organization
from app.modules.funding.models import Allocation, Sponsorship
from app.modules.problem_statements.models import ProblemStatement
from app.modules.projects.models import Review, Submission
from app.modules.teams.models import Team, TeamMember
from app.modules.users.models import User
from app.persistence.audit import SqlAuditWriter
from app.seeds.data import seed_id, user_id
from tests.integration.conftest import Phase2
from tests.integration.test_phase4_api import DISTRICT, add_user

pytestmark = pytest.mark.integration
STATEMENT = seed_id("statement")
TEAM = seed_id("team")
SUBMISSION = seed_id("submission")


async def post(phase2, path, role, body=None, key="first"):
    return await phase2.client.post(
        f"/api/v1/{path}", json=body, headers=phase2.headers(role, **{"Idempotency-Key": key})
    )


async def get(phase2, path, role):
    return await phase2.client.get(f"/api/v1/{path}", headers=phase2.headers(role))


def change_body(**extra):
    return {
        "role": "citizen",
        "district_id": str(DISTRICT),
        "department_id": None,
        "institute_id": None,
        "organization_id": None,
        "reason": "Demo reassignment",
        **extra,
    }


async def test_complete_partner_journey_and_summary(phase2: Phase2):
    body = {"name": "Water alerts", "statement_id": str(STATEMENT)}
    created = await post(phase2, "teams", Role.STUDENT, body)
    assert created.status_code == 201, created.text
    team = created.json()
    assert team["member_count"] == 1 and not team["institute_approved"]
    retry = await post(phase2, "teams", Role.STUDENT, body)
    assert retry.json() == team
    listed = await get(phase2, "teams?mine=true", Role.STUDENT)
    assert team["id"] in [t["id"] for t in listed.json()["items"]]
    submission = {
        "team_id": team["id"],
        "title": "Sensor concept",
        "summary": "A proposal",
        "link": "https://example.test/demo",
    }
    denied = await post(phase2, "submissions", Role.STUDENT, submission)
    assert denied.status_code == 409
    approved = await post(phase2, f"teams/{team['id']}/approve", Role.INSTITUTE)
    assert approved.status_code == 200 and approved.json()["institute_approved"]
    assert (
        await post(phase2, f"teams/{team['id']}/approve", Role.INSTITUTE)
    ).json() == approved.json()
    submitted = await post(phase2, "submissions", Role.STUDENT, submission)
    assert submitted.status_code == 201, submitted.text
    assert (await post(phase2, "submissions", Role.STUDENT, submission)).json() == submitted.json()
    sid = submitted.json()["id"]
    reviewed = await post(
        phase2,
        f"submissions/{sid}/reviews",
        Role.FACULTY,
        {"score": 4, "comment": "Feasible prototype"},
    )
    assert reviewed.status_code == 201, reviewed.text
    assert (
        await post(
            phase2,
            f"submissions/{sid}/reviews",
            Role.FACULTY,
            {"score": 4, "comment": "Feasible prototype"},
        )
    ).json() == reviewed.json()
    duplicate = await post(
        phase2,
        f"submissions/{sid}/reviews",
        Role.FACULTY,
        {"score": 4, "comment": "Feasible prototype"},
        "different",
    )
    assert duplicate.status_code == 409
    faculty = await get(phase2, "submissions?institute=me", Role.FACULTY)
    row = next(r for r in faculty.json()["items"] if r["id"] == sid)
    assert row["review_count"] == 1 and row["my_review"]["score"] == 4
    student = await get(phase2, "submissions?mine=true", Role.STUDENT)
    assert all(r["my_review"] is None for r in student.json()["items"])
    pledge = await post(
        phase2, f"statements/{STATEMENT}/sponsorships", Role.INDUSTRY, {"amount_paise": 500000}
    )
    assert pledge.status_code == 201 and pledge.json()["status"] == "pledged", pledge.text
    assert (
        await post(
            phase2, f"statements/{STATEMENT}/sponsorships", Role.INDUSTRY, {"amount_paise": 500000}
        )
    ).json() == pledge.json()
    assert len((await get(phase2, "sponsorships?mine=true", Role.INDUSTRY)).json()["items"]) == 1
    summary = (await get(phase2, "admin/summary", Role.GOV_ADMIN)).json()
    assert summary["allocated_paise"] == 250000
    assert summary["pledged_paise"] == 500000
    assert summary["reports_by_status"] == {"reported": 1, "prioritised": 1, "in_progress": 1}
    assert summary["work_orders_by_status"] == {"in_progress": 1}
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Allocation)) == 1
        assert (
            await session.scalar(
                select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team["id"])
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEventRecord)
                .where(
                    AuditEventRecord.action == "team.approved",
                    AuditEventRecord.entity_id == team["id"],
                )
            )
            == 1
        )


@pytest.mark.parametrize(
    "link",
    [
        "javascript:alert(1)",
        "http://example.test",
        "https://a:b@example.test",
        "https://",
        "https://example.test/a b",
    ],
)
async def test_invalid_submission_links(phase2: Phase2, link):
    result = await post(
        phase2,
        "submissions",
        Role.STUDENT,
        {"team_id": str(TEAM), "title": "Demo", "summary": "Demo", "link": link},
    )
    assert result.status_code == 422


@pytest.mark.parametrize("link", ["HTTPS://example.test/demo", "https:example.test/demo"])
async def test_accepted_urls_are_canonicalized_before_storage(phase2: Phase2, link):
    result = await post(
        phase2,
        "submissions",
        Role.STUDENT,
        {"team_id": str(TEAM), "title": "Demo", "summary": "Demo", "link": link},
    )
    assert result.status_code == 201, result.text
    assert result.json()["link"] == "https://example.test/demo"
    async with phase2.sessions() as session:
        saved = await session.get(Submission, result.json()["id"])
        assert saved.link == "https://example.test/demo"


async def test_draft_and_other_district_statements_are_inaccessible(phase2: Phase2):
    async with phase2.sessions.begin() as session:
        statement = await session.get(ProblemStatement, STATEMENT)
        statement.status = "draft"
        statement.published_at = None
    for path, role, body in [
        ("teams", Role.STUDENT, {"name": "Hidden", "statement_id": str(STATEMENT)}),
        (f"statements/{STATEMENT}/sponsorships", Role.INDUSTRY, {"amount_paise": 100}),
    ]:
        assert (await post(phase2, path, role, body)).status_code == 404
    async with phase2.sessions.begin() as session:
        statement = await session.get(ProblemStatement, STATEMENT)
        statement.status = "published"
        statement.published_at = datetime.now(UTC)
        statement.district_id = seed_id("district/boundary")
    assert (
        await post(
            phase2, "teams", Role.STUDENT, {"name": "Hidden", "statement_id": str(STATEMENT)}
        )
    ).status_code == 404
    assert (
        await post(
            phase2, f"statements/{STATEMENT}/sponsorships", Role.INDUSTRY, {"amount_paise": 100}
        )
    ).status_code == 404


async def test_other_institute_and_non_member_scope(phase2: Phase2):
    institute = uuid4()
    async with phase2.sessions.begin() as session:
        session.add(
            Organization(
                id=institute,
                type="institute",
                parent_id=DISTRICT,
                name="Other institute",
                code=f"OTHER-{institute.hex}",
                is_active=True,
            )
        )
    for role in [Role.FACULTY, Role.INSTITUTE]:
        headers = await add_user(phase2, f"other-{role}", role, institute_id=institute)
        route = (
            f"submissions/{SUBMISSION}/reviews" if role == Role.FACULTY else f"teams/{TEAM}/approve"
        )
        result = await phase2.client.post(
            f"/api/v1/{route}",
            json={"score": 4, "comment": "Review"} if role == Role.FACULTY else None,
            headers={**headers, "Idempotency-Key": "other"},
        )
        assert result.status_code == 404, result.text
        listing = await phase2.client.get("/api/v1/submissions?institute=me", headers=headers)
        assert listing.json()["items"] == []
    headers = await add_user(
        phase2, "unrelated-student", Role.STUDENT, institute_id=seed_id("institute")
    )
    assert (await phase2.client.get("/api/v1/teams?mine=true", headers=headers)).json()[
        "items"
    ] == []
    result = await phase2.client.post(
        "/api/v1/submissions",
        json={"team_id": str(TEAM), "title": "Not mine", "summary": "Not mine"},
        headers={**headers, "Idempotency-Key": "no"},
    )
    assert result.status_code == 404


async def test_concurrent_review_and_pledge_retries(phase2: Phase2):
    path = f"submissions/{SUBMISSION}/reviews"
    body = {"score": 5, "comment": "Reviewed once"}
    results = await asyncio.gather(
        post(phase2, path, Role.FACULTY, body, "a"), post(phase2, path, Role.FACULTY, body, "b")
    )
    assert sorted(r.status_code for r in results) == [201, 409]
    path = f"statements/{STATEMENT}/sponsorships"
    results = await asyncio.gather(
        *(post(phase2, path, Role.INDUSTRY, {"amount_paise": 100}, "same") for _ in range(2))
    )
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json() == results[1].json()
    assert (
        await post(phase2, path, Role.INDUSTRY, {"amount_paise": 101}, "same")
    ).status_code == 409
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Review)) == 1
        assert await session.scalar(select(func.count()).select_from(Sponsorship)) == 1


@pytest.mark.parametrize(
    "path",
    [
        "teams?mine=true",
        "submissions?mine=true",
        "sponsorships?mine=true",
        "admin/summary",
        "admin/audit",
        "admin/users",
        "organizations",
    ],
)
async def test_citizen_cannot_access_partner_or_admin_lists(phase2: Phase2, path):
    assert (await get(phase2, path, Role.CITIZEN)).status_code == 403


async def test_admin_change_validates_scope_and_blocks_self(phase2: Phase2):
    path = f"/api/v1/admin/users/{user_id(Role.STUDENT)}"
    headers = phase2.headers(Role.SUPER_ADMIN)
    invalid = await phase2.client.patch(
        path, json=change_body(role="officer", department_id=str(uuid4())), headers=headers
    )
    assert invalid.status_code == 422, invalid.text
    async with phase2.sessions() as session:
        assert (await session.get(User, user_id(Role.STUDENT))).role == "student"
    valid = await phase2.client.patch(
        path,
        json=change_body(role="industry", organization_id=str(seed_id("industry"))),
        headers=headers,
    )
    assert valid.status_code == 200, valid.text
    assert valid.json()["institute_id"] is None
    assert valid.json()["organization_id"] == str(seed_id("industry"))
    profile = await get(phase2, "users/me", Role.STUDENT)
    assert profile.json()["role"] == "industry"
    audit = (await get(phase2, "admin/audit", Role.GOV_ADMIN)).json()["items"]
    changed = [e for e in audit if e["action"] == "user.scope_changed"]
    assert len(changed) == 1 and changed[0]["reason"] == "Demo reassignment"
    self_change = await phase2.client.patch(
        f"/api/v1/admin/users/{user_id(Role.SUPER_ADMIN)}", json=change_body(), headers=headers
    )
    assert self_change.status_code == 403
    assert (await get(phase2, "admin/users", Role.GOV_ADMIN)).status_code == 403
    assert (await get(phase2, "organizations", Role.GOV_ADMIN)).status_code == 403
    assert (await get(phase2, "admin/users", Role.SUPER_ADMIN)).status_code == 200
    assert (await get(phase2, "organizations", Role.SUPER_ADMIN)).status_code == 200


async def test_admin_can_correct_a_disabled_accounts_scope(phase2: Phase2):
    path = f"/api/v1/admin/users/{user_id(Role.STUDENT)}"
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(User).where(User.id == user_id(Role.STUDENT)).values(is_active=False)
        )
    headers = phase2.headers(Role.SUPER_ADMIN)
    changed = await phase2.client.patch(path, json=change_body(), headers=headers)
    assert changed.status_code == 200, changed.text
    # Scope is still validated, and the account stays disabled.
    invalid = await phase2.client.patch(
        path, json=change_body(role="officer", department_id=str(uuid4())), headers=headers
    )
    assert invalid.status_code == 422, invalid.text
    async with phase2.sessions() as session:
        user = await session.get(User, user_id(Role.STUDENT))
        assert (user.role, user.is_active) == ("citizen", False)


async def test_audit_scope_is_stored_not_actor_scope(phase2: Phase2):
    async with phase2.sessions.begin() as session:
        session.add(
            AuditEventRecord(
                actor_id=user_id(Role.SUPER_ADMIN),
                actor_role="super_admin",
                action="other.district",
                entity_type="organization",
                entity_id=seed_id("district/boundary"),
                district_id=seed_id("district/boundary"),
            )
        )
    own = (await get(phase2, "admin/audit", Role.GOV_ADMIN)).json()["items"]
    all_events = (await get(phase2, "admin/audit", Role.SUPER_ADMIN)).json()["items"]
    assert "other.district" not in [e["action"] for e in own]
    assert "demo.seeded" in [e["action"] for e in own]
    assert "other.district" in [e["action"] for e in all_events]
    assert (await get(phase2, "admin/audit?limit=0", Role.GOV_ADMIN)).status_code == 422


async def test_audit_failure_rolls_back_partner_and_admin_writes(phase2: Phase2, monkeypatch):
    async def fail(*args, **kwargs):
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr(SqlAuditWriter, "log_event", fail)
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        await post(
            phase2, "teams", Role.STUDENT, {"name": "Rolled back", "statement_id": str(STATEMENT)}
        )
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        await phase2.client.patch(
            f"/api/v1/admin/users/{user_id(Role.STUDENT)}",
            json=change_body(),
            headers=phase2.headers(Role.SUPER_ADMIN),
        )
    async with phase2.sessions() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(Team).where(Team.name == "Rolled back")
            )
            == 0
        )
        assert (await session.get(User, user_id(Role.STUDENT))).role == "student"


@pytest.mark.parametrize("amount", [0, -1, 1.5, True, "100", 10**13 + 1])
async def test_invalid_pledge_amount(phase2: Phase2, amount):
    assert (
        await post(
            phase2, f"statements/{STATEMENT}/sponsorships", Role.INDUSTRY, {"amount_paise": amount}
        )
    ).status_code == 422


@pytest.mark.parametrize(
    "path,body",
    [
        ("teams", {"name": "Not allowed", "statement_id": str(STATEMENT)}),
        (f"teams/{TEAM}/approve", None),
        ("submissions", {"team_id": str(TEAM), "title": "No", "summary": "No"}),
        (f"submissions/{SUBMISSION}/reviews", {"score": 4, "comment": "No"}),
        (f"statements/{STATEMENT}/sponsorships", {"amount_paise": 100}),
    ],
)
async def test_citizen_cannot_write_partner_records(phase2: Phase2, path, body):
    assert (await post(phase2, path, Role.CITIZEN, body)).status_code == 403


@pytest.mark.parametrize(
    "path,role,body",
    [
        (f"teams/{TEAM}/approve", Role.INSTITUTE, None),
        (
            "submissions",
            Role.STUDENT,
            {"team_id": str(TEAM), "title": "Rollback", "summary": "Rollback"},
        ),
        (f"submissions/{SUBMISSION}/reviews", Role.FACULTY, {"score": 4, "comment": "Rollback"}),
        (f"statements/{STATEMENT}/sponsorships", Role.INDUSTRY, {"amount_paise": 100}),
    ],
)
async def test_each_partner_write_rolls_back_on_audit_failure(
    phase2: Phase2, monkeypatch, path, role, body
):
    if role == Role.INSTITUTE:
        async with phase2.sessions.begin() as session:
            team = await session.get(Team, TEAM)
            team.institute_approved = False
            team.approved_by = None
            team.approved_at = None

    async def fail(*args, **kwargs):
        raise RuntimeError("No audit")

    with monkeypatch.context() as patch:
        patch.setattr(SqlAuditWriter, "log_event", fail)
        with pytest.raises(RuntimeError, match="No audit"):
            await post(phase2, path, role, body)
    async with phase2.sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Review)) == 0
        assert await session.scalar(select(func.count()).select_from(Sponsorship)) == 0
        assert await session.scalar(select(func.count()).select_from(Submission)) == 1
        if role == Role.INSTITUTE:
            assert not (await session.get(Team, TEAM)).institute_approved
    # The failed request must not consume its retry key.
    assert (await post(phase2, path, role, body)).status_code in {200, 201}


async def test_admin_summary_is_district_scoped_and_does_not_multiply_money(phase2: Phase2):
    async with phase2.sessions.begin() as session:
        other = ProblemStatement(
            id=uuid4(),
            title="Elsewhere",
            body="Demo",
            status="published",
            district_id=seed_id("district/boundary"),
            department_id=seed_id("department/civic"),
            created_by=user_id(Role.DEPARTMENT),
            published_at=datetime.now(UTC),
        )
        session.add(other)
        await session.flush()
        session.add(
            Sponsorship(
                statement_id=other.id,
                organization_id=seed_id("industry"),
                pledged_by=user_id(Role.INDUSTRY),
                amount_paise=999,
            )
        )
    for index in range(2):
        assert (
            await post(
                phase2,
                f"statements/{STATEMENT}/sponsorships",
                Role.INDUSTRY,
                {"amount_paise": 100},
                str(index),
            )
        ).status_code == 201
    own = (await get(phase2, "admin/summary", Role.GOV_ADMIN)).json()
    all_districts = (await get(phase2, "admin/summary", Role.SUPER_ADMIN)).json()
    assert own["pledged_paise"] == 200
    assert all_districts["pledged_paise"] == 1199
    assert own["allocated_paise"] == all_districts["allocated_paise"] == 250000


async def test_admin_scope_validation_and_unauthorized_patch(phase2: Phase2):
    path = f"/api/v1/admin/users/{user_id(Role.STUDENT)}"
    for body in [
        change_body(role="industry"),
        change_body(role="faculty"),
        change_body(district_id=None),
        change_body(reason="   "),
        change_body(district_id=str(seed_id("district/boundary"))),
    ]:
        response = await phase2.client.patch(
            path, json=body, headers=phase2.headers(Role.SUPER_ADMIN)
        )
        assert response.status_code == 422, response.text
    assert (
        await phase2.client.patch(path, json=change_body(), headers=phase2.headers(Role.GOV_ADMIN))
    ).status_code == 403
    assert (
        await phase2.client.patch(
            f"/api/v1/admin/users/{uuid4()}",
            json=change_body(),
            headers=phase2.headers(Role.SUPER_ADMIN),
        )
    ).status_code == 404


async def test_same_institute_other_faculty_can_review_once_each(phase2: Phase2):
    first = await post(
        phase2,
        f"submissions/{SUBMISSION}/reviews",
        Role.FACULTY,
        {"score": 5, "comment": "First faculty"},
    )
    assert first.status_code == 201
    headers = await add_user(
        phase2, "second-faculty", Role.FACULTY, institute_id=seed_id("institute")
    )
    second = await phase2.client.post(
        f"/api/v1/submissions/{SUBMISSION}/reviews",
        json={"score": 3, "comment": "Second faculty"},
        headers={**headers, "Idempotency-Key": "first"},
    )
    assert second.status_code == 201
    listing = (await phase2.client.get("/api/v1/submissions?institute=me", headers=headers)).json()
    assert listing["items"][0]["review_count"] == 2
    assert listing["items"][0]["my_review"] == {"score": 3, "comment": "Second faculty"}
