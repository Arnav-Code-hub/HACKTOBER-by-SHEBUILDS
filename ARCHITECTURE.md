# Architecture

One page. Detail lives in [docs/architecture/](docs/architecture/); the reasoning
lives in [the ADRs](docs/architecture/decisions/).

## Shape

```
   ┌────────────────┐          ┌────────────────┐
   │  apps/mobile   │          │   apps/web     │
   │  Flutter       │          │   Next.js      │
   │  citizens      │          │   9 roles      │
   └───────┬────────┘          └───────┬────────┘
           │      HTTPS + Firebase ID token
           └──────────────┬──────────────┘
                          ▼
              ┌───────────────────────┐        ┌──────────────────┐
              │    services/api       │───────▶│   services/ai    │
              │  FastAPI              │  HTTP  │  stateless       │
              │  modular monolith     │◀───────│  internal only   │
              │  OWNS THE SCHEMA      │        └──────────────────┘
              └────┬─────────────┬────┘
                   │             │ enqueue
                   ▼             ▼
        ┌──────────────────┐  ┌──────────────┐
        │ Postgres 16      │  │ Redis        │
        │ PostGIS pgvector │  │ cache+queue  │
        └──────────────────┘  └──────┬───────┘
                                     ▼
                            ┌──────────────────┐
                            │ worker (ARQ)     │
                            │ SAME IMAGE as api│
                            └──────────────────┘

  Firebase, retained deliberately:  Auth (phone OTP) · FCM push · Storage
```

## The four decisions

| ADR | Decision |
|---|---|
| [0001](docs/architecture/decisions/0001-one-repository.md) | One repository, polyglot, no cross-ecosystem monorepo tool |
| [0002](docs/architecture/decisions/0002-postgres-over-firestore.md) | Postgres + PostGIS primary; Firebase kept for Auth, FCM, Storage |
| [0003](docs/architecture/decisions/0003-separate-ai-service.md) | One separate AI service, modular by capability, stateless |
| [0004](docs/architecture/decisions/0004-single-web-app.md) | One web app with role-based routes, admin kept import-isolated |

## Invariants

These are load-bearing. Breaking one is an architecture change, not a refactor.

1. **The API owns the schema.** Nothing else writes DDL. The AI service is
   stateless and reaches data only through the API.
2. **Modules talk through `service.py` and `schemas.py`** — never another
   module's `models.py` or `repository.py`. Enforced by `import-linter` in CI.
   This is what makes extraction possible later.
3. **The AI service is internal.** The API is its only legitimate caller,
   authenticated by a shared internal key.
4. **Authorisation is server-side.** Client-side role checks are UX only.
5. **Types are generated, one direction:** FastAPI → OpenAPI → TypeScript client
   and Dart models. Never hand-synced.
6. **No client ships a server-side credential.** `NEXT_PUBLIC_*` and anything in
   an APK is public.
7. **Slow work is queued.** Nothing a citizen waits on may block on an LLM.

## Evolving without a rewrite

Invariant 2 is the whole plan. Every module already has a defined interface;
extraction promotes that interface from a Python call to an HTTP call.

Extracting `notifications`:

1. `git mv services/api/app/modules/notifications services/notifications/app`
2. Wrap the existing `service.py` in a FastAPI router — the logic is unchanged
3. Swap the in-process import for a generated HTTP client with the same signatures
4. Give it its own tables and migration head
5. Add a Dockerfile, a compose entry and a CI workflow

**No caller changes**, because callers always went through `service.py`.

Predicted order, by real pressure: `notifications` (push volume) →
`problem-engine` (ranking saturates the API) → `auth` (government SSO) →
splitting `ai` into orchestration and GPU inference.

Do not do any of this now. The monolith is correct until something above
actually hurts.
