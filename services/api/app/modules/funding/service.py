"""Business logic for funding. THE PUBLIC FACE of this module.

Allocations are recorded amounts in integer paise. No payment is processed.

# Module boundary: other modules may import this file and schemas.py.
# They must NEVER import models.py or repository.py.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.funding.models import Allocation


async def record_allocation(
    session: AsyncSession,
    *,
    cluster_id: UUID,
    work_order_id: UUID,
    amount_paise: int,
    allocated_by: UUID,
    is_demo: bool,
) -> UUID:
    """Insert the cluster's one allocation in the caller's transaction.

    The unique constraints on cluster and work order refuse a second
    allocation even if a caller skipped the status precondition.
    """
    allocation = Allocation(
        cluster_id=cluster_id,
        work_order_id=work_order_id,
        amount_paise=amount_paise,
        allocated_by=allocated_by,
        is_demo=is_demo,
    )
    session.add(allocation)
    await session.flush()
    return allocation.id


async def allocated_paise(session: AsyncSession, work_order_ids: list[UUID]) -> dict[UUID, int]:
    if not work_order_ids:
        return {}
    rows = await session.execute(
        select(Allocation.work_order_id, Allocation.amount_paise).where(
            Allocation.work_order_id.in_(work_order_ids)
        )
    )
    return {row.work_order_id: row.amount_paise for row in rows}
