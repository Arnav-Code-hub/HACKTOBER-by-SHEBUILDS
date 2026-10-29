"""Business logic for analytics. THE PUBLIC FACE of this module.

Aggregations powering the role dashboards.

# Module boundary: other modules may import this file and schemas.py.
# They must NEVER import models.py or repository.py — see the import-linter
# contract in pyproject.toml. That rule is what makes this module extractable
# into its own service later without touching a single caller.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal
from app.modules.analytics import repository
from app.modules.analytics.schemas import PublicTransparency, StaffWorkloadList


async def public_transparency(session: AsyncSession) -> PublicTransparency:
    return await repository.public_dashboard(session)


async def staff_workload(session: AsyncSession, principal: Principal) -> StaffWorkloadList:
    return await repository.workload(session, principal)
