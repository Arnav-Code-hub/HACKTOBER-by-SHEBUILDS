# 0002. PostgreSQL + PostGIS as the primary datastore

Date: 2026-09-06
Status: accepted

## Context

The app was built Firebase-first: Firestore, Storage and TypeScript Cloud
Functions, with Gemini called from `analyzeReport`. That was the right call for
a single-screen citizen app.

The platform now specified is not that. Nine role dashboards, leaderboards,
cross-entity analytics, funding ledgers, audit logs, and geographic clustering
of reports into ranked demands.

## Decision

**PostgreSQL 16 + PostGIS + pgvector** becomes the primary datastore, behind a
FastAPI modular monolith.

**Firebase is retained for exactly three things:** Auth (phone OTP), FCM push,
and Storage. These are commodity, and replacing them costs days for no demo
value.

## Consequences

**Easier.** Joins, aggregations and window functions — which is what nine
dashboards and a leaderboard actually are. Real geospatial queries instead of
geohash workarounds. `pgvector` puts duplicate-detection embeddings in the same
database as the rows they describe. Self-hostable, which a government deployment
will eventually require.

**Harder.** The mobile app's data layer must move from Firestore to HTTP. Local
development now needs Docker.

**Cheaper than it looks.** The existing mobile architecture already puts every
datasource behind a repository interface with a mock implementation
(`docs/architecture/mobile.md`). The migration swaps `*_repository_impl.dart`'s
datasource; the domain interfaces and every screen are untouched. This is a
datasource swap, not a rewrite — but it is still days, not hours.

## Alternatives considered

**Stay on Firestore.** Rejected. No joins, no aggregation beyond `count`, no
geospatial queries, and leaderboards require fan-out reads that get slow and
expensive. The wall arrives while building the *second* role dashboard.

**Migrate everything including Auth.** Rejected. Phone OTP for rural citizens is
genuinely hard to build well and carries zero demo value.

**Two datastores permanently.** Rejected as a target, but acknowledged as the
honest fallback if the sprint cannot absorb the migration: keep Firestore for
the citizen mobile flow, stand up Postgres for the web platform's relational
domain, and document a convergence plan. Two sources of truth for one concept is
a real cost, so this is a scheduling compromise, not an architecture.

## Consequence for Cloud Functions

`apps/mobile/firebase/functions` shrinks to Firebase-native triggers only.
`analyzeReport` moves to `services/ai`; `clusterDemand` and `computePriority`
move to the API's worker. AI logic in a TypeScript Function cannot share code
with a Python AI service and cannot run heavy pipelines.
