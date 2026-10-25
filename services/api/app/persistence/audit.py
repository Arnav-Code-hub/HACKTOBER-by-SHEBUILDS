"""Write an audit event inside the business transaction."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditEvent
from app.core.errors import NotFoundError
from app.modules.audit.models import AuditEventRecord
from app.modules.users.models import User


class SqlAuditWriter:
    async def log_event(self, session: AsyncSession, event: AuditEvent) -> None:
        actor = (
            await session.execute(select(User.role, User.is_demo).where(User.id == event.actor_id))
        ).one_or_none()
        if actor is None:
            raise NotFoundError("Audit actor not found.")
        session.add(
            AuditEventRecord(
                actor_id=event.actor_id,
                actor_role=actor.role,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                district_id=event.district_id,
                before=event.before,
                after=event.after,
                reason=event.reason,
                is_demo=actor.is_demo,
            )
        )
        await session.flush()
