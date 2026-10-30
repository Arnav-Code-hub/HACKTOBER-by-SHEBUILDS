import base64
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ConflictError, ServiceUnavailableError
from app.core.security import Principal, get_current_principal
from app.modules.council import service
from app.modules.council.schemas import (
    AssessmentDetail,
    AssessmentList,
    AssessmentRead,
    CouncilEvidence,
    FacultyList,
    PdfRead,
    SupervisorCreate,
    SupervisorRead,
)

router = APIRouter(prefix="/council", tags=["Council integration"])


def enabled() -> None:
    if not get_settings().council_enabled:
        raise ServiceUnavailableError("Council integration is disabled.")


@router.get("/config")
async def config(principal: Principal = Depends(get_current_principal)) -> dict[str, bool]:
    return {"enabled": get_settings().council_enabled}


@router.get("/faculty", response_model=FacultyList, dependencies=[Depends(enabled)])
async def faculty(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> FacultyList:
    return await service.faculty_list(session, principal)


@router.get(
    "/teams/{team_id}/supervisor", response_model=SupervisorRead, dependencies=[Depends(enabled)]
)
async def supervisor(
    team_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> SupervisorRead:
    return await service.supervisor_read(session, principal, team_id)


@router.post(
    "/teams/{team_id}/supervisor", response_model=SupervisorRead, dependencies=[Depends(enabled)]
)
async def assign(
    team_id: UUID,
    body: SupervisorCreate,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> SupervisorRead:
    return await service.assign_supervisor(session, principal, team_id, body.faculty_id)


@router.get("/assessments", response_model=AssessmentList, dependencies=[Depends(enabled)])
async def assessments(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> AssessmentList:
    return await service.assessment_list(session, principal)


@router.post(
    "/submissions/{submission_id}/assessments",
    response_model=AssessmentRead,
    status_code=202,
    dependencies=[Depends(enabled)],
)
async def create(
    submission_id: UUID,
    body: CouncilEvidence,
    key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"\S"),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> JSONResponse:
    result = await service.create_assessment(session, principal, submission_id, body, key)
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.get(
    "/assessments/{identity}", response_model=AssessmentDetail, dependencies=[Depends(enabled)]
)
async def assessment(
    identity: UUID,
    response: Response,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> AssessmentDetail:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.assessment_detail(session, principal, identity)


@router.post(
    "/assessments/{identity}/retry", response_model=AssessmentRead, dependencies=[Depends(enabled)]
)
async def retry(
    identity: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> AssessmentRead:
    return await service.request_retry(session, principal, identity)


@router.get("/assessments/{identity}/pdf", response_model=PdfRead, dependencies=[Depends(enabled)])
async def pdf(
    identity: UUID,
    response: Response,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> PdfRead:
    row = await service.assessment_get(session, principal, identity, with_pdf=True)
    if row.status != "available" or row.pdf is None:
        raise ConflictError("A complete council report is not available.")
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return PdfRead(content_base64=base64.b64encode(row.pdf).decode("ascii"))
