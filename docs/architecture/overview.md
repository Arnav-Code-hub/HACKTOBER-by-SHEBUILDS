# System overview

The one-page version is [`ARCHITECTURE.md`](../../ARCHITECTURE.md) at the
repository root, including the component diagram and the seven invariants.
This page covers what does not fit there.

## Request paths

**Citizen reports a problem (mobile).** Report is written to the local Drift
database and an outbox row, so it exists offline immediately. On reconnect the
sync engine POSTs it with a client-generated UUID as an idempotency key. The API
persists it, then enqueues classification and clustering. The citizen sees the
report as `pending` the whole time — nothing in the capture path blocks on a
network call or on a model.

**Report is classified and clustered (worker).** The worker calls the AI service
for category, severity and an embedding; the API compares the embedding plus
geographic proximity plus category against existing clusters, and either attaches
the report or opens a new cluster. Cluster weight is a count of reports, not a
count of distinct sites — forty people reporting one handpump is one demand
carrying the weight of forty.

**Cluster is ranked (scheduled).** Five published factors — people affected,
infrastructure gap, equity index, severity, duration unaddressed — produce a
score, ranked within a district. The score breakdown is stored alongside the
score, because the product's central claim is a ranking that can be defended in
public rather than a number.

**Department publishes a statement (web).** A ranked cluster becomes a Problem
Statement students can build against. Statement generation is queued, not
synchronous — it is an LLM call a person is not sitting and waiting on.

**Citizen verifies the fix (mobile).** Geotag and timestamp are validated
server-side, then the status advances and the ledger entry becomes public. This
is the only path that closes the loop, and it is deliberately citizen-driven.

## Where each concern lives

| Concern | Home | Not |
|---|---|---|
| Schema and DDL | `services/api/app/migrations` | anywhere else |
| Business rules | `services/api/app/modules/*/service.py` | the clients |
| Authorisation | `services/api/app/core/permissions.py` | web middleware |
| Prompts | `services/ai/prompts/` | inline strings |
| Slow work | `services/api/app/modules/*/tasks.py` | request handlers |
| Design tokens | `packages/tokens/src/tokens.json` | duplicated per app |
| Cross-language types | generated into `packages/contracts` | hand-synced |

## Why there is no notification service

Notifications are a module in the API, and the worker is the API's own image with
a different command. Both would be separate deployments in a microservice
design, and both would need the same models, config and database session — so
splitting them buys nothing and costs a duplicate dependency set plus a
serialisation boundary. `notifications` is the first realistic extraction
candidate later; see [`ARCHITECTURE.md`](../../ARCHITECTURE.md#evolving-without-a-rewrite).

## Further reading

- [Decisions](decisions/) — why, with the alternatives that were rejected
- [Mobile internals](mobile.md) — the citizen app's layering and data model
- [Roles](../product/roles.md) · [Glossary](../product/glossary.md)
