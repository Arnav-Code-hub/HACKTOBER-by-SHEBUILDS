"""FastAPI application factory.

JanMaang's API is a MODULAR MONOLITH: one deployable, many isolated modules.
Microservices at this team size would spend the schedule on service discovery
and distributed tracing instead of on features. The import-linter contract in
pyproject.toml keeps the module seams real, so any module can be extracted into
its own service later without changing a caller.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import SuggestionRateLimiter
from app.integrations.firebase import FirebaseTokenVerifier
from app.modules.analytics.router import router as analytics_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.service import DatabaseAuthenticator
from app.modules.departments.router import router as departments_router
from app.modules.files.router import router as files_router
from app.modules.funding.router import router as funding_router
from app.modules.notifications.router import router as notifications_router
from app.modules.problem_statements.router import router as problem_statements_router
from app.modules.problems.router import cases_router, clusters_router, work_orders_router
from app.modules.problems.router import router as problems_router
from app.modules.projects.router import router as projects_router
from app.modules.rbac.router import router as rbac_router
from app.modules.teams.router import router as teams_router
from app.modules.users.router import router as users_router

logger = get_logger(__name__)

API_V1 = "/api/v1"

MODULE_ROUTERS = (
    auth_router,
    users_router,
    rbac_router,
    departments_router,
    problems_router,
    clusters_router,
    work_orders_router,
    cases_router,
    problem_statements_router,
    projects_router,
    teams_router,
    funding_router,
    files_router,
    audit_router,
    notifications_router,
    analytics_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    logger.info("api.startup", environment=settings.environment)
    yield
    logger.info("api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="JanMaang API",
        description=(
            "Civic demand-to-budget platform. A citizen reports a local need; "
            "AI structures it; identical reports cluster; the cluster is ranked, "
            "funded, executed and citizen-verified."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=f"{API_V1}/openapi.json",
    )

    app.state.authenticator = DatabaseAuthenticator(FirebaseTokenVerifier())
    app.state.suggestion_limiter = SuggestionRateLimiter()

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "Accept"],
        )

    register_error_handlers(app)

    v1 = APIRouter(prefix=API_V1)
    for module_router in MODULE_ROUTERS:
        v1.include_router(module_router)
    app.include_router(v1)

    @app.get("/health", tags=["Meta"], include_in_schema=False)
    async def health() -> dict[str, str]:
        """Liveness probe. Used by the container healthcheck and the load balancer."""
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
