# JanMaang

A civic demand-to-budget platform. A citizen reports a local need in their own
voice; AI structures it; identical reports are clustered so forty people asking
for the same handpump count as one demand with the weight of forty; the demand
is ranked against every other demand in the district on five published factors;
government funds down the ranked list; and the citizens who reported it decide
whether it was actually fixed.

**Speak → Analyze → Cluster → Prioritise → Fund → Execute → Citizen Verify**

## Quickstart

```bash
git clone https://github.com/<org>/janmaang.git
cd janmaang
make setup     # tools, .env files, dependencies, database, seed data
make dev       # postgres, redis, api, worker, ai, web
```

- web — <http://localhost:3000>
- API docs — <http://localhost:8000/docs>
- AI docs — <http://localhost:8001/docs>
- citizen app — `make mobile`

`make help` lists every target. `make doctor` diagnoses a broken environment.
Full instructions: [docs/development/setup.md](docs/development/setup.md).

## The repository

One repository, three ecosystems, one command surface. Flutter uses pub,
TypeScript uses pnpm workspaces, Python uses uv — and `make` sits in front of all
three so there is one interface to learn. See
[ADR 0001](docs/architecture/decisions/0001-one-repository.md) for why.

```
apps/
  mobile/          Flutter — the citizen app (offline-first)
  web/             Next.js — nine role dashboards in one application
services/
  api/             FastAPI modular monolith. Owns the schema.
                   The worker is this same image with a different command.
  ai/              One internal AI service, modular by capability. Stateless.
packages/
  contracts/       Generated API contract → TypeScript client + Dart models
  tokens/          Design tokens → CSS variables + Dart constants
  ui/              React primitives (web only)
  config/          Shared lint/TS/Tailwind presets
infrastructure/    Docker, Terraform, Kubernetes, ops scripts
docs/              Architecture, ADRs, API, database, AI, deployment, product
scripts/           setup · doctor · contract generation
tests/e2e/         Cross-service journeys
```

## Architecture in four decisions

| | Decision | Why |
|---|---|---|
| [0001](docs/architecture/decisions/0001-one-repository.md) | One repository, polyglot, no monorepo tool | A contract change is one PR, validated end-to-end |
| [0002](docs/architecture/decisions/0002-postgres-over-firestore.md) | Postgres + PostGIS primary; Firebase for Auth/FCM/Storage | Nine dashboards and a leaderboard are joins and aggregations |
| [0003](docs/architecture/decisions/0003-separate-ai-service.md) | One separate AI service, modular by capability | ML deps, 2–30s calls and crash isolation |
| [0004](docs/architecture/decisions/0004-single-web-app.md) | One web app with role-based routes | Nine apps means nine auth implementations |

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Short version: branch from `main`,
keep it under two days and 400 lines, run `make check`, open a PR.

---

A civic demand-to-budget platform. A citizen reports a local need in their own
voice; AI structures it; identical reports are clustered so forty people asking
for the same handpump count as one demand with the weight of forty; the demand
is ranked against every other demand in the district on five published factors;
government funds down the ranked list; and the citizens who reported it decide
whether it was actually fixed.

**Speak → Analyze → Cluster → Prioritise → Fund → Execute → Citizen Verify**

## The map

Issues are plotted at their coordinates and **aggregated by location**: forty
citizens reporting the same handpump become one pin carrying the weight of
forty. Concentration is ranked across four tiers — green, amber, orange, red —
taken directly from the five colour bars under the logo wordmark, so the map
legend and the brand mark are the same palette.

Colour is never the only signal. Pin diameter (34 → 64px), ring weight and the
count badge all move with the tier, so the ranking survives greyscale and
colour-blindness. Only the critical tier pulses; animating every marker would
make the map unreadable. Nearby sites cluster while zoomed out and resolve into
individual pins past zoom 14, with cluster weight measured in total reports
rather than number of sites.

## Data transparency

`docs/SOURCES.md` is the source of truth for provenance, and the app renders it
at `/method`: every dataset, its licence, what it feeds, what was rejected and
why, and the two landmines that shaped the product.

Every seeded record is labelled. A provenance line — *"Synthetic rural ·
Approximate location"* — sits beside the figures it explains, and tapping it
opens the dataset, its licence and the "realistic, not real" caveat.

**No SLA or time-to-resolution metric appears anywhere.** The BBMP grievance
schema carries a grievance date and a status string but no closure timestamp,
so that number is not computable and would have to be invented. Supported
metrics — reports by category, ward, quarter, status and volume — are used
instead.

## Design provenance

Every screen is built from the Stitch project *JanMaang Civic Intelligence
System* (`projects/5610348960166970948`). The colour roles, type scale, spacing,
radii and elevation recipe in `lib/core/theme/` are transcribed from that
design system rather than approximated — see
[docs/STITCH_INVENTORY.md](docs/STITCH_INVENTORY.md) for the screen-by-screen
mapping and the full token table.

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Citizen app | Flutter · Riverpod · go_router · flutter_map | Offline-first. See [apps/mobile](apps/mobile/README.md) |
| Web platform | Next.js · TypeScript · React Query | One app, nine role route groups |
| API | FastAPI · SQLAlchemy · Alembic | Modular monolith; owns the schema |
| Worker | ARQ | Same image as the API, different command |
| AI | FastAPI · Gemini | One internal service, modular by capability |
| Data | PostgreSQL 16 · PostGIS · pgvector | Geo clustering, ranking, dedup embeddings |
| Cache / queue | Redis | |
| Identity, push, files | Firebase Auth · FCM · Storage | Retained deliberately — see [ADR 0002](docs/architecture/decisions/0002-postgres-over-firestore.md) |

Design tokens are generated from one JSON source into both CSS variables and
Dart constants (`packages/tokens`), so the five-tier density palette cannot
drift between the map legend and the wordmark.

## Checks

```bash
make check    # lint, typecheck and tests across every ecosystem — what CI runs
make test     # tests only
make lint     # lint only
```

Per-ecosystem: `make test-api`, `make test-ai`, `make test-web`, `make test-mobile`.

## Security

No server-side credential ships in any client. The Gemini key lives in the AI
service, reachable only through the API, which is the AI service's sole
legitimate caller; ranking, clustering, funding and verification are all
server-write-only. Secrets are scanned by gitleaks in a pre-commit hook and again
in CI. See [SECURITY.md](SECURITY.md).

## Component documentation

| | |
|---|---|
| [apps/mobile](apps/mobile/README.md) | Citizen app — running it, mocks, brand assets, platform status |
| [docs/development/setup.md](docs/development/setup.md) | Full local setup |
| [docs/development/workflow.md](docs/development/workflow.md) | Branching and PR rules |
| [docs/product/roles.md](docs/product/roles.md) | The nine roles and the permission matrix |
| [docs/product/glossary.md](docs/product/glossary.md) | Demand vs Cluster vs Problem Statement vs Project |
| [docs/SOURCES.md](docs/SOURCES.md) | Data provenance — rendered by the app at `/method` |
