"""Database access for analytics. PRIVATE to this module.

Only service.py in this module may call these functions.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal
from app.modules.analytics.schemas import PublicTransparency, StaffWorkloadList
from app.persistence.oversight import public_transparency as _public_transparency
from app.persistence.oversight import staff_workload as _staff_workload


async def public_dashboard(session: AsyncSession) -> PublicTransparency:
    return await _public_transparency(session)


async def workload(session: AsyncSession, principal: Principal) -> StaffWorkloadList:
    return await _staff_workload(session, principal)
