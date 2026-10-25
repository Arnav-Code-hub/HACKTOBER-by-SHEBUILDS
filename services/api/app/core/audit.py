"""Audit data and the persistence interface, with no module-table dependency."""

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class AuditEvent:
    actor_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    district_id: UUID | None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    reason: str | None = None


class AuditWriter(Protocol):
    async def log_event(self, session: AsyncSession, event: AuditEvent) -> None:
        """Phase 1 adapter inserts into audit_events in the caller's transaction.

        Never commit here. District scope belongs to the affected record, not
        the actor's current assignment. Platform events use district_id=None.
        """
        ...
