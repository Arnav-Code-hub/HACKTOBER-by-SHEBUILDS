"""ARQ worker entrypoint.

Deliberately NOT a separate codebase. The worker needs the same models, config
and database session as the API, so it runs from the SAME Docker image with a
different command. A `services/worker/` directory would only duplicate the
dependency set and force a shared-code package between them.

Queue the slow and the expensive here: OCR, speech-to-text, embedding backfill,
before/after image analysis, batch deduplication, problem-statement generation.
Anything a citizen waits on stays in the request path.
"""

from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    logger.info("worker.startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker.shutdown")


class WorkerSettings:
    """Discovered by `arq app.worker.WorkerSettings` (see docker-compose.yml)."""

    functions: ClassVar[list[Any]] = [
        # Registered from each module's tasks.py as they land, e.g.
        # problems_tasks.cluster_demand, problems_tasks.recompute_priority
    ]
    cron_jobs: ClassVar[list[Any]] = []
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(str(get_settings().redis_url))
    max_jobs = 10
    job_timeout = 300
