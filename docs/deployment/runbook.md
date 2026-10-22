# Runbook

## Deploy to staging

Automatic on merge to `main`. Nothing to do.

## Deploy to production

1. Confirm the SHA is healthy in staging
2. Actions → **Deploy · production** → Run workflow → paste the SHA
3. Approve the `production` environment gate
4. Watch the smoke test at the end of the job

Production **promotes an image already built and verified in staging**. It never
rebuilds, so what ships is byte-identical to what was tested.

## Rollback

**Code only** — safe:

```bash
bash infrastructure/scripts/rollback.sh
```

**The deploy included a migration** — redeploying the old image will not undo a
schema change. Restore from the pre-deploy backup:

```bash
bash infrastructure/scripts/restore.sh <pre-deploy-dump>
```

This is why `backup.sh` runs before every production migration, and why additive
migrations are preferred: add a column, backfill, drop it a release later.

## Incidents

### API returning 5xx

```bash
docker compose logs --tail=200 api        # or the platform's log view
curl -fsS https://<host>/health
```

Most common causes, in order: a migration that did not run; a missing environment
variable after a config change; the database connection pool exhausted by a slow
query.

### AI features failing, everything else fine

Expected and designed for — AI failures must degrade gracefully. Check the AI
service's health, then `LLM_API_KEY` and the daily token budget: calls are
refused once `DAILY_TOKEN_BUDGET` is exceeded, which looks like a broken feature
but is the cost guardrail working.

Reports must still submit while classification is down. If they do not, that is
a bug in the API, not in the AI service.

### Push notifications not arriving

Check FCM credentials, then the worker — notifications are queued, so a stalled
worker looks exactly like broken push. `docker compose logs worker`.

### Database slow

Check for a missing index. Every index belongs in a migration; one applied by
hand in psql exists on one machine and nowhere else, which is the classic "fast
in dev, times out in the demo" failure.

## Before a demo

```bash
make doctor        # environment sanity
make reset-db      # clean, migrated, seeded — local only
```

Confirm the four demo journeys pass: report → cluster → rank → fund → verify.
