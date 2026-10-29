"""HTTP surface for analytics. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.modules.analytics import service
from app.modules.analytics.schemas import PublicTransparency, StaffWorkloadList

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/public", response_model=PublicTransparency)
async def public_transparency(
    session: AsyncSession = Depends(get_db, scope="function"),
) -> PublicTransparency:
    """Anonymous aggregate only. Reporter identity and exact coordinates stay private."""
    return await service.public_transparency(session)


@router.get("/workload", response_model=StaffWorkloadList)
async def staff_workload(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db, scope="function"),
) -> StaffWorkloadList:
    return await service.staff_workload(session, principal)
