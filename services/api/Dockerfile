# syntax=docker/dockerfile:1
# Multi-stage. `development` has dev deps and source mounted over it by
# docker-compose.override.yml; `production` is slim and runs as a non-root user.
#
# The prototype runs one API service; the legacy worker is not deployed.

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/
WORKDIR /app

# Dependencies resolve in their own layer, so an application-code change does
# not reinstall the world.
FROM base AS deps
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then \
      export SSL_CERT_FILE=/run/secrets/build_ca UV_SYSTEM_CERTS=true; \
    fi; uv sync --frozen --no-install-project --all-groups

FROM deps AS development
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then \
      export SSL_CERT_FILE=/run/secrets/build_ca UV_SYSTEM_CERTS=true; \
    fi; uv sync --frozen --all-groups
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
COPY --from=deps /app/.venv /app/.venv
# Drop dev dependencies from the production image.
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then \
      export SSL_CERT_FILE=/run/secrets/build_ca UV_SYSTEM_CERTS=true; \
    fi; uv sync --frozen --no-install-project --no-dev
COPY ./app ./app
COPY ./seeds ./seeds
COPY alembic.ini ./
RUN useradd --create-home --uid 10001 janmaang && chown -R janmaang:janmaang /app
USER janmaang
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1
CMD ["python", "-m", "app.start"]
