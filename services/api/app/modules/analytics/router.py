"""HTTP surface for analytics. Routing and validation only.

Business logic belongs in service.py; this file translates HTTP to it.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.analytics import service
from app.modules.analytics.schemas import PublicTransparency

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/public", response_model=PublicTransparency)
async def public_transparency(
    session: AsyncSession = Depends(get_db, scope="function"),
) -> PublicTransparency:
    """Public non-demo totals, with no authentication or personal records."""
    return await service.public_transparency(session)
