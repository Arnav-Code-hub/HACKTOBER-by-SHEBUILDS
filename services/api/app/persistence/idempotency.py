"""PostgreSQL unique-index arbitration; no process-local locks or cache."""

from collections.abc import Awaitable, Callable

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.core.idempotency import RequestIdentity, StoredResponse
from app.modules.auth.models import IdempotencyKey


class SqlIdempotencyStore:
    async def execute(
        self,
        session: AsyncSession,
        identity: RequestIdentity,
        action: Callable[[], Awaitable[StoredResponse]],
    ) -> StoredResponse:
        # A caught action failure must not leave a reservation for the caller
        # to commit accidentally. The savepoint also rolls back action/audit writes.
        async with session.begin_nested():
            reserved = await session.scalar(
                insert(IdempotencyKey)
                .values(
                    user_id=identity.user_id,
                    operation=identity.operation,
                    key=identity.key,
                    request_hash=identity.request_hash,
                )
                .on_conflict_do_nothing(index_elements=["user_id", "operation", "key"])
                .returning(IdempotencyKey.id)
            )
            if reserved is None:
                # ON CONFLICT waits for an in-flight owner. At READ COMMITTED
                # this separate statement sees that owner's committed response.
                previous = (
                    await session.scalars(
                        select(IdempotencyKey).where(
                            IdempotencyKey.user_id == identity.user_id,
                            IdempotencyKey.operation == identity.operation,
                            IdempotencyKey.key == identity.key,
                        )
                    )
                ).one()
                if previous.request_hash != identity.request_hash:
                    raise ConflictError("This request key was already used for different data.")
                if previous.status_code is None or previous.response_json is None:
                    raise ConflictError("This request has no completed response; contact support.")
                return StoredResponse(previous.status_code, previous.response_json)
            response = await action()
            if not 200 <= response.status_code < 300:
                raise ValueError("Only successful business responses can be stored")
            await session.execute(
                update(IdempotencyKey)
                .where(IdempotencyKey.id == reserved)
                .values(status_code=response.status_code, response_json=response.body)
            )
            return response
