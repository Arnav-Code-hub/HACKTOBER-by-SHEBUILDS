import asyncio
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select

from app.core.roles import Role
from app.modules.audit.models import AuditEventRecord
from app.modules.problems.models import Report
from app.modules.users.models import User
from app.persistence.audit import SqlAuditWriter
from app.seeds.data import seed_id
from tests.integration.conftest import Phase2
from tests.integration.helpers import new_report

pytestmark = pytest.mark.integration


async def test_simultaneous_membership_and_support_preserve_unique_citizens(phase2: Phase2) -> None:
    cluster_id = seed_id("cluster/prioritised")
    report_ids = []
    async with phase2.sessions.begin() as session:
        for index in range(2):
            user = User(
                id=uuid4(),
                firebase_uid=f"member-{index}",
                role="citizen",
                display_name=f"Member {index}",
                email=f"member-{index}@example.test",
                district_id=seed_id("district/yadgir"),
                is_active=True,
            )
            session.add(user)
            await session.flush()
            report = new_report(f"Member report {index}")
            report.reporter_id = user.id
            report.status = "verified"
            session.add(report)
            await session.flush()
            report_ids.append(report.id)
    responses = await asyncio.gather(
        *[
            phase2.client.post(
                f"/api/v1/reports/{report_id}/cluster",
                json={"cluster_id": str(cluster_id)},
                headers=phase2.headers(Role.PANCHAYAT),
            )
            for report_id in report_ids
        ],
        *[
            phase2.client.post(
                f"/api/v1/clusters/{cluster_id}/support",
                headers={"Authorization": f"Bearer valid:member-{index}"},
            )
            for index in range(2)
        ],
    )
    assert all(response.status_code == 200 for response in responses)
    result = await phase2.client.get("/api/v1/clusters/ranked", headers=phase2.headers())
    item = next(item for item in result.json()["items"] if item["id"] == str(cluster_id))
    assert item["report_count"] == item["supporter_count"] == 3
    async with phase2.sessions() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(Report).where(Report.cluster_id == cluster_id)
            )
            == 3
        )


async def test_audit_failure_rolls_back_validation_inputs_and_support(
    phase2: Phase2, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail(*args, **kwargs):
        raise RuntimeError("Simulated audit write failure")

    monkeypatch.setattr(SqlAuditWriter, "log_event", fail)
    cluster_id = seed_id("cluster/prioritised")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=phase2.app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/reports/{seed_id('report/reported')}/validate",
            json={"decision": "verify"},
            headers=phase2.headers(Role.PANCHAYAT),
        )
        assert response.status_code == 500
        response = await client.patch(
            f"/api/v1/clusters/{cluster_id}/inputs",
            json={"infrastructure_gap": 99, "equity_index": 99},
            headers=phase2.headers(Role.DEPARTMENT),
        )
        assert response.status_code == 500
        async with phase2.sessions.begin() as session:
            session.add(
                User(
                    id=uuid4(),
                    firebase_uid="rollback-supporter",
                    role="citizen",
                    display_name="Supporter",
                    email="rollback@example.test",
                    district_id=seed_id("district/yadgir"),
                    is_active=True,
                )
            )
        response = await client.post(
            f"/api/v1/clusters/{cluster_id}/support",
            headers={"Authorization": "Bearer valid:rollback-supporter"},
        )
        assert response.status_code == 500
    response = await phase2.client.get(
        f"/api/v1/reports/{seed_id('report/reported')}", headers=phase2.headers()
    )
    assert response.json()["status"] == "reported"
    response = await phase2.client.get("/api/v1/clusters/ranked", headers=phase2.headers())
    item = next(item for item in response.json()["items"] if item["id"] == str(cluster_id))
    assert item["infrastructure_gap"] == item["equity_index"] == 50
    assert item["inputs_are_demo"] and item["supporter_count"] == 1
    async with phase2.sessions() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(AuditEventRecord)
                .where(
                    AuditEventRecord.action.in_(
                        ["report.status_changed", "cluster.inputs_updated", "cluster.supported"]
                    )
                )
            )
            == 0
        )
