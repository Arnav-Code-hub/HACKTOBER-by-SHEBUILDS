# Backend Phase 3 — Panchayat, clusters and ranking

Implemented in the OneDrive checkout on branch `test`, after Phase 2 and the CI
fix at `2aadba7`. This is local implementation evidence. Firebase, Cloudinary,
Supabase and Render are not configured, so the Phase 2 hosted gate and the live
multi-account browser demonstration are still pending.

## Delivered

- District-scoped report queues and staff detail reads, preserving citizen
  ownership. Status filtering uses effective cluster status, so grouped reports
  disappear from the `verified` queue. Pagination retains the existing bounds.
- Panchayat validation/rejection and explicit cluster confirmation using the
  shared row-locked transition helper. Rejection needs a visible reason. Every
  transition saves its timestamp and audit entry in the same transaction.
- Suggestions use category, district and Python great-circle distance from the
  cluster anchor. The assignment write enforces the same radius. No automatic
  merging. A report cannot join a second cluster or a completed repair.
- Explicit citizen support with a unique `(cluster_id, user_id)` constraint and
  `ON CONFLICT DO NOTHING`; only a new row writes a support audit event. Ranking
  deduplicates the union of member reporters and explicit supporters. Multiple
  reports by one citizen remain one person's support.
- Computed five-factor ranking, score breakdowns, neutral/default provenance,
  deterministic tie-breaking, and matching ranking fields in citizen report
  reads. SQL aggregates membership and support independently to prevent joined
  rows multiplying counts. One query obtains the ranking inputs; computation
  and sorting happen in Python for this bounded prototype.
- Official gap/equity assessments accept only finite JSON numbers in 0–100.
  The responsible department, district government admin or super admin may
  update them. The audit records previous and new inputs; defaults become
  official only after the complete assessment is saved.
- OpenAPI and generated TypeScript contracts include the new endpoints. Existing
  web forms and Dart report mappings already understand the returned shapes;
  their source code does not need a redesign for this phase.

## Endpoint coverage

- `GET /api/v1/reports?status=reported|verified`
- `GET /api/v1/reports/{id}` for authorized staff as well as the reporter
- `POST /api/v1/reports/{id}/validate`
- `GET /api/v1/reports/{id}/cluster-suggestions`
- `POST /api/v1/reports/{id}/cluster`
- `POST /api/v1/clusters/{id}/support`
- `GET /api/v1/clusters/ranked`
- `PATCH /api/v1/clusters/{id}/inputs`

No migration or dependency change was necessary: Phase 1 already created the
tables, constraints and the authoritative cluster execution status.

## Decisions — 24 October 2026, owner: Codex

**Duplicate people in community support.** Options: add report/support counts,
or deduplicate citizen identities across both. Choice: SQL `UNION`, followed by
grouping per cluster. Reason: the reporter can also explicitly support and can
submit multiple member reports. Trade-off: aggregation costs more than a stored
counter; for the demo it avoids drift and is recomputed on read. Evidence:
concurrent member/support requests and repeated support produce one count per
citizen.

**Category radii.** Options: one radius or the plan's 100/500 metre split.
Choice: 100 metres for point categories, 500 for roads and sanitation (including
drains). Reason: the existing enum has no separate drain subtype. Trade-off:
all sanitation cases use the wider suggestion radius; human confirmation is
still required. Evidence: the same 333 metre separation is refused for water
and accepted for roads/sanitation, on the write as well as in suggestions.

**Cluster severity.** Options: first report, mean severity, or maximum validated
member severity. Choice: maximum. Reason: another validated report must not
dilute an urgent member. Trade-off: an incorrect validation can overstate
severity. The current Panchayat action confirms the displayed report fields;
incorrect classifications must be declined and resubmitted until an editing
form is built. Evidence: a critical member changes the cluster severity factor
to 100; an unclustered citizen suggestion never enters the score.

**Read scope.** Choice: district for Panchayat/oversight and partner ranked
lists, additionally category responsibility for department/officer reads.
Reason: the plan requires department as well as district boundaries.
Trade-off: a department sees ranks within its permitted categories, while the
citizen sees the district ranking. Evidence: another district is 404; a
department without category responsibility receives an empty ranked list.

**Ranking/storage.** Choice: compute on read with no Redis, worker or stored
score snapshots, as specified by revision 3. Confirmed clusters remain in the
list through their lifecycle, with their actual status. Trade-off: this is a
bounded demonstration implementation, not a large geographic search service.

## Verification

New automated cases cover the published formula, age limits, provenance,
distance/date-line behavior, strict input validation, queues, rejection,
status/timestamp/audit agreement, competing validations and cluster assignments,
concurrent member/support actions, unique support counts, highest validated
severity, stable ranking ties, district/department boundaries and rollback on
audit failure. All use real isolated PostgreSQL for persistence/concurrency;
Firebase and Cloudinary are test doubles at their provider boundaries.

Run from `services/api`:

```powershell
uv run pytest --cov=app --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run lint-imports
```

Docker must be running for PostgreSQL testcontainers, or supply an explicitly
dedicated `TEST_DATABASE_URL`. Tests never fall back to an application database.
Local verification: **178 backend tests passed** against PostgreSQL 16,
including 38 new Phase 3 cases. Four pre-existing deprecation warnings remain.
Ruff lint/format, strict mypy, and both import-linter contracts passed. The
generated TypeScript contracts also passed their type check.
The exported OpenAPI exactly matches the CI export. After restoring locked
workspace dependencies and generating local Next.js route types, the web app's
TypeScript check passed as well. No frontend source, lockfile or migration was
changed for that environment setup.

## Live walkthrough — pending account setup

Follow [Phase 2 setup](backend-phase2.md) first, provision the citizen, Panchayat
and department Firebase accounts, and seed their real UIDs. Run the API and both
frontends with their live configuration.

1. Citizen submits a report with a real approved image.
2. Panchayat refreshes the validation queue, inspects the image and fields, and
   validates it. Citizen Track now says Panchayat validated.
3. Panchayat reviews same-category suggestions and explicitly chooses one or
   starts a new cluster. The report leaves the clustering queue.
4. Citizen refreshes Track/detail and sees cluster status, rank, unique community
   support and the five labelled score factors.
5. Department refreshes the ranked list and saves a gap/equity assessment. The
   score changes; the two default labels clear and an audit row is persisted.
6. Restart the API and repeat reads. Confirm validation, membership, support and
   official inputs survive. Funding and officer execution remain Phase 4 work.

There is no new citizen support button in this phase: the backend endpoint is
ready, and confirmed citizen report membership already contributes support.
The full browser journey remains unverified until real accounts are available.

## Audit fixes — 25 October 2026

Applied after the Phase 2/3 audit, before Phase 4 builds on ranking:

- **Report channels.** The citizen app starts reports by `text`, `voice`,
  `photo` or `location`; the API accepted only the first two, so reports begun
  from the Home screen's Photo or Location buttons were refused (422). The
  schema and the database check (migration `0003`) now accept all four.
- **`district_name` on `GET /users/me`.** The citizen app shows it as the
  account's location; it was missing.
- **Revocation checks.** Token signatures are still verified on every request;
  the account's disabled/revoked state is fetched from Firebase at most once a
  minute per user instead of on every request. Disabling the JanMaang profile
  in the database still takes effect immediately.
- **Only open demand is ranked.** `GET clusters/ranked` and report ranks cover
  `prioritised` clusters only, so a finished repair can no longer hold a top
  place or inflate "ranked N of M". Community support stays visible after
  funding. The citizen app explains that funded problems have left the ranking.
- **Demo labels.** In score breakdowns only seeded or neutral-default gap and
  equity inputs are labelled demo values; support, severity and age are
  computed from recorded data.
- **District-filtered aggregates.** Cluster summaries filter by district inside
  each aggregate instead of scanning every district first.
