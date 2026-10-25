"""Phase 4: funding, work orders, officer evidence and problem statements."""

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, update

from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.modules.departments.models import Organization
from app.modules.files.models import MediaAsset
from app.modules.funding.models import Allocation
from app.modules.problem_statements.models import ProblemStatement
from app.modules.problems.models import Cluster, WorkOrder
from app.modules.users.models import User
from app.seeds.data import seed_id, user_id
from tests.integration.conftest import Phase2
from tests.integration.test_phase2_api import completed_media

pytestmark = pytest.mark.integration

PRIORITISED = seed_id("cluster/prioritised")
IN_PROGRESS = seed_id("cluster/in_progress")
SEEDED_ORDER = seed_id("work-order")
DISTRICT = seed_id("district/yadgir")
CIVIC = seed_id("department/civic")
OFFICER = user_id(Role.OFFICER)


def fund_body(**values: object) -> dict[str, object]:
    return {"amount_paise": 15_000_000, "officer_id": str(OFFICER), **values}


async def fund(phase2: Phase2, key: str, cluster: UUID = PRIORITISED, role=Role.DEPARTMENT, **body):
    return await phase2.client.post(
        f"/api/v1/clusters/{cluster}/fund",
        json=fund_body(**body),
        headers=phase2.headers(role, **{"Idempotency-Key": key}),
    )


async def add_user(phase2: Phase2, uid: str, role: Role, **scope: object) -> dict[str, str]:
    async with phase2.sessions.begin() as session:
        session.add(
            User(
                id=uuid4(),
                firebase_uid=uid,
                role=role,
                district_id=scope.get("district_id", DISTRICT),
                department_id=scope.get("department_id"),
                institute_id=scope.get("institute_id"),
                organization_id=scope.get("organization_id"),
                display_name=uid,
                email=f"{uid}@example.test",
                is_active=True,
            )
        )
    return {"Authorization": f"Bearer valid:{uid}"}


async def other_department(phase2: Phase2) -> UUID:
    department = uuid4()
    async with phase2.sessions.begin() as session:
        session.add(
            Organization(
                id=department,
                type="department",
                parent_id=DISTRICT,
                name="Roads (other)",
                code=f"ROADS-{department.hex[:6]}",
                is_active=True,
            )
        )
    return department


async def counts(phase2: Phase2) -> tuple[int, int]:
    async with phase2.sessions() as session:
        allocations = await session.scalar(
            select(func.count()).select_from(Allocation).where(Allocation.cluster_id == PRIORITISED)
        )
        orders = await session.scalar(
            select(func.count()).select_from(WorkOrder).where(WorkOrder.cluster_id == PRIORITISED)
        )
    return allocations or 0, orders or 0


# ------------------------------------------------------------------ officers


async def test_department_lists_only_its_own_active_officers(phase2: Phase2) -> None:
    response = await phase2.client.get(
        "/api/v1/users?role=officer", headers=phase2.headers(Role.DEPARTMENT)
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [str(OFFICER)]

    elsewhere = await other_department(phase2)
    await add_user(phase2, "roads-officer", Role.OFFICER, department_id=elsewhere)
    again = await phase2.client.get(
        "/api/v1/users?role=officer", headers=phase2.headers(Role.DEPARTMENT)
    )
    assert [item["id"] for item in again.json()["items"]] == [str(OFFICER)]

    for role in [Role.CITIZEN, Role.OFFICER, Role.PANCHAYAT]:
        denied = await phase2.client.get("/api/v1/users?role=officer", headers=phase2.headers(role))
        assert denied.status_code == 403
    wrong = await phase2.client.get(
        "/api/v1/users?role=citizen", headers=phase2.headers(Role.DEPARTMENT)
    )
    assert wrong.status_code == 422


# ------------------------------------------------------------------- funding


async def test_funding_records_allocation_work_order_status_and_audit(phase2: Phase2) -> None:
    response = await fund(phase2, "fund-1", notes="Replace the cylinder.")
    assert response.status_code == 201, response.text
    result = response.json()
    async with phase2.sessions() as session:
        cluster = await session.get(Cluster, PRIORITISED)
        assert cluster.status == "funded"
        work = await session.get(WorkOrder, UUID(result["work_order_id"]))
        assert (work.officer_id, work.department_id, work.round) == (OFFICER, CIVIC, 1)
        assert work.instructions == "Replace the cylinder."
        allocation = await session.get(Allocation, UUID(result["allocation_id"]))
        assert allocation.amount_paise == 15_000_000
        event = (
            await session.scalars(
                select(AuditEventRecord).where(AuditEventRecord.action == "cluster.funded")
            )
        ).one()
        assert event.district_id == DISTRICT and event.after["amount_paise"] == 15_000_000

    # Funded work leaves the ranking.
    ranked = await phase2.client.get(
        "/api/v1/clusters/ranked", headers=phase2.headers(Role.DEPARTMENT)
    )
    assert str(PRIORITISED) not in {item["id"] for item in ranked.json()["items"]}


async def test_exact_retries_all_receive_the_original_success(phase2: Phase2) -> None:
    responses = await asyncio.gather(*[fund(phase2, "same-key") for _ in range(4)])
    assert [r.status_code for r in responses] == [201] * 4
    assert len({r.text for r in responses}) == 1
    assert await counts(phase2) == (1, 1)


async def test_competing_requests_fund_once_and_the_rest_conflict(phase2: Phase2) -> None:
    responses = await asyncio.gather(*[fund(phase2, f"key-{n}") for n in range(4)])
    assert sorted(r.status_code for r in responses) == [201, 409, 409, 409]
    assert await counts(phase2) == (1, 1)


async def test_same_key_with_different_data_is_refused(phase2: Phase2) -> None:
    assert (await fund(phase2, "reused")).status_code == 201
    assert (await fund(phase2, "reused", amount_paise=1)).status_code == 409
    assert await counts(phase2) == (1, 1)


async def test_funding_scope_rules(phase2: Phase2) -> None:
    elsewhere = await other_department(phase2)
    await add_user(phase2, "roads-officer-2", Role.OFFICER, department_id=elsewhere)
    async with phase2.sessions() as session:
        foreign_officer = (
            await session.scalars(select(User.id).where(User.firebase_uid == "roads-officer-2"))
        ).one()

    # An officer from another department cannot be assigned (422).
    assert (
        await fund(phase2, "foreign-officer", officer_id=str(foreign_officer))
    ).status_code == 422
    # Another department cannot assign the civic department's officer (422);
    # the responsibility rule itself is covered by the next test (403).
    roads = await add_user(phase2, "roads-dept", Role.DEPARTMENT, department_id=elsewhere)
    refused = await phase2.client.post(
        f"/api/v1/clusters/{PRIORITISED}/fund",
        json=fund_body(),
        headers={**roads, "Idempotency-Key": "roads"},
    )
    assert refused.status_code == 422
    # Other roles cannot fund at all; an already-executing cluster conflicts.
    for role in [Role.CITIZEN, Role.PANCHAYAT, Role.OFFICER, Role.GOV_ADMIN]:
        assert (await fund(phase2, f"role-{role}", role=role)).status_code == 403
    assert (await fund(phase2, "in-progress", cluster=IN_PROGRESS)).status_code == 409
    for invalid in [0, -5, "100", 10**14]:
        assert (await fund(phase2, f"amount-{invalid}", amount_paise=invalid)).status_code == 422
    assert await counts(phase2) == (0, 0)


async def test_a_non_responsible_department_with_its_own_officer_gets_403(
    phase2: Phase2,
) -> None:
    elsewhere = await other_department(phase2)
    await add_user(phase2, "roads-officer-3", Role.OFFICER, department_id=elsewhere)
    roads = await add_user(phase2, "roads-dept-2", Role.DEPARTMENT, department_id=elsewhere)
    async with phase2.sessions() as session:
        own_officer = (
            await session.scalars(select(User.id).where(User.firebase_uid == "roads-officer-3"))
        ).one()
    response = await phase2.client.post(
        f"/api/v1/clusters/{PRIORITISED}/fund",
        json=fund_body(officer_id=str(own_officer)),
        headers={**roads, "Idempotency-Key": "roads-own"},
    )
    assert response.status_code == 403
    assert await counts(phase2) == (0, 0)


# --------------------------------------------------------------- work orders


async def test_officer_lists_updates_and_completes_their_work(phase2: Phase2) -> None:
    funded = (await fund(phase2, "fund-for-officer")).json()
    order_id = funded["work_order_id"]
    officer = phase2.headers(Role.OFFICER)

    listed = await phase2.client.get("/api/v1/work-orders?mine=true", headers=officer)
    assert listed.status_code == 200, listed.text
    items = {item["id"]: item for item in listed.json()["items"]}
    assert set(items) == {order_id, str(SEEDED_ORDER)}
    assert items[order_id]["status"] == "funded"
    assert items[order_id]["allocated_paise"] == 15_000_000

    # The first progress note starts the work.
    update = await phase2.client.patch(
        f"/api/v1/work-orders/{order_id}", json={"notes": "Materials ordered."}, headers=officer
    )
    assert update.status_code == 200 and update.json()["status"] == "in_progress"

    photo = await completed_media(phase2, Role.OFFICER)
    complete = await phase2.client.post(
        f"/api/v1/work-orders/{order_id}/complete",
        json={"media_ids": [photo], "expected_round": 1},
        headers={**officer, "Idempotency-Key": "complete-1"},
    )
    assert complete.status_code == 200, complete.text
    assert complete.json() == {"id": order_id, "status": "awaiting_verification"}
    replay = await phase2.client.post(
        f"/api/v1/work-orders/{order_id}/complete",
        json={"media_ids": [photo], "expected_round": 1},
        headers={**officer, "Idempotency-Key": "complete-1"},
    )
    assert replay.status_code == 200 and replay.json() == complete.json()
    async with phase2.sessions() as session:
        asset = await session.get(MediaAsset, UUID(photo))
        assert (str(asset.work_order_id), asset.round) == (order_id, 1)

    # The citizen's report shows the cluster's verification state.
    async with phase2.sessions() as session:
        anchor = (await session.get(Cluster, PRIORITISED)).anchor_report_id
    report = await phase2.client.get(f"/api/v1/reports/{anchor}", headers=phase2.headers())
    assert report.status_code == 200, report.text
    assert report.json()["status"] == "awaiting_verification"

    # No more notes once submitted for verification.
    late = await phase2.client.patch(
        f"/api/v1/work-orders/{order_id}", json={"notes": "More"}, headers=officer
    )
    assert late.status_code == 409


async def test_completion_rules(phase2: Phase2) -> None:
    officer = phase2.headers(Role.OFFICER)
    path = f"/api/v1/work-orders/{SEEDED_ORDER}/complete"
    # At least one, at most three, distinct photos.
    for media in [[], [str(uuid4())] * 2, [str(uuid4()) for _ in range(4)]]:
        bad = await phase2.client.post(
            path,
            json={"media_ids": media, "expected_round": 1},
            headers={**officer, "Idempotency-Key": "x"},
        )
        assert bad.status_code == 422
    # Someone else's photo, or a citizen's report photo, cannot be used.
    citizen_photo = await completed_media(phase2, Role.CITIZEN)
    refused = await phase2.client.post(
        path,
        json={"media_ids": [citizen_photo], "expected_round": 1},
        headers={**officer, "Idempotency-Key": "c"},
    )
    assert refused.status_code == 422
    # Another officer cannot complete this order.
    other = await add_user(phase2, "other-officer", Role.OFFICER, department_id=CIVIC)
    photo = await completed_media(phase2, Role.OFFICER)
    foreign = await phase2.client.post(
        path,
        json={"media_ids": [photo], "expected_round": 1},
        headers={**other, "Idempotency-Key": "o"},
    )
    assert foreign.status_code == 404
    async with phase2.sessions() as session:
        assert (await session.get(Cluster, IN_PROGRESS)).status == "in_progress"


async def test_admin_cannot_strand_an_officers_open_work(phase2: Phase2) -> None:
    path = f"/api/v1/admin/users/{OFFICER}"
    admin = phase2.headers(Role.SUPER_ADMIN)
    async with phase2.sessions() as session:
        department = (await session.get(User, OFFICER)).department_id

    def change(**values: object) -> dict[str, object]:
        return {
            "role": "officer",
            "district_id": str(DISTRICT),
            "department_id": str(department),
            "institute_id": None,
            "organization_id": None,
            "reason": "Demo reassignment",
            **values,
        }

    # Demoting the officer or moving them out of the order's department would
    # leave nobody able to finish the seeded in-progress work.
    for body in [
        change(role="citizen", department_id=None),
        change(department_id=str(await other_department(phase2))),
    ]:
        refused = await phase2.client.patch(path, json=body, headers=admin)
        assert refused.status_code == 409, refused.text
    async with phase2.sessions() as session:
        officer = await session.get(User, OFFICER)
        assert (officer.role, officer.department_id) == ("officer", department)
    # A change that keeps the assignment valid is allowed.
    same = await phase2.client.patch(path, json=change(reason="Scope confirmed"), headers=admin)
    assert same.status_code == 200, same.text
    # Once the officer's work is verified, they can move.
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(Cluster)
            .where(
                Cluster.id.in_(select(WorkOrder.cluster_id).where(WorkOrder.officer_id == OFFICER))
            )
            .values(status="citizen_verified")
        )
    moved = await phase2.client.patch(
        path, json=change(role="citizen", department_id=None), headers=admin
    )
    assert moved.status_code == 200, moved.text


async def test_funding_and_a_concurrent_officer_change_never_both_succeed(
    phase2: Phase2,
) -> None:
    async with phase2.sessions() as session:
        department = (await session.get(User, OFFICER)).department_id
    await add_user(phase2, "race-officer", Role.OFFICER, department_id=department)
    async with phase2.sessions() as session:
        officer = await session.scalar(select(User.id).where(User.firebase_uid == "race-officer"))
    demote = {
        "role": "citizen",
        "district_id": str(DISTRICT),
        "department_id": None,
        "institute_id": None,
        "organization_id": None,
        "reason": "Demo reassignment",
    }
    funded, changed = await asyncio.gather(
        fund(phase2, "race-fund", officer_id=str(officer)),
        phase2.client.patch(
            f"/api/v1/admin/users/{officer}", json=demote, headers=phase2.headers(Role.SUPER_ADMIN)
        ),
    )
    # Either funding wins and the demotion is refused, or the demotion wins
    # and funding finds no assignable officer. Never a stranded work order.
    assert (funded.status_code, changed.status_code) in {(201, 409), (422, 200)}
    async with phase2.sessions() as session:
        role = await session.scalar(select(User.role).where(User.id == officer))
        orders = await session.scalar(
            select(func.count()).select_from(WorkOrder).where(WorkOrder.officer_id == officer)
        )
    assert (role, orders) in {("officer", 1), ("citizen", 0)}


async def test_completion_is_refused_before_work_starts(phase2: Phase2) -> None:
    order_id = (await fund(phase2, "fund-early")).json()["work_order_id"]
    photo = await completed_media(phase2, Role.OFFICER)
    early = await phase2.client.post(
        f"/api/v1/work-orders/{order_id}/complete",
        json={"media_ids": [photo], "expected_round": 1},
        headers={**phase2.headers(Role.OFFICER), "Idempotency-Key": "early"},
    )
    assert early.status_code == 409
    async with phase2.sessions() as session:
        assert (await session.get(MediaAsset, UUID(photo))).work_order_id is None


# ------------------------------------------------------------------ evidence


async def test_evidence_is_available_before_and_after_completion(phase2: Phase2) -> None:
    path = f"/api/v1/work-orders/{SEEDED_ORDER}/evidence"
    officer = phase2.headers(Role.OFFICER)
    before = await phase2.client.get(path, headers=officer)
    assert before.status_code == 200, before.text
    body = before.json()
    assert body["status"] == "in_progress" and body["after"] is None
    assert body["after_round"] is None and body["card_url"] is None

    photo = await completed_media(phase2, Role.OFFICER)
    await phase2.client.post(
        f"/api/v1/work-orders/{SEEDED_ORDER}/complete",
        json={"media_ids": [photo], "expected_round": 1},
        headers={**officer, "Idempotency-Key": "evidence"},
    )
    after = (await phase2.client.get(path, headers=officer)).json()
    assert after["status"] == "awaiting_verification"
    assert after["after_round"] == 1 and after["after"]["url"].startswith("https://")

    # The reporter, the department and district oversight may see it.
    for role in [Role.CITIZEN, Role.DEPARTMENT, Role.PANCHAYAT, Role.GOV_ADMIN, Role.SUPER_ADMIN]:
        assert (await phase2.client.get(path, headers=phase2.headers(role))).status_code == 200
    # Another citizen, another officer, and partner roles may not.
    stranger = await add_user(phase2, "stranger", Role.CITIZEN)
    other_officer = await add_user(phase2, "other-officer-2", Role.OFFICER, department_id=CIVIC)
    for headers in [stranger, other_officer, phase2.headers(Role.STUDENT)]:
        assert (await phase2.client.get(path, headers=headers)).status_code == 404


# ---------------------------------------------------------------- statements


async def test_partners_read_published_statements_only(phase2: Phase2) -> None:
    draft = await phase2.client.post(
        "/api/v1/statements",
        json={"title": "Draft idea", "body": "Not public yet."},
        headers={**phase2.headers(Role.DEPARTMENT), "Idempotency-Key": "draft"},
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["status"] == "draft"

    for role in [Role.STUDENT, Role.FACULTY, Role.INSTITUTE, Role.INDUSTRY, Role.GOV_ADMIN]:
        listed = await phase2.client.get("/api/v1/statements", headers=phase2.headers(role))
        assert listed.status_code == 200, (role, listed.text)
        assert all(item["status"] == "published" for item in listed.json()["items"])
        assert draft.json()["id"] not in {item["id"] for item in listed.json()["items"]}
    own = await phase2.client.get("/api/v1/statements", headers=phase2.headers(Role.DEPARTMENT))
    assert draft.json()["id"] in {item["id"] for item in own.json()["items"]}
    for role in [Role.CITIZEN, Role.PANCHAYAT, Role.OFFICER]:
        assert (
            await phase2.client.get("/api/v1/statements", headers=phase2.headers(role))
        ).status_code == 403


async def test_another_departments_drafts_stay_hidden(phase2: Phase2) -> None:
    await phase2.client.post(
        "/api/v1/statements",
        json={"title": "Civic draft", "body": "Internal."},
        headers={**phase2.headers(Role.DEPARTMENT), "Idempotency-Key": "civic-draft"},
    )
    elsewhere = await other_department(phase2)
    roads = await add_user(phase2, "roads-dept-3", Role.DEPARTMENT, department_id=elsewhere)
    listed = await phase2.client.get("/api/v1/statements", headers=roads)
    assert listed.status_code == 200
    assert all(item["status"] == "published" for item in listed.json()["items"])


async def test_publish_and_link_rules(phase2: Phase2) -> None:
    department = phase2.headers(Role.DEPARTMENT)
    created = await phase2.client.post(
        "/api/v1/statements",
        json={
            "title": "Pump alerts",
            "body": "Early fault alerts.",
            "cluster_id": str(PRIORITISED),
        },
        headers={**department, "Idempotency-Key": "linked"},
    )
    assert created.status_code == 201, created.text
    statement_id = created.json()["id"]
    published = await phase2.client.post(
        f"/api/v1/statements/{statement_id}/publish", headers=department
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published" and published.json()["published_at"]
    again = await phase2.client.post(
        f"/api/v1/statements/{statement_id}/publish", headers=department
    )
    assert again.json() == published.json()

    # Partners cannot create or publish; unknown clusters cannot be linked.
    for role in [Role.STUDENT, Role.INDUSTRY, Role.GOV_ADMIN]:
        assert (
            await phase2.client.post(
                "/api/v1/statements",
                json={"title": "x", "body": "y"},
                headers={**phase2.headers(role), "Idempotency-Key": f"p-{role}"},
            )
        ).status_code == 403
    unknown = await phase2.client.post(
        "/api/v1/statements",
        json={"title": "x", "body": "y", "cluster_id": str(uuid4())},
        headers={**department, "Idempotency-Key": "unknown-cluster"},
    )
    assert unknown.status_code == 422
    async with phase2.sessions() as session:
        published_count = await session.scalar(
            select(func.count())
            .select_from(ProblemStatement)
            .where(ProblemStatement.status == "published")
        )
    assert published_count == 2  # the seeded statement and this one
