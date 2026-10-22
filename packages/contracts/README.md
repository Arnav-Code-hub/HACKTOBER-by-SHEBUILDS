# `@janmaang/contracts`

The API contract, **generated — never hand-written**.

```
services/api (FastAPI)
        │  make contracts
        ▼
openapi/openapi.json ──┬──► src/generated/api.ts   TypeScript types + client  → apps/web
                       └──► dart/                  Dart models                → apps/mobile
```

## Why generated

Hand-synced types drift, and they drift silently — the copy that is wrong is
never the one you are looking at. Generation gives cross-language type safety
with no shared runtime: Python stays the API's language, TypeScript the web's,
Dart the app's.

CI (`ci-contracts.yml`) regenerates on every change to `services/api` and fails
the build if the committed output is stale. A schema change therefore cannot
merge without its clients being updated in the same PR — which is the whole
argument for the monorepo in one sentence.

## Rules

- Never edit `src/generated/` or `dart/`. Run `make contracts`.
- Hand-written helpers go in `src/` alongside, not inside, the generated folder.
- Adding a field is backwards-compatible; removing or renaming one is not — say
  so in the PR description and update both clients in the same change.
