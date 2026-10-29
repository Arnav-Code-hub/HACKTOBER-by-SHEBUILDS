"""Scoped citizen/staff reports and the agreed cluster endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import PermissionDeniedError
from app.core.security import Principal, get_current_principal
from app.integrations.cloudinary import MediaProvider, get_media_provider
from app.integrations.gemini import SuggestionProvider, get_suggestion_provider
from app.modules.problems import (
    cases,
    clusters,
    service,
    suggestions,
    verification,
    work_orders,
)
from app.modules.problems.schemas import (
    AssignCluster,
    CaseList,
    ClusterSuggestions,
    CompleteWorkOrder,
    EvidenceRead,
    FundCluster,
    FundResult,
    IdentityAck,
    RankedClusters,
    RankingInputs,
    ReportCreate,
    ReportList,
    ReportRead,
    ReportSuggestion,
    StatusAck,
    SuggestionRequest,
    SupportAck,
    ValidateReport,
    VerificationRead,
    VerifyWorkOrder,
    WorkOrderList,
    WorkOrderUpdate,
)

router = APIRouter(prefix="/reports", tags=["Reports"])
clusters_router = APIRouter(prefix="/clusters", tags=["Clusters"])
work_orders_router = APIRouter(prefix="/work-orders", tags=["Work orders"])
cases_router = APIRouter(prefix="/cases", tags=["Cases"])

IdempotencyKey = Header(alias="Idempotency-Key", min_length=1, max_length=200, pattern=r"\S")


@router.post("/suggest", response_model=ReportSuggestion)
async def suggest_report(
    body: SuggestionRequest,
    request: Request,
    principal: Principal = Depends(get_current_principal),
    settings: Settings = Depends(get_settings),
    provider: SuggestionProvider = Depends(get_suggestion_provider),
) -> ReportSuggestion:
    return await suggestions.suggest_report(
        principal, body, settings, provider, request.app.state.suggestion_limiter
    )


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


@clusters_router.post("/{cluster_id}/fund", response_model=FundResult, status_code=201)
async def fund(
    cluster_id: UUID,
    body: FundCluster,
    key: str = IdempotencyKey,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> JSONResponse:
    result = await work_orders.fund_cluster(session, principal, cluster_id, body, key)
    return JSONResponse(status_code=result.status_code, content=result.body)


@work_orders_router.get("", response_model=WorkOrderList)
async def my_work_orders(
    mine: bool = True,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> WorkOrderList:
    if not mine:
        raise PermissionDeniedError("Officers can list only their own work orders.")
    return await work_orders.my_work_orders(session, principal)


@work_orders_router.patch("/{work_order_id}", response_model=StatusAck)
async def update_work_order(
    work_order_id: UUID,
    body: WorkOrderUpdate,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> StatusAck:
    return await work_orders.update_work_order(session, principal, work_order_id, body)


@work_orders_router.post("/{work_order_id}/complete", response_model=StatusAck)
async def complete_work_order(
    work_order_id: UUID,
    body: CompleteWorkOrder,
    key: str = IdempotencyKey,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> JSONResponse:
    result = await work_orders.complete_work_order(session, principal, work_order_id, body, key)
    return JSONResponse(status_code=result.status_code, content=result.body)


@work_orders_router.get("/{work_order_id}/evidence", response_model=EvidenceRead)
async def work_order_evidence(
    work_order_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    provider: MediaProvider = Depends(get_media_provider),
) -> EvidenceRead:
    return await work_orders.work_order_evidence(session, principal, work_order_id, provider)


@router.get("/{report_id}/verification", response_model=VerificationRead)
async def report_verification(
    report_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
    provider: MediaProvider = Depends(get_media_provider),
) -> VerificationRead:
    return await verification.verification_view(session, principal, report_id, provider)


@work_orders_router.post("/{work_order_id}/verify", response_model=StatusAck)
async def verify_work_order(
    work_order_id: UUID,
    body: VerifyWorkOrder,
    key: str = IdempotencyKey,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> JSONResponse:
    result = await verification.verify_work_order(session, principal, work_order_id, body, key)
    return JSONResponse(status_code=result.status_code, content=result.body)


@cases_router.get("", response_model=CaseList)
async def case_list(
    limit: int = Query(default=200, ge=1, le=200),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> CaseList:
    return await cases.case_list(session, principal, limit)
