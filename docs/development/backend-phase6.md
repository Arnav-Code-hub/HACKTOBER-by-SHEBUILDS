# Backend Phase 6 — partner workflows and administration

Implemented locally on 25 October 2026 on branch `test`, on top of the
uncommitted Phase 4 and 5 work. This adds no services, dependencies or database
migrations: the Phase 1 tables already cover the required records. External
accounts and the hosted demonstration remain unconfigured.

## Delivered

- Students create a team against a published statement in their district. The
  creator becomes its first member. `mine=true` lists teams by membership, not
  merely by creator or institute. Membership invitations remain out of scope.
- Institute users see and approve their own institute's teams. Approval locks
  the team; repeated approval returns the saved result without another audit
  event. Other institutes receive 404.
- Students submit only for teams they belong to, within their current institute
  and district, after institutional approval. Links must be HTTPS, without
  embedded credentials or raw whitespace. The validated URL is canonicalized
  before storage, so accepted uppercase/abbreviated HTTPS input cannot fail the
  database guard. Titles and summaries are bounded.
  A proposal neither assigns government work nor spends its allocation.
- Faculty see submissions from their current institute and district. Each can
  review a submission once, with an integer score from 1 through 5 and a comment.
  The submission row lock serializes competing reviews; the unique database
  constraint provides an additional guard. A second distinct request receives
  409; an exact retry returns the original review ID. Multiple faculty may each
  review once; `my_review` contains only the caller's own review.
- CSR users record positive integer-paise pledges against published statements
  in their district. Organization and owner come from the verified profile.
  `mine=true` includes only the caller's pledges in their current organization
  and district. Pledges always remain `pledged`; there is no payment processing.
- Team creation, submissions, reviews and pledges reserve an idempotency key,
  write business records and audit events, and save the response in one
  transaction. Failed transactions release their keys for retry.
- Government administrators inspect their own district's report/work-order
  counts, allocations, pledges and audit history. Super administrators see all
  districts. Cluster execution status takes precedence over report intake
  status. Separate monetary aggregates avoid multiplying amounts across joins.
- Audit visibility uses the event's saved affected district and historical
  actor role. It never follows the actor's later district or role. Events are
  newest first; the requested limit is bounded to 1–200 (default 50).
- Super administrators list users and active organizations and change another
  user's role/scope with a nonblank reason. Self-change returns 403. Proposed
  scope is checked for required role fields, active organizations, organization
  type and district parent before it can be flushed. Invalid changes roll back.
  Scope fields unrelated to the new role are cleared. Changed district scope
  gets an audit event in both the old and new district so both retain visibility.
  An identical already-applied PATCH is a no-op, without a duplicate event.

The admin contract and form now include `organization_id` for industry scope;
without it, switching a user to CSR would produce an unusable account. Older
responses lacking that field remain readable by the frontend. Industry changes
must explicitly supply it. User edits take effect on the next API request;
another user's already-open browser may need to sign in again to refresh its
local profile/navigation.

## Implementation boundaries

Public module services expose the operations. Cross-module joins and
transaction coordination live in `app/persistence/participation.py` and
`app/persistence/oversight.py`; modules do not import one another's private
models. Partner lists fetch labels/counts with their projection instead of
issuing queries for each displayed row.

Lists intentionally cover the narrow demonstration dataset. Pagination,
membership invitations, edits/revisions, review moderation, pledge withdrawal,
organization provisioning and account creation are outside this phase. Existing
database users must still be linked to real Firebase identities before sign-in.
Audit names reflect the user's current display name; the role and affected
district are historical snapshots.

## Local review sequence

After following [Phase 2 setup](backend-phase2.md) and configuring accounts:

1. Department: publish a problem statement.
2. Student: create a team for that statement.
3. Institute: refresh its team list and approve the team.
4. Student: refresh, then submit an HTTPS solution link and summary.
5. Faculty: refresh and submit a score/comment for that submission.
6. Industry: record a pledge against the same published statement.
7. Government admin: inspect the district summary and audit events.
8. Super admin: change a different seeded user's scope with a reason; inspect
   its audit event. Do not change the next account needed by the demonstration.

Provider doubles are confined to external authentication/media boundaries;
integration tests run business transactions against isolated PostgreSQL 16.


## Decision record — industry scope

25 October 2026 · implementation owner: Codex; human review pending.

Problem: the existing admin form could assign the industry role but could not
supply its required organization. Options were to block all role changes to
industry or extend the existing contract/form. Choice: add nullable
`organization_id`, require it for industry assignments, and clear it for other
roles. This keeps CSR usable and prevents stale scope from surviving role
changes. Trade-off: another form field; organization provisioning remains a
separate setup task. Evidence: the admin form serialization test and the
PostgreSQL scope-change/next-request profile test.


## Verification

- All 39 Phase 6 PostgreSQL integration cases pass, including the complete
  partner journey, ownership/institute/district boundaries, invalid URLs and
  amount types, URL canonicalization before storage, review concurrency,
  idempotent pledge retries, and rollback/retry after audit failure.
- All 117 web tests pass, including selecting and sending industry organization
  scope in the admin form. The production Next.js build succeeds.
- Ruff lint and formatting, strict mypy, both import-linter contracts, generated
  OpenAPI/TypeScript contracts and their type check, and web lint/type checks pass.
- The full backend regression run passed **269 tests** (four pre-existing
  deprecation warnings). That run collected before the final two URL regression
  cases were added. The final Phase 6 rerun passed **39 cases**, including both
  additions and the canonicalization fix. These runs overlap; their counts
  should not be added together. No coverage percentage is claimed because
  source lines changed while the earlier coverage run was active.

No real Firebase/Cloudinary account, live hosted deployment or cross-browser
real-account demonstration has been verified in this phase. Those gates remain
part of provider setup and Phase 8. Flutter source was unchanged in Phase 6;
its last Phase 5 results are recorded in [backend-phase5.md](backend-phase5.md).
