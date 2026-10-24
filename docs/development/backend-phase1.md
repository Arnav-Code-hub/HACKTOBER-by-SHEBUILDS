# Backend Phase 1 — schema, seed and transaction adapters

Implemented locally on 24 October 2026, following backend plan revision 3.
This phase adds persistence infrastructure. Business HTTP endpoints and real
Firebase token verification remain Phase 2 onward.

## Delivered

- Eighteen application tables, UUID keys, timezone-aware timestamps and explicit
  `is_demo` provenance. Report intake status and cluster execution status have
  separate allowed values; work orders have no status column.
- Initial Alembic revision `0001`, including the report-code sequence and the
  report/cluster circular foreign keys. Codes are sequence-generated `JM-N`;
  the contract's `YDG-WTR-0001` was an example, not a required format.
- Database uniqueness for category responsibility, support, allocation, work
  orders, team membership, reviews and verification rounds. Money uses positive
  BIGINT paise; media attachment kind/round and size have check constraints.
- PostgreSQL idempotency, lifecycle and audit adapters under `app/persistence/`.
  Reservations, responses, business writes and audit entries use the caller's
  transaction. Savepoints remove failed actions even when their exception is
  caught by a caller. No adapter commits independently.
- Status changes lock and refresh database rows before checking their current
  state. Cluster execution locks precede work-order locks. Reporter eligibility
  precedes the verification-round check. `report_status()` reads the one
  authoritative effective status and its actual transition timestamp.
- Deterministic insert-only demo fixtures: active Yadgir, inactive boundary
  district, a demonstration department covering all nine categories, institute,
  industry partner, ten role records, three reports, two clusters, one work
  order/allocation, published statement, approved student team and submission.
  There is only one citizen account, so each cluster has one citizen supporter.
- Explicit, guarded reset and optional approved-photo seeding. The CLI serializes
  seed/reset runs with a PostgreSQL transaction advisory lock.

## Run locally

From `services/api`, after copying `.env.example` to `.env` and setting a local
PostgreSQL `DATABASE_URL` and `AUTH_SECRET`:

```bash
uv sync --frozen --all-groups
uv run alembic upgrade head
uv run python -m app.seeds
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The prototype Compose file starts PostgreSQL and the API. Apply migrations and
seed using `docker compose -f docker-compose.prototype.yml exec api ...` with
the same `alembic upgrade head` and `python -m app.seeds` commands.

`--reference` performs no writes: no real reference dataset is imported yet.
Demo seeding is refused with `ENVIRONMENT=production`.

## Real identities and evidence are still configuration work

`seeds/demo/users.json` intentionally has null Firebase UIDs. Those rows are
disabled and use unmistakable `unprovisioned:` identifiers. They cannot sign in.
Create the ten email/password accounts in Firebase, copy this JSON to ignored
`seeds/demo/users.local.json`, enter their real UIDs, then run:

```bash
uv run python -m app.seeds --users-file seeds/demo/users.local.json
```

This provisions existing placeholders. Later runs preserve existing roles,
scope, administrative disables and demonstration progress. Changing an already
provisioned UID requires a deliberate administrative change or guarded reset.
Never put account passwords or service-account secrets into a seed file.

No image was copied from the existing gallery because its public-display
approval is undocumented. Add approved files inside `seeds/demo/photos/`, record
their source and approval in a manifest based on `photos.example.json`, configure
Cloudinary server credentials, then run:

```bash
uv run python -m app.seeds --photos-manifest seeds/demo/photos.local.json
```

Alternatively record existing public IDs at
`<CLOUDINARY_FOLDER>/demo-seed/<case>/<key>`. The loader fetches Cloudinary Admin
metadata and validates identity, type, format, size, dimensions and timestamp.
No client URL is accepted. Deterministic public IDs and `overwrite=false` permit
retries after a database rollback; a remote upload itself cannot be rolled back.
Live Cloudinary delivery and live Firebase sign-in are not established by these
tests; provider fixtures are used for photo-loader tests.

## Reset

Reset removes **all rows in the eighteen application tables** on the designated
demo database. Use it only on a disposable demo deployment. It preserves the
schema, report-code sequence and remote Cloudinary uploads. It uses no CASCADE;
an unexpected external foreign key makes it fail instead of deleting other data.

Set all three conditions explicitly:

```dotenv
ENVIRONMENT=staging
SEED_RESET_ALLOWED=true
SEED_RESET_TARGETS=janmaang@localhost:5432/janmaang
```

Then run `uv run python -m app.seeds --reset`, adding the users/photo options if
needed. The URL's decoded username, host, effective port and database must match
one whole entry. Passwords are ignored and never printed in refusal messages.
For Supabase use the exact project-specific session-pooler username, host and
port; do not use a generic shared pooler hostname as the sole guard.
Inside Compose, the configured database host is `postgres`, so its local reset
entry is `janmaang@postgres:5432/janmaang`.

## Verification and decisions

Local result: **99 tests passed** against PostgreSQL 16, including the CLI and
migration round trip. Ruff lint/format, strict mypy, import-linter and
`git diff --check` passed. Four dependency/deprecation warnings remain; they
did not fail the checks. Live provider authentication and media are still
unverified, as described above.

Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy app` and `uv run lint-imports`.

Database tests use a disposable PostgreSQL 16 container, or an explicit
`TEST_DATABASE_URL`. The suite resets application tables on that test target;
never point it at a database whose data matters. Migration round-trip testing
uses a separate temporary database and needs CREATEDB on the test server.

Tests cover migration application and reversal, zero autogenerate changes,
identical seed rows on rerun, placeholder provisioning, database constraints,
each reset-target component, actual PostgreSQL lock contention between concurrent
retries, action failure rollback, competing transitions, scope, round checks,
effective status and audit atomicity. Phase 4 still supplies funding endpoint
tests; Phase 5 supplies evidence/verification endpoint tests.

Decision record — 24 October 2026, implementation owner: Codex:

- Need: preserve the module import boundary while implementing shared database
  transactions. Options: import business models into core, duplicate helpers in
  modules, or implement explicit composition adapters. Choice: adapters outside
  core/modules. Trade-off: one small composition layer knows multiple tables.
  Evidence: import-linter and module-boundary tests.
- Need: repeatable demonstrations without destroying review progress. Choice:
  insert-only deterministic fixtures plus an explicit reset. Trade-off: existing
  fixtures do not silently adopt future seed edits. Evidence: full-row snapshot
  comparison and preservation of edited records.
- Need: seed usable identities/photos without inventing external configuration.
  Choice: disabled UID placeholders and an approved-photo manifest. Trade-off:
  provider setup remains required before the hosted demonstration.
