"""Durable outbox polling. Disabled until the external council is configured."""

import asyncio
from datetime import UTC, datetime

import httpx
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.integrations.council import CouncilClient
from app.modules.council.models import CouncilAssessment
from app.persistence.council import advance

logger = get_logger(__name__)


async def poll_once(settings: Settings, client: CouncilClient) -> bool:
    async with SessionLocal.begin() as session:
        row = await session.scalar(
            select(CouncilAssessment)
            .where(
                CouncilAssessment.status.in_(["queued", "reviewing", "delivery_failed"]),
                CouncilAssessment.next_attempt_at <= datetime.now(UTC),
            )
            .order_by(CouncilAssessment.next_attempt_at, CouncilAssessment.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return False
        await advance(session, row, client, settings)
        return True


async def council_worker(settings: Settings) -> None:
    async with httpx.AsyncClient(
        base_url=settings.council_url,
        headers={"X-Council-Key": settings.council_service_key.get_secret_value()},
        timeout=10,
        follow_redirects=False,
        trust_env=False,
    ) as http:
        client = CouncilClient(http)
        while True:
            try:
                more = await poll_once(settings, client)
            except Exception as exc:
                logger.error("council.delivery_failed", error_type=type(exc).__name__)
                more = False
            await asyncio.sleep(1 if more else 5)
