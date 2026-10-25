# Backend Phase 5 — citizen verification and Cloudinary evidence

Implemented on 25 October 2026 on branch `test`, building on the existing
uncommitted Phase 4 implementation. This record describes local code and test
evidence. Firebase, Cloudinary, Supabase and Render are still unconfigured; the
hosted exit gate, actual card rendering, Strict transformations checks and real
byte measurements remain pending.

## Delivered

- `GET /api/v1/reports/{id}/verification`: the citizen's own district-scoped
  report, anchor evidence, current work round, selected evidence round,
  eligibility and an actionable blocked reason. Returns 404 before completion.
  Member-report citizens may inspect their case, but the anchor reporter alone
  decides the verdict. Confirmed cases and returned attempts remain readable.
- `POST /api/v1/work-orders/{id}/verify`: strict JSON boolean verdict, explicit
  positive integer `expected_round`, optional comment up to 500 characters and
  an idempotency header. The stored request hash includes the work-order ID.
- A citizen with no report in the cluster gets 404, as the verification view
  does. The shared transition checks the reporter before revealing stale state/round,
  locks cluster then work order, records the verdict for the reviewed round,
  updates status/round and writes its audit event in one transaction. The audit
  now includes the verdict as well as before/after rounds. Failed writes and
  commits leave no partial verification or retry-key reservation.
- Positive verdict: `citizen_verified`. Negative verdict: `in_progress`, round
  increases by one, the same allocation remains. Exact retries return the
  original response; competing distinct requests produce one success and 409s.
- The officer evidence endpoint and citizen verification view call one evidence
  builder and `core.evidence.select`. The card uses that same selection. While
  correcting, all show the previous round's photo with "Round N · returned for
  correction"; the next completion switches all to the new round.
- Cloudinary signs 640x480 `c_pad` comparison panels, plus existing bounded
  thumbnail/detail variants with `f_auto,q_auto`. Aspect ratios are preserved.
- The shareable 1280x640 card uses Cloudinary image/text layers, upload dates in
  UTC, the report reference, round and trusted verdict. Only saved application
  asset references reach the signer; arbitrary remote URLs are not accepted.
  A missing before photo gets a text panel, never a fake or duplicated image.
- Flutter accepts missing originals and reads `after_round`. The correction
  screen identifies the returned attempt, hides verdict buttons and avoids the
  previous incorrect claim that round 2 already has new completion evidence.
- Officer evidence and assignment reads also require the officer's current
  district and department, so moving scope does not expose old assignments.
- `scripts/measure_cloudinary.py` measures actual image response-body bytes
  against original bytes from Cloudinary Admin metadata. It includes the exact
  browser Accept header and records negative savings honestly. No invented
  measurement report is committed.

No migration or dependency change is needed. The verification table,
per-round uniqueness and shared transitions were established in earlier phases.

## Card behavior and provider configuration

The pending wording is "Awaiting citizen verification". Only the confirmed
state says "Citizen verified". Returned attempts identify their own earlier
round. Photos support human judgement and do not prove a repair.

Each signed URL is a status snapshot. The footer and web caption state that
status was captured when the card was generated. A later verdict creates a
different signed transformation. Previously shared cards remain valid older
snapshots, so use the application to inspect current status. A signed URL is
not a revocable per-user authorization token; only approved public evidence is
appropriate for this demo.

Follow [Phase 2 setup](backend-phase2.md), enable **Strict transformations** in
the Cloudinary product environment, and exercise the signed variants. The
server signs the complete composition using the SDK's long SHA-256 delivery
signature. Local tests recompute it and detect edited verdict text. They cannot
establish that your product environment rejects edited/unsigned URLs until
that setting is enabled and tested there. Previously generated derivatives can
remain accessible under provider caching rules; do not broadly allowlist card
transforms or treat enabling Strict transformations as retroactive privacy.

The first image becomes a 640x480 padded panel. Larger canvas extensions use
`c_lpad`, which adds the header/footer and second panel without resizing the
first panel again. The image layer is applied separately from the image/text
definition, as required by Cloudinary. The after overlay references the saved
public ID; application uploads use immutable random IDs and `overwrite=false`.
Manually replacing originals in the provider console is outside this history
contract.

References:

- [Cloudinary layers](https://cloudinary.com/documentation/layers)
- [Padding and resize modes](https://cloudinary.com/documentation/resizing_and_cropping)
- [Strict transformations and delivery signatures](https://cloudinary.com/documentation/control_access_to_media)

## Measure approved demonstration images

From `services/api`, with its server-side `.env` configured:

```powershell
uv run python ../../scripts/measure_cloudinary.py --public-id janmaang/users/OWNER/report/ASSET --output ../../docs/development/cloudinary-measurements.local.json
```

Replace the reference with an actual approved asset ID from your app. Repeat
`--public-id` for additional images. Optionally pass `--accept` with the browser's
actual image Accept header. The script follows no redirects, checks image HTTP
responses and caps response bodies at 10 MiB. It does not persist credentials
or response URLs. The example filename is local measurement output; review its
approved asset references before deliberately committing or pasting to Notion.

Output records original bytes (Admin metadata), actual thumbnail/detail/panel
body lengths, content types, saved bytes, percentage, Accept header and a UTC
measurement time. Response headers, TLS overhead, cache timing and latency are
not counted. A failure produces no success report. No real measurements have
been run yet.

## Verification

Tests cover positive and negative verdicts; original-reporter eligibility;
non-anchor member reads; stale rounds; exact concurrent retries; competing
verdicts; commit rollback; allocation preservation; retained round photos;
shared endpoint/card selection; missing before images; signed composition and
tamper detection; measurement failure/negative-savings behavior; and a full
report → validation → cluster → funding → officer completion → citizen return →
second completion → citizen confirmation journey on real PostgreSQL.

Cloudinary and Firebase are doubled only at their external provider boundaries.
The actual Cloudinary SDK generates/signs URLs in unit tests. Flutter unit and
widget tests cover null originals, returned-attempt labels, hidden verdict
buttons and the existing stale-round reload flow.

Local final results:

- **232 backend tests passed** against PostgreSQL 16, including 28 new Phase 5
  cases; four pre-existing deprecation warnings remain.
- Ruff lint/format (including the measurement script), strict mypy and both
  import-linter contracts passed.
- OpenAPI matches the CI export exactly; regenerated TypeScript contracts
  passed their type check.
- Flutter formatting/analyze passed, **150 tests passed**, and the live-mode
  production web build succeeded.
- Web typing/lint passed, **116 tests passed**, and the Next.js production
  build succeeded. The first sandboxed Vitest launch was blocked by filesystem
  access before testing; rerunning with normal access passed all tests.
- Source formatting and the whitespace diff check passed. Phase 4 work remains
  present; these changes have not been committed, pushed or deployed.

## Live exit gate — not yet performed

1. Configure actual provider accounts and real seeded Firebase UIDs.
2. Submit an approved original photo in Flutter, validate/cluster it, fund and
   assign it, and upload the officer's completion via the web workspace.
3. Confirm equal comparison canvases, correct upload dates, and the pending card.
4. Reject as the anchor citizen. Confirm round 2, the round-1 returned photo and
   correction label in all three consumers, and exactly the same allocation.
5. Submit round-2 completion. A stale round-1 fresh request must get 409. Confirm
   as the citizen and check the saved verdict, audit and card all agree.
6. Refresh/restart the API and repeat reads; perform two full hosted reset runs.
7. Load the generated card and variants in hosted browsers. Alter verdict text
   or an image-layer reference without resigning; confirm provider rejection.
8. Measure real delivery sizes and paste the actual results, decisions,
   screenshots, test evidence and remaining limitations into the Notion journal.

## Decisions — 25 October 2026, owner: Codex

- Need: avoid another independently drifting evidence implementation. Options:
  separate card/view queries or one builder using the existing selection rule.
  Choice: one builder. Trade-off: both reads share provider delivery failures;
  tests compare the selected round, photos, label and card across consumers.
- Need: support optional originals without blocking verification. Choice: null
  before evidence and a truthful text panel. Trade-off: the comparison is less
  useful, but no picture or date is invented. Covered by API and Flutter tests.
- Need: prevent a returned attempt being presented as new repair evidence.
  Choice: carry `after_round` to Flutter and label the previous round explicitly.
  Trade-off: a small frontend change is necessary alongside the backend.
- Need: trustworthy shareable cards without extra Cloudinary uploads. Choice:
  server-signed dynamic image/text layers and explicit snapshot wording.
  Trade-off: shared URLs do not update or revoke themselves after later verdicts;
  the current application view remains authoritative.
