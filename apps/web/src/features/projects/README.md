# `projects`

Mirrors `services/api/app/modules/`. Same vocabulary on both sides of the wire.

- `components/` — presentational pieces for this domain
- `hooks/` — React Query hooks wrapping the generated API client
- `api.ts` — typed calls via `@janmaang/contracts`
- `schemas.ts` — client-side form validation (zod)

Business rules live in the API. A copy here will drift, and the copy is the one
that will be wrong.
