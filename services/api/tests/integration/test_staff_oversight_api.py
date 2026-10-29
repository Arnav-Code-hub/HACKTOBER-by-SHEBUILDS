"""Case tracker, correction brief, audit paging and organization districts."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.modules.departments.models import Organization
from app.seeds.data import user_id
from tests.integration.conftest import Phase2
from tests.integration.test_phase4_api import (
    CIVIC,
    DISTRICT,
    IN_PROGRESS,
    PRIORITISED,
    SEEDED_ORDER,
    add_user,
    fund,
    other_department,
)
from tests.integration.test_phase5_api import ready, verdict

pytestmark = pytest.mark.integration


async def cases(phase2: Phase2, headers: dict[str, str]):
    response = await phase2.client.get("/api/v1/cases", headers=headers)
    assert response.status_code == 200, response.text
    return {item["cluster_id"]: item for item in response.json()["items"]}


# ------------------------------------------------------------- case tracker


async def test_department_tracks_what_it_must_fund_and_what_it_funded(
    phase2: Phase2,
) -> None:
    department = phase2.headers(Role.DEPARTMENT)
    before = await cases(phase2, department)
    assert before[str(PRIORITISED)]["waiting_on"] == "department"
    assert before[str(PRIORITISED)]["work_order_id"] is None
    assert before[str(IN_PROGRESS)]["waiting_on"] == "officer"

    funded = await fund(phase2, "tracker-fund")
    assert funded.status_code == 201, funded.text
    item = (await cases(phase2, department))[str(PRIORITISED)]
    assert item["status"] == "funded" and item["waiting_on"] == "officer"
    assert item["work_order_id"] == funded.json()["work_order_id"]
    assert item["round"] == 1
    # The allocation receipt: what was recorded, by whom, for which officer.
    assert item["allocated_paise"] == 15_000_000
    assert item["allocated_at"] and item["allocated_by_name"]
    assert item["officer_name"] and item["department_name"]


async def test_another_department_sees_none_of_these_cases(phase2: Phase2) -> None:
    other = await add_user(
        phase2, "tracker-other-dept", Role.DEPARTMENT, department_id=await other_department(phase2)
    )
    assert await cases(phase2, other) == {}


async def test_gov_admin_sees_the_district_and_other_districts_see_nothing(
    phase2: Phase2,
) -> None:
    district = await cases(phase2, phase2.headers(Role.GOV_ADMIN))
    assert {str(PRIORITISED), str(IN_PROGRESS)} <= set(district)
    other_district = uuid4()
    async with phase2.sessions.begin() as session:
        session.add(
            Organization(
                id=other_district,
                type="district",
                name="Another district",
                code=f"DIST-{other_district.hex[:6]}",
                is_active=True,
            )
        )
    elsewhere = await add_user(
        phase2, "tracker-elsewhere", Role.GOV_ADMIN, district_id=other_district
    )
    assert await cases(phase2, elsewhere) == {}
    assert set(await cases(phase2, phase2.headers(Role.SUPER_ADMIN))) >= set(district)


@pytest.mark.parametrize("role", [Role.CITIZEN, Role.OFFICER, Role.PANCHAYAT, Role.STUDENT])
async def test_other_roles_cannot_track_cases(phase2: Phase2, role: Role) -> None:
    response = await phase2.client.get("/api/v1/cases", headers=phase2.headers(role))
    assert response.status_code == 403


async def test_waiting_on_follows_the_case_to_the_citizen(phase2: Phase2) -> None:
    await ready(phase2)
    item = (await cases(phase2, phase2.headers(Role.GOV_ADMIN)))[str(IN_PROGRESS)]
    assert item["status"] == "awaiting_verification" and item["waiting_on"] == "citizen"
    assert (await verdict(phase2, True, key="tracker-confirm")).status_code == 200
    item = (await cases(phase2, phase2.headers(Role.GOV_ADMIN)))[str(IN_PROGRESS)]
    assert item["status"] == "citizen_verified" and item["waiting_on"] == "none"


# --------------------------------------------------------- correction brief


async def test_evidence_carries_the_citizens_reason_for_a_returned_round(
    phase2: Phase2,
) -> None:
    path = f"/api/v1/work-orders/{SEEDED_ORDER}/evidence"
    await ready(phase2)
    waiting = (await phase2.client.get(path, headers=phase2.headers(Role.OFFICER))).json()
    assert waiting["returned_comment"] is None

    returned = await verdict(
        phase2, False, key="tracker-return", comment="Still no water in the evening."
    )
    assert returned.status_code == 200, returned.text
    for role in [Role.OFFICER, Role.DEPARTMENT, Role.GOV_ADMIN]:
        body = (await phase2.client.get(path, headers=phase2.headers(role))).json()
        assert body["after_round"] == 1
        assert body["returned_comment"] == "Still no water in the evening."


async def test_a_return_without_a_comment_has_no_reason(phase2: Phase2) -> None:
    await ready(phase2)
    assert (await verdict(phase2, False, key="tracker-silent")).status_code == 200
    body = (
        await phase2.client.get(
            f"/api/v1/work-orders/{SEEDED_ORDER}/evidence", headers=phase2.headers(Role.OFFICER)
        )
    ).json()
    assert body["after_round"] == 1 and body["returned_comment"] is None


# ------------------------------------------------------------- audit paging


async def add_events(phase2: Phase2, count: int) -> list[str]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    ids = []
    async with phase2.sessions.begin() as session:
        for index in range(count):
            event = AuditEventRecord(
                id=uuid4(),
                actor_id=user_id(Role.SUPER_ADMIN),
                actor_role="super_admin",
                action="user.scope_changed",
                entity_type="user",
                entity_id=user_id(Role.STUDENT),
                district_id=DISTRICT,
                before={"role": "student", "email": "private@example.test"},
                after={"role": "faculty", "email": "private@example.test"},
                reason=f"Paging test {index}",
                created_at=start + timedelta(minutes=index),
            )
            session.add(event)
            ids.append(str(event.id))
    return ids


async def test_audit_pages_back_without_gaps_or_repeats(phase2: Phase2) -> None:
    added = await add_events(phase2, 5)
    admin = phase2.headers(Role.GOV_ADMIN)
    seen: list[str] = []
    query: dict[str, str | int] = {"limit": 2}
    for _ in range(50):
        response = await phase2.client.get("/api/v1/admin/audit", params=query, headers=admin)
        assert response.status_code == 200, response.text
        body = response.json()
        seen.extend(item["id"] for item in body["items"])
        if body["next"] is None:
            break
        query = {"limit": 2, **body["next"]}
    assert len(seen) == len(set(seen)), "a page repeated an event"
    assert set(added) <= set(seen), "an older event was unreachable"
    # Contact details never leave the audit store.
    page = (
        await phase2.client.get("/api/v1/admin/audit", params={"limit": 200}, headers=admin)
    ).json()
    mine = [item for item in page["items"] if item["id"] in added]
    assert mine and all(item["before"] == {"role": "student"} for item in mine)
    assert all(item["after"] == {"role": "faculty"} for item in mine)


async def test_audit_cursor_needs_both_parts(phase2: Phase2) -> None:
    response = await phase2.client.get(
        "/api/v1/admin/audit",
        params={"before_at": "2026-01-01T00:00:00Z"},
        headers=phase2.headers(Role.GOV_ADMIN),
    )
    assert response.status_code == 422


# ------------------------------------------------------ organization district


async def test_organizations_name_their_district(phase2: Phase2) -> None:
    response = await phase2.client.get(
        "/api/v1/organizations", headers=phase2.headers(Role.SUPER_ADMIN)
    )
    assert response.status_code == 200, response.text
    items = {item["id"]: item for item in response.json()["items"]}
    assert items[str(CIVIC)]["parent_id"] == str(DISTRICT)
    assert items[str(DISTRICT)]["parent_id"] is None
