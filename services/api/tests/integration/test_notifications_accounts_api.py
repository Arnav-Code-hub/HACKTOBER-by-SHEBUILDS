"""Case-update notifications, account activation and transparency analytics."""

import pytest
from sqlalchemy import select

from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.seeds.data import user_id
from tests.integration.conftest import Phase2
from tests.integration.test_phase2_api import report_body
from tests.integration.test_phase4_api import add_user, fund
from tests.integration.test_phase5_api import completion, ready, verdict

pytestmark = pytest.mark.integration


async def inbox(phase2: Phase2, headers: dict[str, str]):
    response = await phase2.client.get("/api/v1/notifications", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def titles(page) -> list[str]:
    return [item["title"] for item in page["items"]]


# ------------------------------------------------------------ notifications


async def test_every_round_of_a_repair_notifies_the_citizen(phase2: Phase2) -> None:
    citizen = phase2.headers(Role.CITIZEN)
    await ready(phase2)
    assert titles(await inbox(phase2, citizen)).count("Repair work is ready for review") == 1

    assert (await verdict(phase2, False, key="notify-return")).status_code == 200
    page = await inbox(phase2, citizen)
    assert "Repair needs another attempt" in titles(page)

    # A correction round is a new event, not a duplicate of round 1.
    await completion(phase2, key="notify-round-two", round_=2)
    page = await inbox(phase2, citizen)
    assert titles(page).count("Repair work is ready for review") == 2

    assert (await verdict(phase2, True, round_=2, key="notify-confirm")).status_code == 200
    assert "Repair confirmed by a citizen" in titles(await inbox(phase2, citizen))


async def test_funding_notifies_the_reporters(phase2: Phase2) -> None:
    assert (await fund(phase2, "notify-fund")).status_code == 201
    assert "A community case was funded" in titles(
        await inbox(phase2, phase2.headers(Role.CITIZEN))
    )


async def test_an_inbox_is_private_and_marking_read_is_owner_only(phase2: Phase2) -> None:
    citizen = phase2.headers(Role.CITIZEN)
    await ready(phase2)
    page = await inbox(phase2, citizen)
    assert page["unread_count"] >= 1
    first = page["items"][0]["id"]

    stranger = await add_user(phase2, "notify-stranger", Role.CITIZEN)
    assert (await inbox(phase2, stranger))["items"] == []
    refused = await phase2.client.post(f"/api/v1/notifications/{first}/read", headers=stranger)
    assert refused.status_code == 404

    marked = await phase2.client.post(f"/api/v1/notifications/{first}/read", headers=citizen)
    assert marked.status_code == 200 and marked.json()["read_at"]
    again = await phase2.client.post(f"/api/v1/notifications/{first}/read", headers=citizen)
    assert again.json()["read_at"] == marked.json()["read_at"]
    assert (await inbox(phase2, citizen))["unread_count"] == page["unread_count"] - 1


# -------------------------------------------------------- account activation


def status_change(active: bool, reason: str = "Account review") -> dict[str, object]:
    return {"is_active": active, "reason": reason}


async def test_super_admin_deactivates_and_reactivates_an_account(phase2: Phase2) -> None:
    admin = phase2.headers(Role.SUPER_ADMIN)
    path = f"/api/v1/admin/users/{user_id(Role.STUDENT)}/status"
    off = await phase2.client.patch(path, json=status_change(False), headers=admin)
    assert off.status_code == 200, off.text
    assert off.json()["is_active"] is False
    # A deactivated account is refused on its next request.
    me = await phase2.client.get("/api/v1/users/me", headers=phase2.headers(Role.STUDENT))
    assert me.status_code == 403

    on = await phase2.client.patch(path, json=status_change(True), headers=admin)
    assert on.status_code == 200 and on.json()["is_active"] is True
    async with phase2.sessions() as session:
        actions = (
            await session.scalars(
                select(AuditEventRecord.action).where(
                    AuditEventRecord.entity_id == user_id(Role.STUDENT)
                )
            )
        ).all()
    assert {"user.deactivated", "user.activated"} <= set(actions)


async def test_activation_safeguards(phase2: Phase2) -> None:
    admin = phase2.headers(Role.SUPER_ADMIN)
    own = await phase2.client.patch(
        f"/api/v1/admin/users/{user_id(Role.SUPER_ADMIN)}/status",
        json=status_change(False),
        headers=admin,
    )
    assert own.status_code == 403
    # The seeded officer has open work; deactivating would strand it.
    officer = await phase2.client.patch(
        f"/api/v1/admin/users/{user_id(Role.OFFICER)}/status",
        json=status_change(False),
        headers=admin,
    )
    assert officer.status_code == 409
    no_reason = await phase2.client.patch(
        f"/api/v1/admin/users/{user_id(Role.STUDENT)}/status",
        json={"is_active": False, "reason": " "},
        headers=admin,
    )
    assert no_reason.status_code == 422
    gov = await phase2.client.patch(
        f"/api/v1/admin/users/{user_id(Role.STUDENT)}/status",
        json=status_change(False),
        headers=phase2.headers(Role.GOV_ADMIN),
    )
    assert gov.status_code == 403


# ------------------------------------------------------------------ analytics


async def test_public_totals_show_sample_data_until_a_live_report_exists(phase2: Phase2) -> None:
    before = await phase2.client.get("/api/v1/analytics/public")
    assert before.status_code == 200, before.text
    body = before.json()
    # Only the seeded demonstration data exists: shown, and labelled as sample.
    assert body["sample_data"] is True and body["report_count"] > 0
    resident = await add_user(phase2, "analytics-resident", Role.CITIZEN)
    created = await phase2.client.post(
        "/api/v1/reports",
        json=report_body(),
        headers={**resident, "Idempotency-Key": "analytics-live-report"},
    )
    assert created.status_code == 201, created.text
    after = (await phase2.client.get("/api/v1/analytics/public")).json()
    # A live report exists: only live records are counted, never mixed.
    assert after["sample_data"] is False and after["report_count"] == 1
    # Aggregates only: no reporter, title or coordinates are published.
    text = str(after)
    assert "Handpump repair" not in text and "16.76" not in text


@pytest.mark.parametrize(
    ("role", "status"),
    [(Role.DEPARTMENT, 200), (Role.GOV_ADMIN, 200), (Role.OFFICER, 403), (Role.CITIZEN, 403)],
)
async def test_workload_is_for_departments_and_administrators(
    phase2: Phase2, role: Role, status: int
) -> None:
    response = await phase2.client.get("/api/v1/analytics/workload", headers=phase2.headers(role))
    assert response.status_code == status, response.text
