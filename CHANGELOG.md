# Changelog

Notable changes to JanMaang. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed — repository restructured into a monorepo

- Flutter citizen app moved from the repository root to `apps/mobile/`
- Added `apps/web` (Next.js, nine role dashboards in one application)
- Added `services/api` (FastAPI modular monolith) and `services/ai` (internal AI service)
- Added `packages/` — generated API contracts, design tokens, UI primitives, shared config
- Added `infrastructure/`, `scripts/`, `tests/e2e/` and ten GitHub Actions workflows
- `make` is now the single command surface across pub, pnpm and uv

Decisions recorded in [`docs/architecture/decisions/`](docs/architecture/decisions/):
one repository (0001), Postgres over Firestore (0002), a separate AI service
(0003), a single web app (0004).

### Fixed

- Removed an unnecessary `characters` import in `home_screen.dart`
- Applied `dart format` across `apps/mobile` so the CI format gate passes
- Added a missing block around a single-statement `if` in `demands_repository_mock.dart`

### Known issues

- Five widget tests in `apps/mobile/test/widget/` assert on UI copy the screens no
  longer render. Pre-existing — they fail at `a13bd3a` too, before the restructure.
