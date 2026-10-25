# 0001. One repository, polyglot, tool-light

Date: 2026-09-06
Status: accepted

## Context

JanMaang spans a Flutter citizen app, a TypeScript web platform with nine role
dashboards, a Python API, Python AI services, and infrastructure. The team is
5–7 developers building through a hackathon with rapid iteration and a possible
future government deployment.

## Decision

**One GitHub repository**, with per-ecosystem package managers and no
cross-ecosystem monorepo tool:

- `apps/web` + `packages/*` → pnpm workspaces
- `apps/mobile` → pub
- `services/api`, `services/ai` → uv, with **separate** virtualenvs
- everything → `make` as the single command surface

## Consequences

**Easier.** A contract change is one PR that CI validates end-to-end. One clone,
one `make setup`. `git bisect` covers the whole system. One version means one
working system — no skew between a deployed API and an installed APK.

**Harder.** CI must be path-filtered or every push builds everything. Three
package managers coexist, which needs documenting. Everyone can see everything —
acceptable at this size, revisit with external contributors.

**Accepted cost.** The repository must stay cloneable: no APKs, no model
weights, no datasets in git. `.gitignore` enforces this.

## Alternatives considered

**Separate repositories per component.** Rejected: the coordination cost lands
squarely on our most common change. A field added to the problem payload touches
the API, the AI scorer, the web dashboard and the Flutter model — four repos,
four PRs, no atomic merge, and on demo day someone forgets one. Access control
and CI cost, the real arguments for multirepo, only bite at 10–50× this team.

**Hybrid (shared backend repo + separate clients).** Rejected as the worst of
both: it pays multirepo's coordination cost *and* monorepo's discipline cost, in
exchange for a security boundary we do not need.

**Nx or Turborepo as the primary orchestrator.** Rejected. Their value is a
computed task graph across JavaScript packages; this repo is ~40% Dart and ~35%
Python, which they handle only through community plugins we would maintain
ourselves. One Git repository is not the same as one build system. Turborepo may
be added for the TypeScript subtree alone when web build time exceeds ~60s.

## When to revisit

Split a component out when **two** of these hold: separate release cadence,
separate on-call owner, separate security boundary, no shared code. Today none
do. The first realistic candidate is `apps/mobile`, once app-store review
cadence diverges from daily API deploys — cheap, because it depends only on
`packages/contracts`.
