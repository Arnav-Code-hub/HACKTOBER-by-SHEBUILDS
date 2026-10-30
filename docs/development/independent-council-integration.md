# Independent AI Council integration

The council is a separate repository/service. JanMaang contains only contracts, authenticated transport, supervision, authorization and delivery state. It never imports council source or accesses the council SQLite store.

## Enable after acceptance

Apply Alembic revision 0005. Set COUNCIL_ENABLED=true, COUNCIL_URL to the private service origin, and COUNCIL_SERVICE_KEY to the same random 32+ character secret configured in the council's COUNCIL_SERVICE_KEY. Use TLS outside localhost. Service secrets never go to browsers. The integration rejects simulation reports by default; COUNCIL_ALLOW_SIMULATION=true is for an isolated acceptance environment only.

The institute assigns one active faculty member at its own institute/district to a team. Students then select a submission and supply findings plus evidence. Completed reports are advisory, do not change faculty grades, and are automatically available to current team students and the supervisor recorded when the assessment was requested. A later assignment change applies to future assessments only.

The worker starts with the API only when enabled. It claims outbox rows with PostgreSQL SKIP LOCKED; requests use the durable local assessment UUID as the council Idempotency-Key. Crashes and network failures replay the same upstream request rather than regenerate reports. Incomplete model reviews require a student's explicit retry. Delivery failures retry automatically after 60 seconds. Queued/running upstream work is polled every 10 seconds. The worker has no model credentials.

## Privacy and persistence

Every list, detail and PDF retrieval checks current institute/district and current student team membership or snapshot supervisor identity. Institute administrators can assign supervisors, but cannot retrieve project reports through this API. Faculty outside the assigned supervision cannot retrieve them even within the same institute.

Report JSON, the canonical council PDF (up to 8 MB), delivery timestamp, and idempotent in-app notifications are persisted in one PostgreSQL transaction. Available therefore means both report and PDF are durably accessible to faculty through JanMaang. PDFs are base64-wrapped only to reuse the existing authenticated JSON transport. No public artifact URLs are exposed.

Back up council_assessments together with the business database. The evidence snapshot and report are sensitive academic data. Do not reset demo data on a production database.

## APIs

All routes are under /api/v1/council and require the existing Firebase session.
- GET config: enabled flag.
- GET faculty: institute-scoped assignable faculty.
- GET/POST teams/{team_id}/supervisor: read/set the supervisor.
- POST submissions/{submission_id}/assessments: evidence payload and Idempotency-Key.
- GET assessments and GET assessments/{id}: scoped status/report.
- POST assessments/{id}/retry: student-only retry for incomplete/failed delivery.
- GET assessments/{id}/pdf: authenticated JSON {content_base64}; never publicly cached.

No migrations are run automatically. All integration stays disabled until the separate council passes live quality and authorization acceptance.

## Retry identity and evidence

Every explicit retry of an incomplete model assessment persists a new retry key.
The worker reuses that key if transport delivery is replayed; the independent
council durably deduplicates it even if the model failed again. Delivery-only
retries preserve the original completed assessment and never trigger model work.
Report details include the authorized immutable evidence snapshot; the viewer
numbers its lines so faculty can resolve PDF citations without external links.

## Verification on 30 October 2026

129 API unit tests, 144 frontend tests (one worker), TypeScript, ESLint, mypy,
Ruff and both import contracts passed. Four real PostgreSQL tests applied the
complete migration chain and checked private supervision/publication, concurrent
idempotency, delivery retry without a second submission, and transaction rollback
after notification inserts. Remote council calls were mocked; no production
database was used.

The independent service has 45 passing backend tests and browser-to-PDF acceptance.
Live Gemini acceptance and faculty calibration remain pending. The existing
configured model was rejected as retired, and replacement-model probes timed out.
Do not enable this feature based on offline simulation or mocked upstream results.
