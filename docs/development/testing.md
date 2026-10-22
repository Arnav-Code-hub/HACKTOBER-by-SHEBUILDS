# Testing

Tests live **with the code they test**. A top-level suite mirroring the whole
system rots, because nobody updates a test three directories from what they
changed. The one exception is E2E, which belongs to no single service.

| Layer | Location | Tool | Runs |
|---|---|---|---|
| API unit | `services/api/tests/unit/` | pytest | every PR |
| API integration | `services/api/tests/integration/` | pytest + testcontainers | every PR |
| API contract | `services/api/tests/api/` | pytest + httpx | every PR |
| AI unit | `services/ai/tests/` | pytest, **LLM mocked** | every PR |
| **AI evals** | `services/ai/evals/` | custom runner | **nightly + manual** |
| Web unit | colocated `*.test.tsx` | Vitest | every PR |
| Web E2E | `apps/web/e2e/` | Playwright | merge to main |
| Mobile unit/widget | `apps/mobile/test/` | flutter_test | every PR |
| Mobile integration | `apps/mobile/integration_test/` | integration_test | nightly |
| **System E2E** | `tests/e2e/` | Playwright + compose | merge + nightly |

## Evals are not tests

Tests assert deterministic behaviour. **Evals measure quality** against a golden
set: non-deterministic, slow, and they cost money. They never run on the PR path.

A prompt change without a re-run eval is not reviewable — attach the
before/after score table to the PR.

## What to test first

With limited time, in this order:

1. **Permission checks** — every role × endpoint. The worst security risk and
   the fastest thing to get silently wrong across nine roles.
2. **Offline sync and idempotency** on mobile — a retried sync must not create
   duplicate reports.
3. **Priority-score arithmetic** — it is the product's central public claim and
   must be reproducible.
4. **The four demo journeys** — report → cluster → rank → fund → verify.

Everything else can wait. Coverage percentage is not a goal; these four are.

## Keeping the PR gate fast

Target **under five minutes**. A slow gate is the single most common reason a
team starts bypassing branch protection. E2E, evals, image builds and mobile
release builds all run off the PR path deliberately.
