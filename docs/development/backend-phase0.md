# Backend Phase 0

This implements Revision 3's infrastructure phase. It does not add business
tables, Firebase verification, report persistence, or provider endpoints.

This is the Phase 0 record. The subsequent schema and transaction adapters are
documented in [Phase 1](backend-phase1.md); statements below about empty tables
describe the Phase 0 exit gate, not the current schema.

## Implemented

- The API starts with `ENVIRONMENT=staging` without Redis or provider credentials.
- Typed Cloudinary/Gemini settings; privileged provider secrets are server-only.
- Exact-origin CORS for bearer authentication and `Idempotency-Key`.
- A consistent `{ "detail": "..." }` error body; invalid inputs and unexpected
  exceptions are not echoed to users.
- Permissions for work orders, clustering, published statements and institute
  approval. Panchayat/officer validation is distinct from citizen verification.
- Pure canonical request hashing, lifecycle rules, effective-status selection,
  evidence selection by completion round, and scope helpers.
- Protocols for idempotent execution, conditional transitions and audit writes.
  **These are interfaces, not implemented database operations.** Their adapters
  and atomicity/concurrency tests are Phase 1 work.
- Explicit model-module registration in Alembic. There are no migration revisions
  or application tables yet.
- Isolated PostgreSQL fixtures, nested-transaction sessions, clients, every-role
  principals and fake provider clients. Test overrides never enter runtime code.
- A prototype Compose file and PostgreSQL-only API CI job. The legacy Compose
  stack and separate AI service remain references and are not required.

## Run the API locally

Install Python 3.12+ and uv 0.13.5. From `services/api`:

```bash
cp .env.example .env
# Replace AUTH_SECRET with a generated secret (at least 16 characters).
uv sync --frozen --all-groups
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

PowerShell uses `Copy-Item .env.example .env`. `/health` is public. PostgreSQL
does not need to be reachable for this liveness endpoint; this is not a
readiness check. No login or saved report is claimed to work in Phase 0.

Alternatively, after creating `services/api/.env`, run from the repository root:

```bash
docker compose -f docker-compose.prototype.yml up --build
```

This starts plain PostgreSQL and the API, with no Redis, worker or AI container.
It binds the database and API ports to the local machine only.

## Verify

From `services/api`, with Docker running:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run lint-imports
uv run pytest
```

Tests start an isolated `postgres:16-alpine` testcontainer and apply the empty
Alembic chain. No Supabase credentials or Firebase accounts are required.
An explicitly supplied `TEST_DATABASE_URL` can select a disposable test database;
the ordinary application's `DATABASE_URL` is never used for this automatically.
Missing Docker is a test failure, not a skipped successful exit gate.

Use `pytest -m "not integration"` for the fast pure/API checks. Integration
coverage currently proves migrations connect to PostgreSQL and test writes roll
back; it does not prove any future business table, idempotency implementation,
or state transition is durable.

## Handoff to Phase 1

Implement `IdempotencyStore`, `TransitionStore` and `AuditWriter` against the real
tables, retaining one caller-owned transaction for the action, reservation and
audit event. Persist only one cluster execution status; no work-order status
column. Use `evidence.select` in every evidence consumer. Add schemas/migrations,
seed/reset protection and real concurrent-request tests before wiring endpoints.

The API Dockerfile and API CI use uv 0.13.5, matching the regenerated lockfile;
image builds are frozen and fail on lockfile drift rather than silently resolving
new packages. The untouched AI service keeps its own toolchain.
