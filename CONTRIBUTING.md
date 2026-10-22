# Contributing to JanMaang

## Setup

```bash
make setup    # idempotent — re-run it whenever your environment breaks
make dev
```

See [docs/development/setup.md](docs/development/setup.md). `make doctor`
diagnoses problems.

## The loop

```bash
git switch -c feat/api-problem-dedup
# ... work ...
make check        # exactly what CI runs, in the same order
git push -u origin feat/api-problem-dedup
gh pr create
```

## Branches

`<type>/<scope>-<description>` — the scope makes blame legible in a monorepo.

```
feat/api-problem-dedup       fix/mobile-offline-sync-duplicate
refactor/web-role-guards     docs/adr-005-notification-split
```

Types: `feat` `fix` `refactor` `chore` `docs` `test` `perf`
Scopes: `api` `ai` `web` `mobile` `infra` `ci` `contracts` `db`

**A branch lives less than two days.** Older than that, split it or merge it
behind a feature flag.

## Pull requests

We **squash-merge**, so the PR title becomes the commit message on `main`. Write
it as a Conventional Commit: `feat(api): cluster demands by geo proximity`.

- **Under ~400 lines.** A 2000-line PR gets rubber-stamped, which is the same as
  no review.
- **One approval**, and CI green — non-negotiable.
- During the SIH sprint, if no reviewer responds in 30 minutes and CI is green,
  self-merge and note it in the PR. **Never disable branch protection.**

The PR template lists the checks. The ones people forget:

- **API change?** run `make contracts` and commit the generated output — CI fails
  otherwise, by design
- **Schema change?** include the migration, and make sure it applies to an empty
  database
- **Prompt change?** paste before/after eval scores
- **New env var?** add it to the relevant `.env.example` with a comment

## Where code goes

| Change | Where |
|---|---|
| Citizen app feature | `apps/mobile/lib/features/<feature>/` |
| Web dashboard screen | `apps/web/src/app/(app)/<role>/` + `src/features/<domain>/` |
| API endpoint | `services/api/app/modules/<module>/` |
| Background job | `services/api/app/modules/<module>/tasks.py` |
| AI capability | `services/ai/app/capabilities/<capability>/` |
| Prompt | `services/ai/prompts/<capability>/<task>.jinja` |
| Type shared by web and mobile | it is **generated** — change the API schema |
| Colour or spacing | `packages/tokens/src/tokens.json` |
| Architectural decision | a new ADR in `docs/architecture/decisions/` |

## The rules that are actually enforced

**Backend module boundaries.** A module may import another module's `service.py`
and `schemas.py`. It may **never** import another's `models.py` or
`repository.py`. `import-linter` fails CI on violation. This is what keeps a
module extractable into its own service later without touching a caller.

**Generated code is never hand-edited.** `packages/contracts/src/generated/`,
`packages/tokens/dist/`. Run the generator.

**Secrets never enter the repository.** gitleaks runs pre-commit and in CI. If
you commit a key: rotate it first, then rewrite history. Removing it in a later
commit does not un-leak it.

**Authorisation is server-side.** Web middleware and hidden buttons are UX. Every
protected read and write is authorised by the API.

## Conventions

[docs/development/conventions.md](docs/development/conventions.md). The one that
matters most: **a domain concept keeps the same word everywhere** —
`problem_statement` / `ProblemStatement` / `problem-statements` /
`problemStatement`. See the [glossary](docs/product/glossary.md).

## Questions

Something unclear or undocumented is a bug in the docs. Open an issue, or fix it
in the PR you are already writing.
