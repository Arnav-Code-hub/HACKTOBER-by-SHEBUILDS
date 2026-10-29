"""Database access for analytics. PRIVATE to this module.

Only service.py in this module may call these functions.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.schemas import PublicTransparency
from app.persistence.oversight import public_transparency


async def public_dashboard(session: AsyncSession) -> PublicTransparency:
    return await public_transparency(session)
