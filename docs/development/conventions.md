# Conventions

One cross-cutting rule: **a domain concept keeps the same word everywhere.**
See [the glossary](../product/glossary.md).

## Naming

| Thing | Convention | Example |
|---|---|---|
| Folders (all ecosystems) | `kebab-case` | `problem-statements/` |
| Python files | `snake_case.py` | `priority_service.py` |
| Dart files | `snake_case.dart` | `demand_repository_impl.dart` |
| React components | `PascalCase.tsx`, one per file | `ProblemCard.tsx` |
| Other TS files | `kebab-case.ts` | `api-client.ts` |
| Classes | `PascalCase` | `ProblemService` |
| Functions/vars — Python | `snake_case` | `compute_priority_score()` |
| Functions/vars — TS/Dart | `camelCase` | `computePriorityScore()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_PHOTO_COUNT` |
| Flutter shared widgets | `Jm` prefix | `JmStatusChip` |
| DB tables | `snake_case`, **plural** | `problem_statements` |
| DB columns | `snake_case` | `reporter_id`, `created_at` |
| DB join tables | `<a>_<b>`, alphabetical | `project_students` |
| DB indexes | `ix_` / `uq_` / `fk_` / `ck_` | `ix_problems_district_id_status` |
| API paths | `kebab-case`, plural nouns, no verbs | `GET /api/v1/problem-statements/{id}/projects` |
| Query params | `snake_case` | `?district_id=…&sort_by=priority_score` |
| JSON keys | `snake_case` | `{"priority_score": 8.4}` |
| Env vars | `UPPER_SNAKE_CASE`, prefixed when ambiguous | `AI_SERVICE_URL` |
| Branches | `<type>/<scope>-<description>` | `feat/api-problem-dedup` |

## Structure

- **Backend** — a module is `router · schemas · models · service · repository · tasks · events`.
  A module may import another's `service` and `schemas`; **never** its `models`
  or `repository`. Enforced by `import-linter` in CI.
- **Web** — `app/` is routing and layout only; logic lives in `features/`, named
  identically to the backend module.
- **Mobile** — feature-first with `data / domain / presentation`. Presentation
  never imports a datasource directly.
- **AI** — one folder per capability; prompts are files in `prompts/`, never
  string literals.

## Comments

Explain **why**, not what. A comment restating the code is noise that goes stale.
The comments worth writing are the ones recording a decision — why this approach
over the obvious one, what breaks if the order changes.
