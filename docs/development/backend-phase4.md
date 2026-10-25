# Backend Phase 4 — funding, work orders, officer evidence, statements

Implemented on 25 October 2026 in the primary checkout on `test`, following
backend plan revision 3. Local evidence only: Firebase, Cloudinary, Supabase and
Render are not configured, so no hosted run has happened yet.

## Delivered

- **Assignable officers** — `GET /users?role=officer` lists active officers in
  the calling department's own district *and* department. Only departments can
  call it.
- **Funding** — `POST /clusters/{id}/fund` (idempotent). One transaction: the
  retry-key reservation, the conditional `prioritised → funded` change (which
  also checks that this department is responsible for the cluster's category
  in that district), the work order (round 1, the officer's instructions), the
  allocation in integer paise, and the audit entry. The officer must be active
  and in the same district and department (422). An exact retry returns the
  original 201; a different request for an already-funded cluster is 409; the
  database also allows only one allocation and one work order per cluster.
  Allocations are created through `funding.service`, keeping module boundaries.
- **Work orders** — `GET /work-orders?mine=true` for the assigned officer, with
  the anchor report's code, title and location and the allocated amount.
  `PATCH /work-orders/{id}` records progress notes; the first note moves
  `funded → in_progress`. Notes are refused (409) once completion is submitted.
- **Completion** — `POST /work-orders/{id}/complete` (idempotent) locks the
  cluster then the work order, attaches the officer's own unused completion
  photos (1–3) stamped with the current round, and moves the cluster to
  `awaiting_verification`. Earlier rounds' photos are kept. Refused (409)
  before work has started; another officer gets 404.
- **Evidence** — `GET /work-orders/{id}/evidence` for every assigned order,
  open ones included, so the officer sees the citizen's photo before taking
  theirs. `before` is the anchor report's earliest photo (or `null` — report
  photos are optional); `after` is the earliest completion photo of the round
  chosen by the shared `core.evidence.select` rule, with `after_round`.
  Visible to the reporter, the assigned officer, the responsible department,
  the district's Panchayat and gov admin, and super admins; 404 for others.
  `card_url` stays `null` until Phase 5.
- **Problem statements** — at the agreed `/statements` paths. Departments
  create drafts (optionally linked to a cluster they are responsible for, in
  their district) and publish them; publishing twice is harmless. Student,
  faculty, institute, industry and gov admin accounts read published
  statements in their district; a department also sees its own drafts; other
  departments' drafts never leave them; citizens, Panchayat and officers get
  403. A statement is never a work order.

## Decisions — 25 October 2026

**Which completion photo is the evidence** (open finding from the Phase 1
audit). Options: the newest photo, a chosen "primary" photo, or the earliest.
Choice: the earliest photo of the selected round (then by id). Reason:
deterministic, needs no extra field, and the endpoint and the Phase 5 card use
the same function. Trade-off: an officer cannot pick a better later photo.

**Reports without photos.** Report photos are optional, so `before` may be
`null`; the web evidence view says the citizen attached no photo rather than
showing a stand-in. The Flutter verification view (Phase 5) must accept the
same.

## Tests

`tests/integration/test_phase4_api.py` (14 tests, real PostgreSQL): officer
listing scope; funding records and audit; four concurrent exact retries all get
the original 201 with one allocation; four competing keys give one 201 and
three 409s; reused key with different data; officer and department scope
(422/403); invalid amounts; listing, notes, completion and replay; completion
photo rules and round stamping; completion before work starts; evidence before
and after completion and its access rules; statement read access, draft
privacy, publishing and cluster links. A unit test covers evidence selection
without a before photo.

## Fixes after the Phase 4–6 review — 25 October 2026

- **Stale completion.** `POST /work-orders/{id}/complete` now requires
  `expected_round` (part of the retry-key hash) and returns 409 unless it is the
  current round, checked under the work-order lock before any photo is
  attached. Before this, a second tab opened during round 1 could submit after
  the citizen returned the work, and its photos were filed as the round-2
  correction. The web officer form sends the round it shows.
- **Stranded assignments.** `PATCH /admin/users/{id}` returns 409 when the user
  is an officer with open work orders (`funded`, `in_progress`,
  `awaiting_verification`) and the change would remove their access, by role,
  district or department. Funding share-locks the officer row while checking
  it, and the admin change locks it for update, so a concurrent funding and
  demotion cannot both succeed.
- **Disabled accounts.** An administrator can correct a disabled account's role
  and scope; the scope is still validated (422), and the account stays
  disabled. Signing in still requires an active account.
- **Verify by a stranger.** `POST /work-orders/{id}/verify` from a citizen with
  no report in the cluster is 404, matching the verification view; a member
  reporter still gets 403.
