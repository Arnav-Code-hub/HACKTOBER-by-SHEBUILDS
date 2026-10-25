"""Request identity and the persistence boundary for Phase 1.

The store MUST reserve (user_id, operation, key), execute the business write,
write its audit event and save the response in the supplied transaction. It
must never commit independently. No in-memory substitute is used in the API.
"""

import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


def request_hash(payload: Mapping[str, Any]) -> str:
    """Hash a validated JSON payload; object ordering does not change identity.

    Hash after request-schema validation, so omitted defaults are normalized by
    the endpoint. Lists retain their order; non-finite numbers are refused.
    """
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class RequestIdentity:
    user_id: UUID
    operation: str
    key: str
    request_hash: str

    def __post_init__(self) -> None:
        if not self.operation.strip() or not self.key.strip() or len(self.key) > 200:
            raise ValueError("An operation and a key of at most 200 characters are required")


@dataclass(frozen=True)
class StoredResponse:
    status_code: int
    body: dict[str, Any]


class IdempotencyStore(Protocol):
    async def execute(
        self,
        session: AsyncSession,
        identity: RequestIdentity,
        action: Callable[[], Awaitable[StoredResponse]],
    ) -> StoredResponse:
        """Phase 1: atomic insert/conflict wait, hash check, action and response.

        Identical retries return the first committed response. Different
        payloads conflict. A rollback removes the reservation and its writes.
        """
        ...
