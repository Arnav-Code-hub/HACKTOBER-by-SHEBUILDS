import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.modules.departments.models import Organization
from app.modules.problems.models import Cluster, Report, Support
from app.modules.users.models import User
from app.seeds.data import seed_id, user_id
from tests.integration.conftest import Phase2
from tests.integration.helpers import new_report
from tests.integration.test_phase2_api import report_body

pytestmark = pytest.mark.integration
REPORTED = seed_id("report/reported")
PRIORITISED = seed_id("cluster/prioritised")
DISTRICT = seed_id("district/yadgir")


async def validate(phase2: Phase2, report_id=REPORTED):
    response = await phase2.client.post(
        f"/api/v1/reports/{report_id}/validate",
        json={"decision": "verify"},
        headers=phase2.headers(Role.PANCHAYAT),
    )
    assert response.status_code == 200, response.text
    return response


async def ranking(phase2: Phase2, role=Role.PANCHAYAT):
    response = await phase2.client.get("/api/v1/clusters/ranked", headers=phase2.headers(role))
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def test_panchayat_queue_to_cluster_and_citizen_read_share_effective_status(
    phase2: Phase2,
) -> None:
    queue = await phase2.client.get(
        "/api/v1/reports?status=reported", headers=phase2.headers(Role.PANCHAYAT)
    )
    assert [item["id"] for item in queue.json()["items"]] == [str(REPORTED)]
    await validate(phase2)
    queue = await phase2.client.get(
        "/api/v1/reports?status=verified", headers=phase2.headers(Role.PANCHAYAT)
    )
    assert [item["id"] for item in queue.json()["items"]] == [str(REPORTED)]
    response = await phase2.client.post(
        f"/api/v1/reports/{REPORTED}/cluster",
        json={"new": True},
        headers=phase2.headers(Role.PANCHAYAT),
    )
    assert response.status_code == 200 and response.json()["status"] == "prioritised"
    detail = await phase2.client.get(f"/api/v1/reports/{REPORTED}", headers=phase2.headers())
    saved = detail.json()
    assert saved["status"] == "prioritised" and saved["status_changed_at"]
    assert saved["rank"] >= 1 and saved["total_ranked"] == 3
    assert saved["supporter_count"] == 1 and len(saved["score_breakdown"]) == 5
    queue = await phase2.client.get(
        "/api/v1/reports?status=verified", headers=phase2.headers(Role.PANCHAYAT)
    )
    assert queue.json() == {"items": []}
    async with phase2.sessions() as session:
        report = await session.get(Report, REPORTED)
        assert report.status == "verified"  # execution status is only on the cluster
        events = (
            await session.scalars(
                select(AuditEventRecord)
                .where(
                    AuditEventRecord.entity_id == REPORTED,
                    AuditEventRecord.action == "report.status_changed",
                )
                .order_by(AuditEventRecord.created_at)
            )
        ).all()
        assert len(events) == 2
        assert all(event.district_id == DISTRICT for event in events)
        assert events[-1].after["cluster_id"] == str(report.cluster_id)


async def test_rejection_is_saved_with_reason_and_cannot_be_validated_twice(phase2: Phase2) -> None:
    endpoint = f"/api/v1/reports/{REPORTED}/validate"
    headers = phase2.headers(Role.PANCHAYAT)
    assert (
        await phase2.client.post(endpoint, json={"decision": "reject"}, headers=headers)
    ).status_code == 422
    response = await phase2.client.post(
        endpoint,
        json={"decision": "reject", "reason": "Duplicate location information"},
        headers=headers,
    )
    assert response.status_code == 200 and response.json()["status"] == "rejected"
    detail = await phase2.client.get(f"/api/v1/reports/{REPORTED}", headers=phase2.headers())
    assert detail.json()["rejection_reason"] == "Duplicate location information"
    assert (
        await phase2.client.post(endpoint, json={"decision": "verify"}, headers=headers)
    ).status_code == 409


async def test_competing_validations_record_one_transition(phase2: Phase2) -> None:
    responses = await asyncio.gather(
        *[
            phase2.client.post(
                f"/api/v1/reports/{REPORTED}/validate",
                json=body,
                headers=phase2.headers(Role.PANCHAYAT),
            )
            for body in [{"decision": "verify"}, {"decision": "reject", "reason": "Not actionable"}]
        ]
    )
    assert sorted(response.status_code for response in responses) == [200, 409]
    async with phase2.sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEventRecord)
                .where(
                    AuditEventRecord.entity_id == REPORTED,
                    AuditEventRecord.action == "report.status_changed",
                )
            )
            == 1
        )


@pytest.mark.parametrize("same_target", [True, False])
async def test_competing_cluster_assignments_cannot_duplicate_membership(
    phase2: Phase2, same_target: bool
) -> None:
    await validate(phase2)
    bodies = [
        {"cluster_id": str(PRIORITISED)},
        {"cluster_id": str(PRIORITISED)} if same_target else {"new": True},
    ]
    responses = await asyncio.gather(
        *[
            phase2.client.post(
                f"/api/v1/reports/{REPORTED}/cluster",
                json=body,
                headers=phase2.headers(Role.PANCHAYAT),
            )
            for body in bodies
        ]
    )
    assert sorted(response.status_code for response in responses) == [200, 409]
    async with phase2.sessions() as session:
        assert (await session.get(Report, REPORTED)).cluster_id is not None
        count = await session.scalar(select(func.count()).select_from(Cluster))
        assert count in ({2} if same_target else {2, 3})


async def test_suggestions_and_assignment_use_same_anchor_radius_category_and_status(
    phase2: Phase2,
) -> None:
    await validate(phase2)
    path = f"/api/v1/reports/{REPORTED}"
    headers = phase2.headers(Role.PANCHAYAT)
    response = await phase2.client.get(path + "/cluster-suggestions", headers=headers)
    assert len(response.json()["items"]) == 2
    assert all(item["distance_m"] == 0 for item in response.json()["items"])
    async with phase2.sessions.begin() as session:
        await session.execute(update(Report).where(Report.id == REPORTED).values(latitude=16.77))
    assert (await phase2.client.get(path + "/cluster-suggestions", headers=headers)).json() == {
        "items": []
    }
    response = await phase2.client.post(
        path + "/cluster", json={"cluster_id": str(PRIORITISED)}, headers=headers
    )
    assert response.status_code == 422
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(Report).where(Report.id == REPORTED).values(latitude=16.76, category="roads")
        )
    assert (await phase2.client.get(path + "/cluster-suggestions", headers=headers)).json() == {
        "items": []
    }
    assert (
        await phase2.client.post(
            path + "/cluster", json={"cluster_id": str(PRIORITISED)}, headers=headers
        )
    ).status_code == 404
    async with phase2.sessions.begin() as session:
        await session.execute(update(Report).where(Report.id == REPORTED).values(category="water"))
        await session.execute(update(Cluster).values(status="awaiting_verification"))
    assert (await phase2.client.get(path + "/cluster-suggestions", headers=headers)).json() == {
        "items": []
    }
    assert (
        await phase2.client.post(
            path + "/cluster", json={"cluster_id": str(PRIORITISED)}, headers=headers
        )
    ).status_code == 409


@pytest.mark.parametrize(
    ("category", "expected"), [("water", 422), ("roads", 200), ("sanitation", 200)]
)
async def test_linear_category_radius_is_500m_and_point_radius_is_100m(
    phase2: Phase2, category: str, expected: int
) -> None:
    await validate(phase2)
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(Report).where(Report.id == REPORTED).values(category=category, latitude=16.763)
        )
        await session.execute(
            update(Report)
            .where(Report.id == seed_id("report/prioritised"))
            .values(category=category)
        )
        await session.execute(
            update(Cluster).where(Cluster.id == PRIORITISED).values(category=category)
        )
    response = await phase2.client.post(
        f"/api/v1/reports/{REPORTED}/cluster",
        json={"cluster_id": str(PRIORITISED)},
        headers=phase2.headers(Role.PANCHAYAT),
    )
    assert response.status_code == expected, response.text


async def test_support_counts_unique_reporters_and_supporters_under_concurrency(
    phase2: Phase2,
) -> None:
    # Existing reporter also has an explicit seeded support; that still counts once.
    assert (
        next(item for item in await ranking(phase2) if item["id"] == str(PRIORITISED))[
            "supporter_count"
        ]
        == 1
    )
    async with phase2.sessions.begin() as session:
        session.add(
            User(
                id=uuid4(),
                firebase_uid="supporter",
                role="citizen",
                district_id=DISTRICT,
                display_name="Supporter",
                email="supporter@example.test",
                is_active=True,
            )
        )
    headers = {"Authorization": "Bearer valid:supporter"}
    responses = await asyncio.gather(
        *[
            phase2.client.post(f"/api/v1/clusters/{PRIORITISED}/support", headers=headers)
            for _ in range(4)
        ]
    )
    assert all(response.status_code == 200 for response in responses)
    assert all(response.json()["supporter_count"] == 2 for response in responses)
    await validate(phase2)
    await phase2.client.post(
        f"/api/v1/reports/{REPORTED}/cluster",
        json={"cluster_id": str(PRIORITISED)},
        headers=phase2.headers(Role.PANCHAYAT),
    )
    # A second report from the original citizen does not add a third supporter.
    item = next(item for item in await ranking(phase2) if item["id"] == str(PRIORITISED))
    assert item["report_count"] == 2 and item["supporter_count"] == 2
    async with phase2.sessions() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(Support).where(Support.cluster_id == PRIORITISED)
            )
            == 2
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEventRecord)
                .where(AuditEventRecord.action == "cluster.supported")
            )
            == 1
        )


async def test_ranking_uses_highest_validated_member_severity_and_honest_defaults(
    phase2: Phase2,
) -> None:
    async with phase2.sessions.begin() as session:
        report = new_report("Critical member")
        report.status = "verified"
        report.severity = "critical"
        report.cluster_id = PRIORITISED
        session.add(report)
    item = next(item for item in await ranking(phase2) if item["id"] == str(PRIORITISED))
    factors = {factor["factor"]: factor for factor in item["score_breakdown"]}
    assert item["inputs_are_demo"] and item["infrastructure_gap"] == item["equity_index"] == 50
    assert factors["severity"]["score"] == 100 and factors["gap"]["is_demo"]
    assert item["priority_score"] == pytest.approx(
        sum(factor["score"] * factor["weight"] for factor in factors.values())
    )


async def test_ties_use_older_anchor_then_cluster_uuid(phase2: Phase2) -> None:
    # All anchors are over 90 days old so age scores saturate and totals tie.
    async with phase2.sessions.begin() as session:
        await session.execute(
            update(Report).values(created_at=datetime.now(UTC) - timedelta(days=100))
        )
        earlier = seed_id("report/in_progress")
        await session.execute(
            update(Report)
            .where(Report.id == earlier)
            .values(created_at=datetime.now(UTC) - timedelta(days=120))
        )
    rows = await ranking(phase2)
    assert rows[0]["id"] == str(seed_id("cluster/in_progress"))
    async with phase2.sessions.begin() as session:
        await session.execute(update(Report).values(created_at=datetime(2026, 1, 1, tzinfo=UTC)))
    rows = await ranking(phase2)
    assert [item["id"] for item in rows] == sorted(
        [str(PRIORITISED), str(seed_id("cluster/in_progress"))]
    )


async def test_official_inputs_are_scoped_audited_and_change_ranking(phase2: Phase2) -> None:
    path = f"/api/v1/clusters/{PRIORITISED}/inputs"
    body = {"infrastructure_gap": 99, "equity_index": 100}
    for role in [Role.CITIZEN, Role.PANCHAYAT, Role.OFFICER, Role.STUDENT]:
        assert (
            await phase2.client.patch(path, json=body, headers=phase2.headers(role))
        ).status_code == 403
    response = await phase2.client.patch(path, json=body, headers=phase2.headers(Role.DEPARTMENT))
    assert response.status_code == 200, response.text
    item = (await ranking(phase2))[0]
    assert item["id"] == str(PRIORITISED) and not item["inputs_are_demo"]
    assert all(
        not factor["is_demo"]
        for factor in item["score_breakdown"]
        if factor["factor"] in {"gap", "equity"}
    )
    async with phase2.sessions() as session:
        event = (
            await session.scalars(
                select(AuditEventRecord).where(AuditEventRecord.action == "cluster.inputs_updated")
            )
        ).one()
        assert event.before["infrastructure_gap"] is None and event.after == {
            **body,
            "inputs_are_demo": False,
        }
        assert event.district_id == DISTRICT
    assert (
        await phase2.client.patch(
            path, json={**body, "equity_index": True}, headers=phase2.headers(Role.GOV_ADMIN)
        )
    ).status_code == 422
    assert (
        await phase2.client.patch(path, json=body, headers=phase2.headers(Role.GOV_ADMIN))
    ).status_code == 200


async def test_district_and_department_boundaries_hide_reports_and_clusters(phase2: Phase2) -> None:
    other_district, other_department = uuid4(), uuid4()
    async with phase2.sessions.begin() as session:
        session.add(
            Organization(
                id=other_district,
                type="district",
                name="Other district",
                code="OTHER",
                is_active=True,
            )
        )
        await session.flush()
        session.add(
            Organization(
                id=other_department,
                type="department",
                parent_id=other_district,
                name="Other department",
                code="OTHER-DEPT",
                is_active=True,
            )
        )
        await session.flush()
        session.add(
            User(
                id=uuid4(),
                firebase_uid="other-panchayat",
                role="panchayat",
                district_id=other_district,
                display_name="Other Panchayat",
                email="other-panchayat@example.test",
                is_active=True,
            )
        )
        report = new_report("Outside district")
        report.district_id = other_district
        report.status = "verified"
        session.add(report)
        await session.flush()
        cluster = Cluster(district_id=other_district, category="water", anchor_report_id=report.id)
        session.add(cluster)
        await session.flush()
        report.cluster_id = cluster.id
        foreign_report, foreign_cluster = report.id, cluster.id
    other = {"Authorization": "Bearer valid:other-panchayat"}
    assert (
        await phase2.client.get(f"/api/v1/reports/{REPORTED}", headers=other)
    ).status_code == 404
    assert (
        await phase2.client.post(
            f"/api/v1/reports/{REPORTED}/validate", json={"decision": "verify"}, headers=other
        )
    ).status_code == 404
    assert (
        await phase2.client.get(f"/api/v1/reports/{REPORTED}/cluster-suggestions", headers=other)
    ).status_code == 404
    assert (
        len(
            (await phase2.client.get("/api/v1/reports?status=reported", headers=other)).json()[
                "items"
            ]
        )
        == 0
    )
    assert len(await ranking(phase2)) == 2
    assert len(await ranking(phase2, Role.SUPER_ADMIN)) == 3
    assert (
        await phase2.client.get(
            f"/api/v1/reports/{foreign_report}", headers=phase2.headers(Role.PANCHAYAT)
        )
    ).status_code == 404
    assert (
        await phase2.client.post(
            f"/api/v1/clusters/{foreign_cluster}/support", headers=phase2.headers()
        )
    ).status_code == 404
    assert (
        await phase2.client.patch(
            f"/api/v1/clusters/{foreign_cluster}/inputs",
            json={"infrastructure_gap": 5, "equity_index": 5},
            headers=phase2.headers(Role.GOV_ADMIN),
        )
    ).status_code == 404
    # Same district, different department: no category responsibility means no visibility.
    async with phase2.sessions.begin() as session:
        dept = Organization(
            type="department", name="Unassigned department", code="UNASSIGNED", parent_id=DISTRICT
        )
        session.add(dept)
        await session.flush()
        await session.execute(
            update(User).where(User.id == user_id(Role.DEPARTMENT)).values(department_id=dept.id)
        )
    assert await ranking(phase2, Role.DEPARTMENT) == []
    assert (
        await phase2.client.get(
            f"/api/v1/reports/{REPORTED}", headers=phase2.headers(Role.DEPARTMENT)
        )
    ).status_code == 404
    assert (
        await phase2.client.patch(
            f"/api/v1/clusters/{PRIORITISED}/inputs",
            json={"infrastructure_gap": 5, "equity_index": 5},
            headers=phase2.headers(Role.DEPARTMENT),
        )
    ).status_code == 404


async def test_only_panchayat_validates_and_only_citizens_support(phase2: Phase2) -> None:
    for role in Role:
        if role != Role.PANCHAYAT:
            assert (
                await phase2.client.post(
                    f"/api/v1/reports/{REPORTED}/validate",
                    json={"decision": "verify"},
                    headers=phase2.headers(role),
                )
            ).status_code == 403
            assert (
                await phase2.client.post(
                    f"/api/v1/reports/{REPORTED}/cluster",
                    json={"new": True},
                    headers=phase2.headers(role),
                )
            ).status_code == 403
        if role != Role.CITIZEN:
            assert (
                await phase2.client.post(
                    f"/api/v1/clusters/{PRIORITISED}/support", headers=phase2.headers(role)
                )
            ).status_code == 403
    assert (
        await phase2.client.get(
            "/api/v1/reports?status=bogus", headers=phase2.headers(Role.PANCHAYAT)
        )
    ).status_code == 422
    # Creating a citizen report still works independently of validation and ranking.
    assert (
        await phase2.client.post(
            "/api/v1/reports",
            json=report_body(),
            headers=phase2.headers(**{"Idempotency-Key": "phase3-create"}),
        )
    ).status_code == 201
