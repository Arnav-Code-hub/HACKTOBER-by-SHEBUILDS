"""JanMaang AI service.

ONE service, modular by capability — not six microservices, and not a module
inside the API.

Separate from the API because: the ML dependency set would bloat every API
rebuild; LLM calls take 2-30s and would starve a latency-sensitive API's worker
pool; an OOM in image analysis must not take down citizen report submission; and
this may need GPU nodes the API never will.

One service rather than six because every capability shares tokenisation,
language detection, embeddings and prompt infrastructure — six deployments for
one team is cost without benefit. Extract only what proves it needs different
hardware.

STATELESS. This service owns no domain tables and never talks to the business
database. The API calls it and persists the result.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.capabilities.chat.router import router as chat_router
from app.capabilities.classification.router import router as classification_router
from app.capabilities.deduplication.router import router as deduplication_router
from app.capabilities.language.router import router as language_router
from app.capabilities.matching.router import router as matching_router
from app.capabilities.prioritization.router import router as prioritization_router
from app.capabilities.recommendation.router import router as recommendation_router
from app.capabilities.speech.router import router as speech_router
from app.capabilities.statement_generation.router import router as statement_router
from app.capabilities.vision.router import router as vision_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)

CAPABILITY_ROUTERS = (
    classification_router,
    deduplication_router,
    prioritization_router,
    statement_router,
    language_router,
    speech_router,
    vision_router,
    matching_router,
    recommendation_router,
    chat_router,
)


async def verify_internal_key(x_internal_key: str = Header(default="")) -> None:
    """This service is internal-only. The API is its sole legitimate caller."""
    settings = get_settings()
    if not settings.internal_api_key or x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal key")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    logger.info("ai.startup", provider=settings.llm_provider, model=settings.llm_model)
    yield
    logger.info("ai.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="JanMaang AI",
        description="Internal AI capabilities. Called only by services/api.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    for router in CAPABILITY_ROUTERS:
        app.include_router(router, dependencies=[Depends(verify_internal_key)])

    @app.get("/health", tags=["Meta"], include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "model": settings.llm_model}

    return app


app = create_app()
