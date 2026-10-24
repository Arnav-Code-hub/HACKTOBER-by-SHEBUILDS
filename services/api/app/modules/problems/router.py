"""Scoped citizen/staff reports and the agreed cluster endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.integrations.cloudinary import MediaProvider, get_media_provider
from app.modules.problems import clusters, service
from app.modules.problems.schemas import (
    AssignCluster,
    ClusterSuggestions,
    IdentityAck,
    RankedClusters,
    RankingInputs,
    ReportCreate,
    ReportList,
    ReportRead,
    StatusAck,
    SupportAck,
    ValidateReport,
)

router = APIRouter(prefix="/reports", tags=["Reports"])
clusters_router = APIRouter(prefix="/clusters", tags=["Clusters"])


@router.post("", response_model=ReportRead, status_code=201)
async def create(
    body: ReportCreate,
    key: str = Header(alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"\S"),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    provider: MediaProvider = Depends(get_media_provider),
) -> JSONResponse:
    result = await service.create_report(session, principal, body, key, provider)
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.get("", response_model=ReportList)
async def mine(
    mine: bool | None = None,
    status: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    provider: MediaProvider = Depends(get_media_provider),
) -> ReportList:
    return await service.list_reports(
        session, principal, provider, mine=mine, limit=limit, offset=offset, status=status
    )


@router.get("/{report_id}", response_model=ReportRead)
async def detail(
    report_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    provider: MediaProvider = Depends(get_media_provider),
) -> ReportRead:
    return await service.get_report(session, principal, report_id, provider)


@router.post("/{report_id}/validate", response_model=StatusAck)
async def validate(
    report_id: UUID,
    body: ValidateReport,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> StatusAck:
    return await clusters.validate_report(session, principal, report_id, body)


@router.get("/{report_id}/cluster-suggestions", response_model=ClusterSuggestions)
async def suggest_clusters(
    report_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> ClusterSuggestions:
    return await clusters.suggestions(session, principal, report_id)


@router.post("/{report_id}/cluster", response_model=StatusAck)
async def confirm_cluster(
    report_id: UUID,
    body: AssignCluster,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> StatusAck:
    return await clusters.assign_cluster(session, principal, report_id, body)


@clusters_router.get("/ranked", response_model=RankedClusters)
async def ranked(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> RankedClusters:
    return await clusters.ranked_clusters(session, principal)


@clusters_router.patch("/{cluster_id}/inputs", response_model=IdentityAck)
async def inputs(
    cluster_id: UUID,
    body: RankingInputs,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> IdentityAck:
    return await clusters.update_inputs(session, principal, cluster_id, body)


@clusters_router.post("/{cluster_id}/support", response_model=SupportAck)
async def support(
    cluster_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> SupportAck:
    return await clusters.support_cluster(session, principal, cluster_id)
