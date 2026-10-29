# Day 1 frontend/backend handoff

Status: Phase 2 implements the current-user, media upload and citizen report endpoints below. The later staff/partner endpoints remain planned. Live Firebase/Cloudinary and hosted integration are pending provider setup; local PostgreSQL integration tests use provider doubles.

## Shared conventions

- `API_BASE_URL` / `NEXT_PUBLIC_API_URL` is the API origin, such as `http://localhost:8000`. Clients append `/api/v1` exactly once.
- Business requests carry `Authorization: Bearer <Firebase ID token>`. Passwords are sent only to Firebase through its client SDK.
- The API verifies the token, resolves the Firebase UID to a local user, and enforces role, district, department, assignment and ownership. Client navigation is not authorization.
- JSON uses snake_case. Datetimes are ISO-8601 UTC strings. IDs are opaque strings.
- Non-2xx responses are errors; the client must not treat a login, upload, or report as successful until the relevant operation succeeds. `detail` may be a safe message or a FastAPI validation-error list.
- **Idempotent writes** (every write marked † below, plus `POST /reports`):
  the key is unique per `(user, operation, key)` by database constraint. The
  business write, its audit event and the stored response commit in **one
  transaction**, so two concurrent requests with one key cannot both run the
  action: the second either waits and receives the stored response or gets
  409. Same key and identical payload → the original response, same status.
  Same key, different payload → 409.
- **State changes are conditional**: each transition updates only from its
  expected status (or under a row lock) and returns 409 if the record moved
  on. A key identifies a request; it never replaces such a precondition.
- An empty list is returned as `{"items": []}`. A missing feature returns an explicit error, never a fabricated success.
- Before the first profile request, both clients call unauthenticated `GET /health` (at the origin, outside `/api/v1`) and wait up to about 75 seconds for a sleeping free-tier host to wake. `/health` must stay public and must be covered by the CORS configuration.
- The Flutter app accepts only `citizen` profiles; staff and partner roles use the web workspace.

## Status, category and severity values

These are the only values the API sends and accepts. The backend enum
(`services/api/app/shared/enums.py`), the Flutter mapping
(`apps/mobile/lib/features/report/data/report_dto.dart`) and this table change
together.

| `status` | Meaning | Set by |
|---|---|---|
| `reported` | Saved; awaiting Panchayat validation | Citizen creates the report |
| `verified` | Validated by the Panchayat — **not** citizen confirmation | Panchayat |
| `rejected` | Declined by the Panchayat; `rejection_reason` is present | Panchayat |
| `prioritised` | In a cluster and in the ranked list | Panchayat confirms the cluster |
| `funded` | Allocation saved and work order assigned | Department |
| `in_progress` | Officer is working on it | Officer's first update, or a negative citizen verdict |
| `awaiting_verification` | Completion evidence uploaded; reporter's verdict pending | Officer completes the work order |
| `citizen_verified` | The original reporter confirmed the repair | Reporter |

Allowed transitions: `reported → verified | rejected`, `verified → prioritised`,
`prioritised → funded`, `funded → in_progress`,
`in_progress → awaiting_verification`,
`awaiting_verification → citizen_verified | in_progress`. Once a report is in a
cluster, the API returns the cluster's status for it.

`category`: `water`, `roads`, `lighting`, `sanitation`, `health`, `education`,
`electricity`, `transport`, `other`.

`severity`: `low`, `medium`, `high`, `critical`.

Clients treat any other value as a protocol error for that record only: a list
skips the record and says how many it could not show.

## Current profile

`GET /api/v1/users/me`

```json
{
  "id": "local-user-id",
  "firebase_uid": "verified-firebase-uid",
  "role": "citizen",
  "display_name": "Demo Citizen",
  "email": "citizen@example.com",
  "district_id": "district-id",
  "district_name": "Yadgir",
  "department_id": null,
  "institute_id": null,
  "organization_id": null,
  "is_demo": true
}
```

`district_name` is the assigned district's display name (`null` for a super
admin without a district); the citizen app shows it as the account's location.

Roles: `citizen`, `student`, `faculty`, `institute`, `panchayat`, `department`, `officer`, `industry`, `gov_admin`, `super_admin`.

Return 401 for invalid authentication and 403 for an authenticated but unprovisioned/disabled account. A browser-supplied role or UID is never authoritative.

## Photo upload

1. `POST /api/v1/media/signature`

```json
{"filename":"handpump.jpg","content_type":"image/jpeg","bytes":123456,"kind":"report"}
```

Response:

```json
{
  "upload_id": "server-upload-intent-id",
  "upload_url": "https://api.cloudinary.com/v1_1/YOUR_CLOUD/image/upload",
  "parameters": {
    "api_key": "PUBLIC_CLOUDINARY_API_KEY",
    "timestamp": "SERVER_TIMESTAMP",
    "signature": "SERVER_GENERATED_SIGNATURE",
    "public_id": "SERVER_GENERATED_ASSET_ID",
    "overwrite": "false"
  }
}
```

The backend returns the complete exact parameter set, including any signed preset, folder or context. The client forwards those values unchanged with the image as multipart `file`. It must not attach the Firebase bearer token to Cloudinary. Only HTTPS `api.cloudinary.com` upload destinations are accepted.

2. Upload the actual image directly to that URL.
3. `POST /api/v1/media/complete`

```json
{"upload_id":"server-upload-intent-id","public_id":"SERVER_GENERATED_ASSET_ID","version":1234567890,"signature":"CLOUDINARY_RESPONSE_SIGNATURE"}
```

Response:

```json
{"id":"local-media-id","url":"https://res.cloudinary.com/...","thumbnail_url":"https://res.cloudinary.com/..."}
```

The API verifies the asset against the authenticated caller's upload intent, image type, format, size, expected ID and upload result. An ownership failure must never cause deletion of another user's asset. Completion is idempotent. Clean up only expired/rejected assets proven to belong to the caller's own issued intent.

The final report accepts at most three attached media IDs. Allowed formats are JPEG, PNG and WebP, with a maximum of 10 MiB per selected file (10,485,760 bytes); backend and frontend must use this same byte limit. Client checks improve feedback; server checks remain required. Cloudinary/API secrets never enter either frontend.

## Reports

`POST /api/v1/reports` with a stable `Idempotency-Key` header for retries of the same logical submission. Scope keys to the authenticated user, reject a reused key with a different payload, and return the same saved report for an exact retry:

```json
{
  "transcript": "The handpump has stopped working.",
  "title": "Handpump repair",
  "category": "water",
  "severity": "medium",
  "summary": "The handpump has stopped working.",
  "latitude": 16.76,
  "longitude": 77.14,
  "location_label": "Ward 4",
  "channel": "text",
  "media_ids": ["local-media-id"]
}
```

`channel` records how the citizen started the report and is one of `text`, `voice`, `photo` or `location` (the four entry points on the citizen app's Home screen). It is provenance only, never a ranking input; any other value is 422.

The API derives reporter identity and district from the verified principal and trusted geography. It validates media ownership, count, ranges, text lengths and enums. Category/severity entered by the citizen are provisional suggestions, not trusted ranking inputs. Report creation must work without Gemini success.

`GET /api/v1/reports/{id}` and the creation response return a report read DTO. `GET /api/v1/reports?mine=true` returns `{"items":[...report read DTOs...]}`. Scope report reads server-side.

```json
{
  "id": "report-id",
  "code": "YDG-WTR-0001",
  "title": "Handpump repair",
  "description": "The handpump has stopped working.",
  "transcript": "The handpump has stopped working.",
  "reporter_id": "local-user-id",
  "category": "water",
  "severity": "medium",
  "status": "reported",
  "ward": "Ward 4",
  "district": "Yadgir",
  "latitude": 16.76,
  "longitude": 77.14,
  "created_at": "2026-10-21T10:00:00Z",
  "media": [{"id":"local-media-id","url":"https://res.cloudinary.com/...","thumbnail_url":"https://res.cloudinary.com/..."}]
}
```

Submission media IDs and display URLs are separate fields. Do not put bare IDs into `photoUrls`. Advanced score, cluster and timeline fields may be added later; absence must not turn into invented live figures.

## Shapes the staff workspace expects (Day 2+)

Implemented on the web client in `apps/web/src/lib/api/schemas.ts`; responses
outside these shapes are shown as errors, not coerced.

Ranking breakdown, on a report or ranked cluster as `score_breakdown`:

```json
[{"factor":"support","label":"Community support","score":72.4,"weight":0.30,"is_demo":false},
 {"factor":"equity","label":"Equity","score":50,"weight":0.20,"is_demo":true}]
```

`score` is 0–100 and `weight` 0–1. `is_demo` is true for a seeded or neutral-default input, which the UI labels "Demo value".

Ranking is computed on read for confirmed clusters. The five factors are
community support (30%), infrastructure gap (22%), equity (20%), severity
(18%) and age (10%). Community support counts the **union of distinct member
reporters and explicit citizen supporters**, never reports plus support rows.
Its score is `100 * (1 - exp(-unique_citizens / 60))`. Severity is the highest
Panchayat-validated member severity: low 30, medium 55, high 80, critical 100.
Age uses elapsed days since the anchor report, capped at 90 days for a score
of 100; future dates contribute zero. Missing gap/equity values use 50 and
remain labelled demo/default. A complete official assessment clears
`inputs_are_demo`; it does not relabel seeded report/support provenance.
Ties use the older anchor's creation date, then the cluster UUID.

Panchayat validation confirms the submitted category and severity as well as
the report's validity. The current form has no field-correction editor; decline
an incorrectly classified report with a reason and request a corrected report.
Unvalidated reports never contribute severity or support to the ranked list.

Cluster matching is against the **anchor report**, with the same category and
district. Water, lighting and the other point categories use 100 metres. Roads
and sanitation use 500 metres; sanitation includes drains in this prototype,
which has no separate drain subtype. Distance proposes candidates only; the
Panchayat must confirm that they describe the same problem. Assignment checks
the radius again. Only `prioritised`, `funded` and `in_progress` clusters accept
members or new explicit support; recurring faults after completion need a new
cluster. These limits do not silently merge nearby assets.

Work-order evidence, `GET /api/v1/work-orders/{id}/evidence`:

```json
{
  "report_code": "YDG-WTR-0001",
  "status": "awaiting_verification",
  "before": {"url": "https://res.cloudinary.com/...", "uploaded_at": "2026-10-20T10:00:00Z"},
  "after": {"url": "https://res.cloudinary.com/...", "uploaded_at": "2026-10-24T10:00:00Z"},
  "card_url": "https://res.cloudinary.com/..."
}
```

`before` is the anchor report's earliest photo and is `null` when the citizen
attached none (report photos are optional). `after` is the earliest completion
photo of the round given in `after_round`, chosen by the shared selection rule;
it is `null` before completion. `card_url` is null until there is selected
completion evidence; otherwise it is a server-built Cloudinary image/text
composition. Missing original evidence is labelled "No original photo attached"
on the card, never replaced with a completion photo. `verdict_label` contains
the same trusted wording used by the card. All URLs are HTTPS, server-signed
Cloudinary delivery URLs. Comparison photos use equal 640x480 padded canvases;
thumbnail/detail variants retain bounded dimensions with automatic format and quality.

Cards are shareable **snapshots of the saved status when their URL was
generated**. Reopening the application fetches the current status and a new
signed composition. An earlier shared card remains an earlier snapshot; it is
not a live status page. Strict transformations must be enabled in Cloudinary
before relying on delivery-side rejection of edited transformations. These
URLs are for approved public demonstration evidence, not confidential media.

Staff uploads use the same `media/signature` → Cloudinary → `media/complete` flow as the citizen app, with `kind: "completion"` for officer evidence.

Money is always integer paise (`amount_paise`); the web form converts typed rupees.

## Staff workspace endpoints (Panchayat, Department, Officer)

What the web pages call, as implemented in `apps/web/src/features/*/api.ts`.
Lists return `{"items": [...]}`. The API scopes every list and write to the
caller's district, department or assignment; the client never filters for
access. Writes marked † carry an `Idempotency-Key` header.

| Call | Body | Response |
|---|---|---|
| `GET reports?status=reported\|verified` | — | report read DTOs (above), plus `rejection_reason` |
| `GET reports/{id}` | — | report read DTO |
| `POST reports/{id}/validate` | `{"decision":"verify"}` or `{"decision":"reject","reason":"…"}` | `{"id","status"}` |
| `GET reports/{id}/cluster-suggestions` | — | items `{"id","title","category","distance_m","report_count","supporter_count"}` |
| `POST reports/{id}/cluster` | `{"cluster_id":"…"}` or `{"new":true}` | `{"id","status"}` |
| `GET clusters/ranked` | — | items `{"id","title","category","status","rank","priority_score","supporter_count","report_count","anchor_report_code","infrastructure_gap","equity_index","inputs_are_demo","score_breakdown"}`. **Only `prioritised` clusters** (open demand still waiting for funding) are ranked and listed; funded, in-progress and verified work leaves the ranking. In `score_breakdown`, `is_demo` is true only for a seeded or neutral-default gap/equity input — support, severity and age are computed from recorded data and are never demo values |
| `POST clusters/{id}/support` | — | `{"id","supporter_count"}` — citizen only, own district. Repeated requests preserve one support row; reporters and explicit supporters are counted once in the same total used by ranking |
| `PATCH clusters/{id}/inputs` | `{"infrastructure_gap":0-100,"equity_index":0-100}` | `{"id"}` |
| `GET users?role=officer` | — | items `{"id","display_name","email"}` — assignable officers in the caller's **district and department** |
| `POST clusters/{id}/fund` † | `{"amount_paise","officer_id","notes"?}` — `amount_paise` a positive integer, `notes` become the officer's instructions | **201** `{"allocation_id","work_order_id"}`. Only the department responsible for the cluster's category in that district may fund it (403 otherwise). The officer must be in the work order's district **and** department (422 otherwise). Exact retry with the same key → the original response. Any other request for an already-funded cluster → **409** |
| `GET statements?status=` | — | items `{"id","title","body","status":"draft\|published","cluster_id","published_at"}`. **Read access:** student, faculty, institute, industry, gov admin and super admin see **published** statements only; a department sees published statements plus **its own drafts**. Drafts are never visible outside the owning department |
| `POST statements` † | `{"title","body","cluster_id"?}` | statement — department only, owned by the caller's department |
| `POST statements/{id}/publish` | — | statement — owning department only; publishing twice returns the published statement |
| `GET cases?limit=200` | — | items `{"cluster_id","report_code","title","category","status","waiting_on":"department\|officer\|citizen\|none","status_changed_at","work_order_id","round","department_name","officer_name","allocated_paise","allocated_at","allocated_by_name"}`, most recently changed first: every case from `prioritised` to `citizen_verified`. A department sees prioritised cases in categories it answers for in its district, plus cases it funded; a gov admin sees the district; a super admin sees all; other roles 403. Allocation fields are `null` until funded; amounts are recorded allocations, not payments |
| `GET work-orders?mine=true` | — | items `{"id","cluster_id","report_code","title","status","round","location_label","instructions","notes","allocated_paise","assigned_at"}` |
| `PATCH work-orders/{id}` | `{"notes":"…"}` | `{"id","status"}`; the first update moves `funded → in_progress` only the assigned officer (404 otherwise); after completion is submitted, 409 |
| `POST work-orders/{id}/complete` † | `{"media_ids":[…],"expected_round":n}` (the caller's own `completion` media; `n` is the work order's `round` as shown) | `{"id","status":"awaiting_verification"}`. Only from `in_progress`. **409** if `expected_round` is not the current round (the citizen returned the work since the page loaded). The attached media are stored with the work order's **current round**; earlier rounds' photos are kept, never overwritten |
| `GET work-orders/{id}/evidence` | — | evidence (above), for **every** assigned order, open ones included. `after` is chosen deliberately by round: while `awaiting_verification` or `citizen_verified`, the **current** round's completion; while `in_progress` on round > 1, the **previous** round's (returned) completion, which the officer page labels "Previous completion · returned by the citizen"; otherwise `null`. `after_round` (int or null) states which round `after` belongs to. `returned_comment` (string or null): while `in_progress` on round > 1, the citizen's reason for returning the round shown, so the officer knows what to fix |

`round` starts at 1 and increases each time the reporter answers "not fixed".

A work order has no status of its own: every `status` returned for a work
order, its cluster and the cluster's reports is the **cluster's** status, with
the cluster's `status_changed_at`. Completing a work order therefore moves
all of them to `awaiting_verification` together.

The evidence endpoint, the verification view and the evidence card use one
selection rule, so they always agree. While a returned attempt is being
corrected (`in_progress`, round > 1), `after` is that returned attempt's photo
with its `after_round`, and the card reads "Round N · returned for
correction".
Errors use FastAPI's `{"detail": …}`; a short string `detail` is shown to the
official verbatim, so keep it user-readable.

## Partner and oversight endpoints (Student, Faculty, Institute, Industry, Admin)

As implemented in `apps/web/src/features/{teams,projects,funding,admin}/api.ts`.
Scope is the API's: `mine=true` is the caller's own records and
`institute=me` the caller's institute. † carries an `Idempotency-Key`.

| Call | Body | Response |
|---|---|---|
| `GET teams?mine=true` / `GET teams?institute=me` | — | items `{"id","name","statement_id","statement_title","institute_approved","member_count","created_at"}` |
| `POST teams` † | `{"name","statement_id"}` (published statements only) | team |
| `POST teams/{id}/approve` | — (institute role, own institute) | team |
| `GET submissions?mine=true` / `GET submissions?institute=me` | — | items `{"id","team_id","team_name","statement_title","title","summary","link","submitted_at","review_count","my_review":{"score","comment"}\|null}` |
| `POST submissions` † | `{"team_id","title","summary","link"?}` — approved teams only; `link` HTTPS | submission |
| `POST submissions/{id}/reviews` † | `{"score":1-5,"comment"}` — own institute, once per reviewer (409 on a second) | `{"id"}` |
| `GET sponsorships?mine=true` | — | items `{"id","statement_id","statement_title","amount_paise","status":"pledged","pledged_at"}` |
| `POST statements/{id}/sponsorships` † | `{"amount_paise"}` | sponsorship |
| `GET admin/summary` | — | `{"district_name","reports_by_status":{status:count},"cluster_count","work_orders_by_status":{status:count},"allocated_paise","pledged_paise"}` |
| `GET admin/audit?limit=50[&before_at=…&before_id=…]` | — | `{"items":[{"id","at","actor_name","actor_role","action","entity_type","entity_id","reason","before","after"}],"next":{"before_at","before_id"}\|null}`, newest first. Pass `next` back to read older events (keyset paging: no gaps or repeats); both cursor parts or neither (422). `before`/`after` are the recorded field values with contact details (`email`) removed. Each event stores its own `district_id` (the district of the affected record, nullable for platform-wide events); a gov admin sees events for their district, a super admin sees all. Scope never depends on the actor's current organisation |
| `GET admin/users` | — (super admin) | items `{"id","display_name","email","role","district_id","department_id","institute_id","organization_id"}` |
| `GET organizations` | — (super admin) | items `{"id","type":"district\|department\|institute\|industry","name","parent_id"}` — `parent_id` is the district a department, institute or industry organization belongs to (`null` for districts) |
| `PATCH admin/users/{id}` | `{"role","district_id","department_id","institute_id","organization_id"?,"reason"}` — `null` clears a scope | admin user; the audit event is written in the same transaction. **403 when `{id}` is the caller**: nobody changes their own role or scope (the web client also refuses). **409 when the user is an officer with open work orders** (`funded`, `in_progress` or `awaiting_verification`) and the change would remove their access to them |

For administration, `organization_id` is required when assigning the industry
role; it identifies an active industry organization in the chosen district.
Department/officer roles require `department_id`; student/faculty/institute
roles require `institute_id`; every role except super admin requires a district.
Scopes irrelevant to the new role are cleared. Invalid scope is 422, missing
users are 404, and self-change is 403. A district move writes an affected-scope
audit event in each of the old and new district. An unchanged PATCH returns the
saved profile without another audit event. The organization list includes only
active entries. Another user's browser may need a fresh sign-in to update its
cached profile after an administrator changes its role.

Student lists require `mine=true`; faculty/institute lists require
`institute=me`. CSR lists require `mine=true` and show the caller's own pledges.
Partner writes cannot target unpublished or other-district statements. Review
and pledge creation return 201; retries with the original key return that same
response. Fresh-key duplicate reviews return 409. Team approval is repeatable
without duplicate approval events. Audit limits are 1–200, default 50.

Changes made by one role reach another role's open page through its
Refresh buttons or when that window regains focus; the API needs no push
channel for the prototype.

Report lists accept a single effective `status` or a pipe-separated set such
as `status=reported|verified`, plus `limit` (default 100, maximum 200) and
`offset` (default 0). `verified` excludes reports already in clusters because
their effective status has advanced. Citizens default to their own reports;
`mine=false` is refused. Panchayat and government admin reads stay in their
district. Department/officer report and ranking reads are also restricted to
the categories assigned to their department. Super admin reads span districts.
Partner roles read ranked clusters within their district, not raw citizen
reports. An out-of-scope report/cluster is 404, a wrong-role action is 403, and
an already-transitioned record is 409.

Status-count keys use the agreed status values. Submission `link` must be an
HTTPS URL: the web client refuses any other scheme because it renders the link
for faculty.

## Citizen verification (Flutter)

Report detail adds `rank`, `total_ranked`, `priority_score` and
`score_breakdown` (shape above) only while the report's cluster is
`prioritised`; once funded they are `null`, and the app explains that the
problem has left the ranking. `supporter_count` is present for every clustered
report, before and after funding.

`status_changed_at` (optional, ISO-8601 UTC) is when the report's **current
effective status** took effect — for a clustered report, when the cluster
entered that status. The app dates the current timeline step with it and
nothing else: when it is absent the step is shown undated. `created_at` and
`updated_at` are never used as transition times.

Every field is type-checked on the client. A record with a wrong-typed field
is a protocol error: a detail view shows an error, and a list skips that
record and says how many it could not show. Each `media` item may
carry `thumbnail_url`; the app shows thumbnails and opens `url` on tap.

`GET /api/v1/reports/{id}/verification` — 404 until a work order has
completion evidence or is awaiting verification:

```json
{
  "work_order_id": "w1",
  "report_code": "YDG-WTR-0001",
  "title": "Handpump not working",
  "category": "water",
  "status": "awaiting_verification",
  "round": 1,
  "after_round": 1,
  "can_verify": true,
  "blocked_reason": null,
  "verdict_label": "Awaiting citizen verification",
  "before": {"url": "https://res.cloudinary.com/...", "uploaded_at": "2026-10-11T10:00:00Z"},
  "after": {"url": "https://res.cloudinary.com/...", "uploaded_at": "2026-10-24T10:00:00Z"},
  "card_url": "https://res.cloudinary.com/..."
}
```

`can_verify` is true only for the original reporter while the work order is
`awaiting_verification`; otherwise `blocked_reason` is a short sentence the
citizen sees. `before` may be null because report photos are optional. The
verification route is 404 until completion evidence exists. During correction,
`round` is the new work round while `after_round` is the returned earlier
attempt; `can_verify` is false. The Flutter view labels that photo "Returned
attempt" and does not claim a new completion has been submitted. A reporter of
a non-anchor member report can review the evidence through their own report
but cannot verify the cluster; other citizens receive 404 for the report read.
The app shows the UI hint; the API enforces it on the write below.

`POST /api/v1/work-orders/{id}/verify` with `Idempotency-Key:
verify-{work_order_id}-{round}`:

```json
{"verdict": false, "expected_round": 2, "comment": "Still dry in the evening."}
```

`expected_round` is the round whose evidence the citizen reviewed (the
`round` from the verification view). In one transaction the API checks, in
order: the caller has a report in this cluster (else 404, as for the
verification view); the caller is the original reporter (else 403); the work order is
`awaiting_verification` **and** its current round equals `expected_round`
(else **409** — the evidence changed, or a verdict was already recorded);
then records the verdict and its audit event. The key identifies the request
for retries; it is not the round check.

An exact retry with the same user, key, work-order ID and normalized payload
returns the saved 200 response, even if the original verdict advanced the
round. A fresh stale-round request gets 409 and writes nothing. Reusing a key
with a different verdict, comment, round or work-order ID also gets 409.

`comment` is optional (≤ 500 characters). `true` → `citizen_verified`;
`false` → `in_progress` with `round` + 1 and **no new allocation**. On 409 the
app tells the citizen "This repair was updated — reload to see the latest
evidence" and offers Reload; nothing is recorded.

## Optional suggestion

`POST /api/v1/reports/suggest` accepts `{"transcript":"..."}` (1–2000 characters after trimming; no other fields) and returns:

```json
{"category":"water","severity":"high","title":"Handpump not working","summary":"The ward 4 handpump gives no water.","mentioned_location":"Ward 4","detected_language":"hi"}
```

`category`, `severity` and `detected_language` use the same values as report creation (`detected_language` is one of `en hi mr bn ta te kn gu`); `title` ≤ 120 characters, `summary` ≤ 500, `mentioned_location` ≤ 200 or `null` when no place was mentioned. Every field is a suggestion the citizen can change; it never sets status, clustering, ranking or funding.

| Status | When |
|---|---|
| 403 | Caller is not a citizen |
| 422 | Empty, too long or extra fields |
| 429 | More than 10 suggestions per citizen per minute (per API instance; resets on restart) |
| 503 | Not configured, timed out (8 s), provider error, or output that fails validation — `{"detail":"Suggestions are unavailable right now. Enter the details yourself."}` |

Nothing is stored and no idempotency key is needed. Failure must leave manual entry and submission available; it must not create or imply a persisted report. Photos are not sent.

## Case-update notifications (Flutter inbox)

| Endpoint | Body | Response / rules |
|---|---|---|
| `GET notifications?unread_only=false&limit=50&offset=0` | — | `{"items":[{"id","title","body","resource_type","resource_id","created_at","read_at"}],"unread_count"}`, newest first. Only the signed-in user's own notifications |
| `POST notifications/{id}/read` | — | `{"id","read_at"}`. Marking twice keeps the first time. Another user's notification is 404 |

Notifications are written in the same transaction as the change they describe, so a failed change never notifies. Reporters (and explicit supporters) of a cluster are told when their report is reviewed or clustered, when the case is funded, when work starts, when completion evidence is ready for review, and when a verdict is recorded. Completion and verdict updates are **per round**, so a correction round notifies again. In-app only: no push, SMS or WhatsApp delivery yet. The citizen app's demo mode shows an explanatory message instead of an inbox.

## Account activation (super admin)

| Endpoint | Body | Response / rules |
|---|---|---|
| `PATCH admin/users/{id}/status` | `{"is_active":true\|false,"reason"}` | admin user (now including `is_active`). A deactivated account is refused on its next request. 403 for your own account and for non-super admins; **409** for an officer with open work orders (funded, in progress or awaiting verification); the reason is required and audited as `user.activated` / `user.deactivated`. No staff-site control yet |

## Transparency analytics

| Endpoint | Body | Response / rules |
|---|---|---|
| `GET analytics/public` | — (**no sign-in**) | `{"report_count","cluster_count","active_cases","citizen_verified_cases","reports_by_status","clusters_by_status","sample_data","updated_at"}`: aggregate totals only; a complaint takes its case's status, and both totals come from one snapshot. **Live records only once any exist; until then the labelled demonstration data is shown with `sample_data: true`** (the homepage labels it "Sample data"). Sample and live figures are never mixed. No reporter, title, photo or coordinate is published |
| `GET analytics/workload` | — (department, gov admin, super admin) | Per active, non-demo officer in scope: open, funded, in-progress and awaiting-verification work orders and the oldest open assignment. Other roles 403. Not yet shown in either client |

## Integration gate

With real Firebase configuration, a seeded citizen account and the API running: sign in, upload one image, submit a report, refresh, read the same report and image, restart the API, and read it again. The gate is pending until performed against the actual backend; client tests cannot establish database persistence.
