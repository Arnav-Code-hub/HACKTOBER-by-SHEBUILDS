# Backend implementation plan (prototype)

Revision 3. Revision 2 added atomic idempotency and state changes, an
explicit verification round, department and audit scope, completion evidence
by round, statement read access, deployment details, and per-phase tests.
Revision 3 adds: one authoritative execution status, one evidence-selection
function shared by the endpoint, card and verification view, database-backed
helper tests moved to Phase 1, a reset guard that matches username, host,
port and database (the Supabase pooler identifies a project only by its
username), and separate retry and competing-request funding tests.

**Target:** [`docs/api/day1-frontend-contract.md`](../api/day1-frontend-contract.md),
which both frontends already call.
**Stack:** one FastAPI service, Supabase Postgres, Firebase Auth, Cloudinary,
Gemini. No Redis, worker, separate AI service or PostGIS.
**Starting point:** every API module is a placeholder; no tables, migrations
or authentication. Only `app/shared/enums.py` (the agreed statuses) is real.

| Phase | Delivers | Frontend that comes alive | Effort |
|---|---|---|---|
| 0 | Infrastructure, shared transaction helpers | — | ½ day |
| 1 | Data model, migration, seed | — | ½–1 day |
| 2 | Auth, media, citizen reports, **first deploy** | Flutter: sign-in, Report, Track | 1 day |
| 3 | Panchayat validation, clusters, ranking | Web: Panchayat, ranked list | 1 day |
| 4 | Funding, work orders, officer evidence, statements | Web: Department, Officer | 1 day |
| 5 | Citizen verification, Cloudinary evidence | Flutter: Verify; evidence card | 1 day |
| 6 | Student, institute, faculty, CSR, admin | Web: remaining five pages | ½–1 day |
| 7 | AI suggestion (optional) | Flutter: suggested fields | ½ day |
| 8 | Integration, hardening, demo readiness | Whole journey | ½ day |

Phases 0–5 are the demonstration journey. Every phase ships its own
acceptance tests; Phase 8 reruns and integrates them.

Implementation progress (25 October 2026): code for Phases 0–7 is implemented
locally. Implementation notes are in [backend-phase4.md](backend-phase4.md),
[backend-phase5.md](backend-phase5.md), [backend-phase6.md](backend-phase6.md)
and [backend-phase7.md](backend-phase7.md).
The Phase 2 provider/deployment gate
and Phase 5 hosted verification gate remain pending account setup. Continuing
local development does not mark either hosted gate as passed.

## Cross-cutting rules (apply from Phase 0)

**Idempotent writes.** Table `idempotency_keys(user_id, operation, key,
request_hash, status_code, response_json, created_at)` with a **unique
constraint on `(user_id, operation, key)`**. A write runs in one transaction:

1. Insert the key row first (`INSERT … ON CONFLICT DO NOTHING RETURNING`).
   If it already exists: same `request_hash` → return the stored response
   (waiting on the row lock if the first request is still in flight);
   different hash → 409.
2. Perform the business write and its audit event.
3. Store the response on the key row and commit — all or nothing.

**Conditional state changes.** Every transition is
`UPDATE … SET status = :to WHERE id = :id AND status = :from [AND round = :n]
RETURNING …` or runs under `SELECT … FOR UPDATE`. Zero rows → 409. Keys
identify requests; they never stand in for these preconditions.

**Funding semantics.** Same key + identical payload → the original success.
Any other request for an already-funded cluster → 409 (unique
`allocations.cluster_id` backs this up).

**One authoritative execution status.** The **cluster** owns the public
lifecycle from `prioritised` onward: `clusters.status` and
`clusters.status_changed_at` are the only copies. `work_orders` has **no
status column**; a work order's status in API responses is its cluster's
status (one work order per cluster). A report's own `status` covers only
`reported`, `verified` and `rejected`; once clustered, its effective status is
the cluster's. One function, `lifecycle.effective_status(report)`, produces
the status and `status_changed_at` every endpoint returns.

Every transition — validate, cluster, fund, first update, complete, verify —
goes through one function, `lifecycle.transition(session, record, from_, to,
*, actor, reason, round=None)`, which performs the conditional update, sets
`status_changed_at`, and writes the audit event in the caller's transaction.
No endpoint updates a status column directly. This is what guarantees that
completing a work order makes the cluster `awaiting_verification`, and so
shows the citizen the verification prompt.

**One evidence selection.** `evidence.select(work_order)` returns `before`,
`after`, `after_round` and the verdict label, and is the only source for
`GET work-orders/{id}/evidence`, `GET reports/{id}/verification` and the
evidence card:

| Cluster status | `after` | Card verdict text |
|---|---|---|
| `funded`, or `in_progress` on round 1 | `null` (no card) | — |
| `awaiting_verification` | current round's completion | "Awaiting citizen verification" |
| `citizen_verified` | current round's completion | "Citizen verified" |
| `in_progress` on round > 1 | the **previous** (returned) round's completion | "Round N · returned for correction" |

**Audit.** `log_event(session, actor, action, entity, before, after, reason,
district_id)` writes in the caller's transaction. `district_id` is the
affected record's district (nullable for platform events) and is what admin
audit queries filter on.

**Scope.** Out-of-scope records are 404; permitted-but-wrong-state actions are
409; wrong role is 403. Department scope is district **and** department.

**Documented decisions** (record in Notion and the contract):
cluster radius 100 m for point assets (water points, lights) and 500 m for
roads and drains; the reporter of a cluster's anchor (first) report verifies
its repair; a category maps to exactly one responsible department per
district.

## Phase 0 — Infrastructure

1. Config (`app/core/config.py`): `redis_url` optional and no Redis
   connection at import (`app/core/redis.py`); Cloudinary and Gemini
   settings replace `storage_*`; document only secrets the runtime consumes;
   environments stay `development | staging | production` —
   **deploy with `ENVIRONMENT=staging`** (`demo` is rejected).
2. Dependencies: add `cloudinary` and `google-genai` with `uv add`, and
   commit the updated `uv.lock`.
3. `app/main.py`: `/health` stays public; CORS with exact origins, allowing
   `Authorization` and `Idempotency-Key`; one `{"detail": …}` error format with
   short human-readable messages; only used routers mounted.
4. Permissions (`app/core/permissions.py`): add `WORKORDER_ASSIGN`,
   `WORKORDER_UPDATE`, `CLUSTER_CONFIRM`, `STATEMENT_READ_PUBLISHED`; give
   Institute `PROJECT_APPROVE`; remove `PROBLEM_VERIFY` from Panchayat and
   Officer.
5. Shared helpers: the idempotency, conditional-transition, audit and scope
   helpers above.
6. Alembic wiring: make `migrations/env.py` import each module's `models`
   explicitly (model discovery itself is verified in Phase 1).
7. Test fixtures (`tests/conftest.py`): Postgres testcontainer, migrations
   applied, `httpx` client, per-role principal overrides, fake Cloudinary and
   Gemini.

The idempotency, transition and evidence helpers get their **interfaces** and
pure unit tests here (request hashing, the transition table, the
evidence-selection rules on plain objects). Their database-backed tests move
to Phase 1, where the tables they use are created.

**Exit:** the API starts without Redis with `ENVIRONMENT=staging`; the test
fixtures start Postgres and apply the (still empty) migration chain; the pure
helper tests pass.

## Phase 1 — Data model, migration, seed

**Tables** (UUID ids, timestamps):

| Area | Tables | Key constraints |
|---|---|---|
| Identity | `organizations` (district / department / institute / industry), `department_categories` (department, district, category), `users` (firebase_uid, role, scope ids, is_active) | `firebase_uid` unique; one responsible department per (district, category) |
| Reports | `reports` (…, `status`, `status_changed_at`, `cluster_id`, `rejection_reason`), `media_assets` (owner, public_id, kind, format, bytes, report_id, work_order_id, **`round`**) | report `code` from a sequence; `public_id` unique |
| Clusters | `clusters` (district, category, anchor_report_id, status, `status_changed_at`, gap, equity, `inputs_are_demo`), `supports` | (cluster, user) unique |
| Government | `work_orders` (cluster, department, district, officer, round, notes, instructions — **no status**; see "One authoritative execution status"), `allocations` (paise), `verifications` (work_order, round, citizen, verdict, comment) | `allocations.cluster_id` unique; `work_orders.cluster_id` unique; (work_order, round) unique on verifications |
| Partners | `problem_statements` (department owner, status), `teams`, `team_members`, `submissions`, `reviews`, `sponsorships` | (submission, reviewer) unique |
| Cross-cutting | `audit_events` (…, **`district_id`**), `idempotency_keys` | as above |

Completion photos are `media_assets` with `kind='completion'`,
`work_order_id` and the **round** they were submitted in; earlier rounds are
kept.

**Seed** (`python -m app.seeds`):
- One active district (Yadgir) and one inactive district for boundary tests;
  departments with their `department_categories`; one institute; one
  industry partner.
- Ten Firebase accounts created by hand; their UIDs in
  `seeds/demo/users.json` (no passwords in git).
- A demo case at each stage: a `reported` report, a `prioritised` cluster
  with supporters, an `in_progress` work order, a published statement with an
  approved team and a submission.
- Photos: approved images packaged in `services/api/seeds/demo/photos/`
  (inside the image, since the Dockerfile copies `seeds/`), uploaded on first
  seed — or, if already uploaded, referenced by recorded `public_id`s.
- Deterministic UUIDs (idempotent re-runs). **`--reset` guard:** refuses
  unless `ENVIRONMENT != production`, `SEED_RESET_ALLOWED=true`, and the
  **username, host, port and database name** parsed from `DATABASE_URL`
  (never the password) exactly match an entry in `SEED_RESET_TARGETS`,
  written `user@host:port/database` — for example
  `janmaang@localhost:5432/janmaang,postgres.abcdefghijklmnop@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`.
  Host and database name are not enough: Supabase's pooler host is shared by
  every project in a region and every database is called `postgres`; the
  project is identified only by the `postgres.<project-ref>` username. The
  port distinguishes the pooler's session (5432) and transaction (6543)
  modes. The hosted demo's own entry is listed explicitly so its reset still
  works.

**Tests:** migration applies to an empty database; `alembic revision
--autogenerate` against it is empty (every model is discovered); seeding
twice yields identical rows; `--reset` accepts the listed target and
refuses a URL that differs from it in **any one** of username (another
project on the same pooler), host, port or database name; the password never
takes part in the comparison or appears in the refusal message.

**Database-backed helper tests (moved from Phase 0):**
- Idempotency: two concurrent requests with **one key and one payload** run
  the action once and both receive the same stored response; the same key
  with a different payload gets 409; a failed business write leaves no
  stored key.
- Transitions: a transition from the wrong status updates zero rows and
  raises 409; it sets `status_changed_at` and writes one audit event in the
  same transaction; a rolled-back transaction leaves neither.

## Phase 2 — Auth, media, citizen reports, first deploy

| Endpoint | Rules |
|---|---|
| `get_current_principal` | Firebase Admin initialised once; `verify_id_token` in a thread; unknown or inactive user → 403 |
| `GET users/me` | Contract shape |
| `POST media/signature` | type and ≤ 10,485,760 bytes; caller's folder; `allowed_formats`, `overwrite=false`; string parameters; `completion` kind only for officers |
| `POST media/complete` | verify Cloudinary's response signature, caller's folder, Admin-API format and size; idempotent on `public_id` |
| `POST reports` † | reporter from token, district from user; caller's own unattached report media (≤ 3); sequence code; idempotent |
| `GET reports?mine=true`, `GET reports/{id}` | read DTO with `thumbnail_url`, `status_changed_at`; citizens see only their own (404) |

**Deploy now:** Render with the existing Dockerfile; start command
`alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`;
Supabase **session pooler** URL (or `statement_cache_size=0`);
`ENVIRONMENT=staging`, Firebase, Cloudinary, Gemini and
`CORS_ORIGINS` set in Render; Vercel and Firebase Hosting domains in Firebase
authorised domains; seed the hosted database.

**Tests:** invalid / unknown / inactive token; another user's media rejected
on report creation; media completion replay; report persisted and readable
after a new session; same-key retry returns the same report, different
payload 409, two concurrent retries create one report.

**Exit:** live Flutter signs in, uploads, submits, reloads, and still sees the
report after a Render restart.

## Phase 3 — Panchayat validation, clusters, ranking

| Endpoint | Rules |
|---|---|
| `GET reports?status=reported\|verified` | caller's district |
| `POST reports/{id}/validate` | conditional from `reported`; reject needs a reason; audited; sets `status_changed_at` |
| `GET reports/{id}/cluster-suggestions` | same category, documented radius from the anchor report, Python distance |
| `POST reports/{id}/cluster` | conditional from `verified`; existing cluster or `{new: true}`; never automatic |
| `POST clusters/{id}/support` | unique (cluster, user) |
| `GET clusters/ranked` | contract shape with `score_breakdown`, computed on read; ties: older anchor, then id |
| `PATCH clusters/{id}/inputs` | responsible department or gov admin; 0–100; clears `inputs_are_demo`; audited |

Ranking: weights 30/22/20/18/10; support `100·(1−e^(−n/60))`; severity
30/55/80/100; age `min(100, days/90·100)`; missing gap/equity = 50 with
`is_demo: true`.

**Tests:** Panchayat outside the district gets 404; concurrent
validations — one wins, the other 409; concurrent supports never
double-count; a report cannot join two clusters; ranking values and
tie-break order.

## Phase 4 — Funding, work orders, officer evidence, statements

| Endpoint | Rules |
|---|---|
| `GET users?role=officer` | officers in the caller's district **and** department |
| `POST clusters/{id}/fund` † | caller's department must be responsible for the cluster's category in that district (403); officer's district and department must match (422); one transaction: idempotency row, conditional `prioritised → funded`, allocation, work order (round 1), audit |
| `GET work-orders?mine=true` | assigned officer |
| `PATCH work-orders/{id}` | assigned officer; first note `funded → in_progress` (conditional) |
| `POST work-orders/{id}/complete` † | conditional from `in_progress` and `expected_round` = current round (409 otherwise); caller's own completion media, 1–3, stamped with that round; → `awaiting_verification` |
| `GET work-orders/{id}/evidence` | any status; `after` selected by round (current while awaiting / verified; previous while correcting on round > 1; else null) with `after_round` |
| `GET statements` | partner roles: published only; department: published + own drafts |
| `POST statements` †, `POST statements/{id}/publish` | owning department only |

**Tests:** two concurrent fund requests with the **same key and payload** —
both receive the original success and one allocation exists; two concurrent
requests with **different keys** — one succeeds, the other gets 409, one
allocation; completing a work order makes the cluster
`awaiting_verification` and the reporter's `GET reports/{id}` and
`/verification` show it (the effective-status path); another department's officer
rejected; a department outside the category mapping gets 403; completion
photos keep their round; evidence selection per status and round; students
and industry read published statements but never drafts.

## Phase 5 — Citizen verification, Cloudinary evidence

| Item | Rules |
|---|---|
| `GET reports/{id}/verification` | contract shape incl. `round`, `can_verify`, `blocked_reason`; 404 until open |
| `POST work-orders/{id}/verify` † | body includes **`expected_round`**. One transaction: anchor reporter (403); conditional `awaiting_verification` **and** `round = expected_round` (409); verdict row (unique per round); `true → citizen_verified`, `false → in_progress` with round + 1 and the **same** allocation; audited |
| Delivery variants | server-signed; thumbnail `c_limit,w_320`, detail `c_limit,w_1280`, panels `c_pad,w_640,h_480`; `f_auto,q_auto` |
| Evidence card | built from `evidence.select(work_order)` — the same `after` and verdict label as the endpoint, so a returned attempt shows its own photo labelled "Round N · returned for correction"; text from saved data only; server-built only |
| Cloudinary | **Strict transformations** on |
| Measurement | `scripts/measure_cloudinary.py` with a browser `Accept` header; results to Notion |

**Client status:** Flutter sends `expected_round` and handles the 409. Phase 5
also accepts null original photos and displays a returned attempt's
`after_round` accurately. See [backend-phase5.md](backend-phase5.md) for local
implementation, verification and the still-pending hosted exit gate.

**Tests:** after a negative verdict, the endpoint, the card and the
verification view all select the returned attempt's photo with the same
round label; a stale `expected_round` is 409 and records nothing (the Flutter
app shows "This repair was updated — reload to see the latest evidence"); a
non-reporter is 403; two concurrent verdicts — one recorded; a negative
verdict leaves exactly one allocation and moves to round 2; the card's
verdict text matches the saved verification; an edited card URL fails.

**Exit:** the full hosted journey including a "not fixed" round.

## Phase 6 — Student, institute, faculty, CSR, admin

| Endpoints | Rules |
|---|---|
| teams (`mine`, `institute=me`, create †, approve) | published statements only; approve within own institute |
| submissions (`mine`, `institute=me`, create †), reviews † | approved teams only; HTTPS links; reviewers within the institute, once each |
| sponsorships (`mine`, pledge †) | `pledged` only |
| `admin/summary`, `admin/audit` | gov admin: own district (audit by `audit_events.district_id`); super admin: all |
| `admin/users`, `organizations`, `PATCH admin/users/{id}` | super admin; reason required; audit in the same transaction; **self-change → 403** |

**Tests:** faculty from another institute gets 404; duplicate review 409;
unapproved team cannot submit; a `javascript:` link is rejected; gov admin
sees only their district's audit events; self role change 403.

## Phase 7 — AI suggestion (optional)

`POST reports/suggest`: Gemini structured output constrained to the allowed
categories and severities, 8 s timeout, 503 on any failure, nothing saved;
per-user rate limit. The prompt lives at `app/prompts/classify_v1.txt` —
**inside `app/`**, which the production Dockerfile copies — and is loaded
relative to the package. Wire Flutter `analyze()` to it.

**Tests:** structured output validated; timeout and malformed output → 503;
report creation unaffected.

## Phase 8 — Integration and demo readiness

1. Rerun every phase's tests together plus one end-to-end journey test.
2. Light rate limits on signatures, suggestions and report creation.
3. Two full hosted runs from `--reset`; recorded backup video; warm Render
   before judging.
4. Update ARCHITECTURE.md (removed middleware), Notion decisions and
   limitations, Cloudinary measurements.

## Deployment checklist

- [ ] `ENVIRONMENT=staging` and required provider credentials set in Render
- [ ] Firebase Admin credentials, Cloudinary, Gemini keys set; none in git
- [ ] `CORS_ORIGINS` = exact Vercel and Firebase Hosting origins
- [ ] Supabase session pooler URL
- [ ] Start command runs `alembic upgrade head` first
- [ ] `uv.lock` committed after every dependency change
- [ ] Prompt file under `app/`; seed photos under `seeds/demo/photos/`
- [ ] Strict transformations enabled in Cloudinary
- [ ] Hosted domains in Firebase authorised domains
- [ ] Seed run once; `SEED_RESET_ALLOWED` unset in any non-demo environment;
      `SEED_RESET_TARGETS` lists only demo `user@host:port/database` entries,
      including the Supabase `postgres.<project-ref>` username

## Cut order if time runs short

Phase 7 → most of Phase 6 (keep admin summary and audit) → rate limits.
Never cut Phase 2's deployment or Phase 5's Cloudinary evidence.
