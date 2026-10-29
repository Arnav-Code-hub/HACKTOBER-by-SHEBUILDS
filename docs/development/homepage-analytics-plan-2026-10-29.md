# Homepage public analytics

User request: show overall complaint and resolution statistics on the website's
public homepage. Keep the existing visual design and earlier local changes.

## Implementation

- [x] Add anonymous `GET /api/v1/analytics/public` through the existing analytics
  router/service/repository. Reuse the public aggregate names from added-feature
  for report/case counts and status distributions. No new tables or migrations.
- [x] Count complaint status using the linked cluster status, matching the
  existing report/admin views. Exclude labelled demo reports and clusters.
  Return aggregate counts and latest status timestamp, never personal records.
- [x] Add a homepage component using the existing API origin, React Query, Zod
  and stat-card styling. Show total, open, citizen-resolved and not-accepted
  complaints, plus an expandable status breakdown and separate community-case
  counts. Fetch anonymously; include loading, retry and retained-data refresh.
- [x] Verify actual aggregate SQL using an isolated in-memory SQLite connection
  and the anonymous route through the test client. Docker is unavailable, so
  PostgreSQL integration coverage must be reported as not run.
- [x] Add component/API tests, regenerate OpenAPI/TypeScript contracts, run API
  and website checks, and inspect the local homepage. Do not deploy or merge the
  added-feature branch or its unrelated changes.

## Meaning of the counts

Complaints are individual reports; community cases group related reports.
Resolved complaints inherit `citizen_verified` from their linked case. Open
complaints exclude citizen-verified and rejected complaints. Genuine zero counts
are allowed; a failed request must not be rendered as zero or sample statistics.

## Verification

- API unit tests: 111 passed. Website tests: 131 passed.
- API lint, typing and import boundaries passed; website production build passed.
- Aggregate totals use one SQL statement for a consistent database snapshot.
- Read-only request against the configured Supabase database succeeded with genuine zero non-demo totals.
- Homepage inspected at desktop and phone sizes, including refresh and status breakdown.
- Isolated PostgreSQL integration tests not run: Docker unavailable. No deployment or push performed.
