# JanMaang documentation

| Section | What's in it |
|---|---|
| [architecture/](architecture/) | System shape, [mobile internals](architecture/mobile.md), and the ADRs recording why |
| [api/](api/) | Conventions, auth, errors. Reference is **generated** — see below |
| [database/](database/) | Schema, ERD, migrations, PostGIS, seeding |
| [ai/](ai/) | Capabilities, prompts, evaluation, model choices, safety |
| [deployment/](deployment/) | Environments, runbook, rollback |
| [development/](development/) | Setup, workflow, conventions, troubleshooting |
| [product/](product/) | Roles, journeys, glossary, roadmap |
| [SOURCES.md](SOURCES.md) | Data provenance. The app renders this at `/method` |
| [STITCH_INVENTORY.md](STITCH_INVENTORY.md) | Design source inventory |

## Two rules that keep this alive

**API reference is generated, never hand-written.** It comes from the FastAPI
schema at `/docs`. Hand-written API docs are wrong within a week.

**Architectural decisions get an ADR.** One file per significant decision, dated,
with the alternatives that were rejected and why. A judge — or a maintainer in
six months — asking "why Postgres and not Firestore?" gets a reasoned answer
instead of a shrug.

## Start here

- New to the project → [development/setup.md](development/setup.md)
- Understanding the system → [architecture/overview.md](architecture/overview.md)
- Why is it built this way → [architecture/decisions/](architecture/decisions/)
- What do the roles mean → [product/roles.md](product/roles.md)
