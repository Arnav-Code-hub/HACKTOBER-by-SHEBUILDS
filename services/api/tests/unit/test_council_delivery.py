from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, UpstreamError
from app.core.roles import Role
from app.modules.council.schemas import CouncilEvidence, RemoteAssessment
from app.persistence import council
from tests.integration.helpers import demo_principal


def evidence():
    return CouncilEvidence(
        title="Study", research_question="Does it work?", findings="Some findings."
    )


def remote(*, simulated=False, status="completed", identity=None):
    issue = {
        "title": "Check baseline",
        "severity": "Moderate",
        "claim_status": "not_verifiable",
        "detail": "No measurements supplied.",
        "consequence": "Claim is unverified.",
        "improvement": "Add baseline.",
        "verification": "Repeat measurement.",
        "evidence": [{"evidence_id": "E02", "start_line": 1, "end_line": 1}],
    }
    return RemoteAssessment.model_validate(
        {
            "id": str(identity or uuid4()),
            "status": status,
            "completed_reviewers": 5 if status == "completed" else 0,
            "project": evidence().model_dump(),
            "report": {
                "version": "1.0",
                "simulated": simulated,
                "model": "test-model",
                "prompt_version": "1.0",
                "summary": "Advisory report.",
                "reviewers": [
                    {
                        "reviewer": r,
                        "strengths": [],
                        "issues": [issue],
                        "limitations": ["Only supplied evidence reviewed."],
                    }
                    for r in ["evidence", "engineer", "sceptic", "impact", "delivery"]
                ],
                "priorities": [],
                "limitations": [],
            }
            if status == "completed"
            else None,
        }
    )


def row():
    return SimpleNamespace(
        id=uuid4(),
        team_id=uuid4(),
        supervisor_id=uuid4(),
        remote_id=None,
        evidence=evidence().model_dump(),
        status="queued",
        retry_requested=False,
        error=None,
        completed_reviewers=0,
        report=None,
        pdf=None,
        delivered_at=None,
        next_attempt_at=datetime.now(UTC),
    )


def settings():
    return Settings(_env_file=None, database_url="postgresql+asyncpg://test:test@localhost/test")


def test_completed_report_requires_matching_snapshot_and_real_reviews():
    completed = remote()
    council.validate_remote(evidence(), completed, False)
    completed.project.findings = "Changed evidence"
    with pytest.raises(UpstreamError, match="snapshot"):
        council.validate_remote(evidence(), completed, False)
    with pytest.raises(UpstreamError, match="Simulated"):
        council.validate_remote(evidence(), remote(simulated=True), False)
    bad = remote()
    bad.report.reviewers[0].issues[0].evidence[0].end_line = 500
    with pytest.raises(UpstreamError, match="reference"):
        council.validate_remote(evidence(), bad, False)


def test_scope_query_constrains_student_membership_and_faculty_snapshot():
    student = demo_principal(Role.STUDENT)
    faculty = demo_principal(Role.FACULTY)
    student_query = council.assessment_scope(student).compile(dialect=postgresql.dialect())
    faculty_query = council.assessment_scope(faculty).compile(dialect=postgresql.dialect())
    assert "team_members.user_id" in str(student_query)
    assert "teams.institute_id" in str(student_query)
    assert "problem_statements.district_id" in str(student_query)
    assert "council_assessments.supervisor_id =" in str(faculty_query)
    assert faculty.user_id in faculty_query.params.values()


@pytest.mark.asyncio
async def test_network_failure_retains_upstream_identity_for_delivery_retry():
    item = row()
    remote_id = uuid4()
    client = SimpleNamespace(
        submit=AsyncMock(return_value=remote_id),
        read=AsyncMock(side_effect=UpstreamError("Temporary failure.")),
    )
    await council.advance(AsyncMock(), item, client, settings())
    assert item.status == "delivery_failed"
    assert item.remote_id == remote_id
    client.read = AsyncMock(return_value=remote(status="running", identity=remote_id))
    await council.advance(AsyncMock(), item, client, settings())
    assert item.status == "reviewing"
    assert client.submit.await_count == 1


@pytest.mark.asyncio
async def test_publication_persists_both_artifacts_before_available(monkeypatch):
    item = row()
    completed = remote()
    client = SimpleNamespace(
        submit=AsyncMock(return_value=completed.id),
        read=AsyncMock(return_value=completed),
        pdf=AsyncMock(return_value=b"%PDF-test"),
    )
    publish = AsyncMock()
    monkeypatch.setattr(council, "publish_case_update", publish)
    session = SimpleNamespace(scalars=AsyncMock(return_value=[]))
    await council.advance(session, item, client, settings())
    assert item.status == "available" and item.report and item.pdf.startswith(b"%PDF-")
    assert item.delivered_at is not None
    assert publish.await_args.args[1] == [item.supervisor_id]


@pytest.mark.asyncio
async def test_incomplete_does_not_publish_or_fetch_pdf(monkeypatch):
    item = row()
    incomplete = remote(status="incomplete")
    client = SimpleNamespace(
        submit=AsyncMock(return_value=incomplete.id),
        read=AsyncMock(return_value=incomplete),
        pdf=AsyncMock(),
    )
    publish = AsyncMock()
    monkeypatch.setattr(council, "publish_case_update", publish)
    await council.advance(AsyncMock(), item, client, settings())
    assert item.status == "incomplete"
    client.pdf.assert_not_awaited()
    publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_supervisor_blocks_submission_before_queue(monkeypatch):
    principal = demo_principal(Role.STUDENT)
    team = SimpleNamespace(id=uuid4(), institute_approved=True)
    submission = SimpleNamespace(id=uuid4(), team_id=team.id)
    session = SimpleNamespace(
        get=AsyncMock(return_value=submission), scalar=AsyncMock(return_value=None)
    )
    monkeypatch.setattr(council, "scoped_team", AsyncMock(return_value=team))

    async def execute(self, session, identity, action):
        return await action()

    monkeypatch.setattr(council.SqlIdempotencyStore, "execute", execute)
    with pytest.raises(ConflictError, match="assign"):
        await council.create_assessment(session, principal, submission.id, evidence(), "first")


@pytest.mark.asyncio
async def test_cross_scope_detail_does_not_leak_record():
    session = SimpleNamespace(scalar=AsyncMock(return_value=None))
    with pytest.raises(NotFoundError):
        await council.assessment_get(session, demo_principal(Role.FACULTY), uuid4())


def test_configuration_requires_private_service_secret():
    with pytest.raises(ValueError, match="COUNCIL_SERVICE_KEY"):
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            council_enabled=True,
            council_url="https://council.example",
        )
    with pytest.raises(ValueError, match="COUNCIL_URL"):
        Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            council_enabled=True,
            council_url="http://public.example",
            council_service_key="x" * 40,
        )


@pytest.mark.asyncio
async def test_history_projects_metadata_without_loading_artifacts():
    result = SimpleNamespace(mappings=lambda: [])
    session = SimpleNamespace(execute=AsyncMock(return_value=result))
    assert (await council.assessment_list(session, demo_principal(Role.STUDENT))).items == []
    query = session.execute.await_args.args[0].compile(dialect=postgresql.dialect())
    sql = str(query)
    assert "council_assessments.pdf" not in sql
    assert "council_assessments.report" not in sql
    assert "->>" in sql


@pytest.mark.asyncio
async def test_transport_retries_preserve_explicit_retry_generation():
    item = row()
    item.remote_id = uuid4()
    item.retry_requested = True
    item.retry_key = str(uuid4())
    client = SimpleNamespace(retry=AsyncMock(side_effect=UpstreamError("Response lost.")))
    await council.advance(AsyncMock(), item, client, settings())
    await council.advance(AsyncMock(), item, client, settings())
    assert item.status == "delivery_failed"
    assert [call.args for call in client.retry.await_args_list] == [
        (item.remote_id, item.retry_key),
        (item.remote_id, item.retry_key),
    ]


def test_council_tables_follow_seed_snapshot_id_convention():
    from app.modules.council.models import CouncilAssessment, TeamSupervisor

    assert "id" in CouncilAssessment.__table__.c
    assert "id" in TeamSupervisor.__table__.c


@pytest.mark.asyncio
async def test_explicit_delivery_retry_does_not_replace_pending_model_retry_key(monkeypatch):
    item = row()
    item.status = "delivery_failed"
    item.retry_requested = True
    item.retry_key = "durable-generation"
    item.remote_id = uuid4()
    item.created_at = datetime.now(UTC)
    item.submission_id = uuid4()
    item.supervisor_name = "Faculty"
    monkeypatch.setattr(council, "assessment_get", AsyncMock(return_value=item))
    monkeypatch.setattr(council, "log", AsyncMock())
    await council.request_retry(AsyncMock(), demo_principal(Role.STUDENT), item.id)
    assert item.retry_requested and item.retry_key == "durable-generation"


@pytest.mark.asyncio
async def test_detail_returns_immutable_evidence_for_pdf_references(monkeypatch):
    item = row()
    item.created_at = datetime.now(UTC)
    item.submission_id = uuid4()
    item.supervisor_name = "Faculty"
    monkeypatch.setattr(council, "assessment_get", AsyncMock(return_value=item))
    detail = await council.assessment_detail(AsyncMock(), demo_principal(Role.FACULTY), item.id)
    assert detail.evidence == evidence()
