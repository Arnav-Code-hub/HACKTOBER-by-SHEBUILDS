# Git workflow

**Trunk-based development with short-lived branches.** GitHub Flow, plus a hard
rule that a branch lives less than two days.

## Why not the alternatives

**Git Flow** exists to manage versioned releases of installed software. We deploy
continuously. It adds two merge steps and a permanent source of "did you branch
from develop?" confusion.

**Long-lived feature branches** produce a merge nobody can review and a conflict
nobody can resolve. Merge behind a feature flag instead.

## Rules

- `main` is always deployable and always green. Protected: no direct pushes,
  required status checks, linear history.
- **Squash merge only.** One feature, one commit on `main` — which makes
  `git bisect` and `git revert` trivial when something breaks forty minutes
  before a demo.
- Branch older than 2 days → split it, or merge it behind a flag.
- Never force-push `main`. `--force-with-lease` on your own branch only.

## Branches

`<type>/<scope>-<description>` — the scope makes blame legible in a monorepo:

```
feat/api-problem-dedup            fix/mobile-offline-sync-duplicate
refactor/web-role-guards          chore/ci-cache-uv
docs/adr-005-notification-split   test/ai-classification-eval
```

Types: `feat` `fix` `refactor` `chore` `docs` `test` `perf`
Scopes: `api` `ai` `web` `mobile` `infra` `ci` `contracts` `db`

## Commits and PRs

Because we squash-merge, **the PR title becomes the commit message**. Write it as
a Conventional Commit: `feat(api): cluster demands by geo proximity`.

- **Under ~400 lines.** A 2000-line PR gets rubber-stamped, which is the same as
  no review.
- **One approval required.** CI green is non-negotiable.
- **During the SIH sprint:** if no reviewer responds within 30 minutes and CI is
  green, self-merge and note it in the PR. A blocked queue at hour 30 is worse
  than an unreviewed refactor. **Never disable branch protection** — that is a
  different thing, and it is how secrets get committed.

## Before you push

```bash
make check   # exactly what CI runs, in the same order
```

If CI can fail on something you cannot reproduce locally, people stop trusting
CI. Report that as a bug in the pipeline.
