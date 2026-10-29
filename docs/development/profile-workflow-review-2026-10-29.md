# JanMaang role workflow review and proposed additions

Reviewed 29 October 2026. This is a source-level review of the website and its
FastAPI contracts, not a fresh live-account acceptance test. Existing visual
design and previously implemented UX improvements are retained.

The user accepted the usefulness of the navigation/search/filter proposal and
asked for deeper role-specific improvements. That baseline remains in
[the navigation proposal](profile-navigation-design-2026-10-29.md). The additions
below are recommendations, not implemented features or approved backend changes.

## Main finding

The opportunity is to complete the handoffs between roles. A stored action does
not always give the next person enough information to continue. No Critical
failure was established by this review; the confirmed gaps below are Moderate.

## Confirmed gaps

### Moderate: Panchayat cannot inspect a candidate cluster's underlying evidence

The clustering selector shows a title, distance and counts. It does not let the
reviewer compare the candidate's anchor photo, full description and member
reports. Two nearby problems with similar titles can be grouped without enough
context. Add a scoped cluster-detail read and comparison before confirmation.
Evidence: `apps/web/src/features/problems/components/panchayat-workspace.tsx:185`
and `services/api/app/modules/problems/clusters.py:116`.

### Moderate: Panchayat cannot correct a provisional category

Validation accepts only verify/reject and a reason. A drainage report submitted
as roads keeps that category when validated, affecting clustering and department
responsibility. Add audited category correction before clustering; changing the
ownership of already-funded work requires a separate rule.
Evidence: `services/api/app/modules/problems/schemas.py:107` and
`services/api/app/modules/problems/clusters.py:105`.

### Moderate: Department has no operational follow-through view after funding

Funded demands correctly leave the open ranking, but selected case details are
also derived from that ranking. The Department workspace has no replacement list
for assigned work, progress notes and citizen verdicts. Add a responsible-
department work list; do not restore access to Officer-only update endpoints.
Evidence: `apps/web/src/features/funding/components/department-workspace.tsx:37`,
`services/api/app/modules/problems/clusters.py:129` and
`services/api/app/modules/problems/work_orders.py:158`.

### Moderate: Officers cannot read why the citizen returned the work

The correction notice identifies the round but omits the reporter's stored
comment. An officer can repeat an incomplete repair without knowing what still
failed. Extend the scoped evidence read with the previous verdict/comment and
display it beside the relevant round's evidence.
Evidence: `apps/web/src/features/departments/components/officer-workspace.tsx:155`,
`services/api/app/modules/problems/models.py:124` and
`services/api/app/modules/problems/schemas.py:255`.

### Moderate: Student feedback has no return path

Students see only a review count in their submissions table. The response's
`my_review` is joined to the current caller's reviewer ID, so it does not supply
faculty feedback to the student. Add an authorised team-feedback read and a
submission detail view; showing another user's review needs a scoped contract.
Evidence: `apps/web/src/features/teams/components/student-workspace.tsx:231` and
`services/api/app/persistence/participation.py:230`.

### Moderate: Team formation has no join or invitation flow

Creating a team adds its creator. Current team endpoints expose list, create and
approve, without membership invitations or joining. A student cannot assemble a
multi-person team through this website. Add consent-based, institute-scoped
invitations, roster visibility and membership checks; do not add people silently.
Evidence: `services/api/app/modules/teams/router.py:16` and
`services/api/app/persistence/participation.py:180`.

### Moderate: Institute approval cannot request changes

The institute sees a member count and can approve, but cannot inspect a full
roster or send a reasoned request for changes. A team that is not ready can remain
pending with no explanation to its students. Extend the team workflow with a
recorded request-for-changes outcome and team-visible response.
Evidence: `apps/web/src/features/teams/components/institute-workspace.tsx:63`,
`services/api/app/modules/teams/router.py:37` and
`services/api/app/persistence/participation.py:202`.

### Moderate: CSR scope wording overstates the returned data

The empty message says the organisation has not pledged. The API actually lists
pledges by both the current user and organisation. A second representative can
see an empty history while a colleague has recorded a pledge. Label the existing
view as personal pledge history. Organisation-wide visibility needs a deliberate
permission and contract, not removal of the user filter.
Evidence: `apps/web/src/features/funding/components/industry-workspace.tsx:151`
and `services/api/app/persistence/participation.py:410`.

### Moderate: Older audit events cannot be reached

The website requests the newest 50 events. The API allows a limit up to 200 but
has no cursor, so an investigator cannot reach older events by paging. Add
stable cursor pagination with scoped case/date filters; increasing the limit
alone only postpones the cutoff.
Evidence: `apps/web/src/features/admin/hooks.ts:16`,
`services/api/app/modules/audit/router.py:47` and
`services/api/app/persistence/oversight.py:92`.

### Moderate: Audit details omit the changes that were made

The database stores before/after values but the response exposes only action,
actor, entity, time and reason. The screen cannot show which department or scope
changed. Add an authorised event-detail projection with action-specific fields,
not an unrestricted dump of potentially sensitive snapshots.
Evidence: `services/api/app/modules/audit/models.py:23` and
`services/api/app/modules/audit/schemas.py:49`.

### Moderate: Super Admin scope changes are difficult to review safely

Organisation options lack district relationships, allowing incompatible
selections that the backend then refuses. Confirmation names only the role,
omitting the effective old/new scope. Add dependent choices and a named access
comparison. Keep server validation, the self-change restriction and the existing
protection against stranding open officer work.
Evidence: `apps/web/src/features/admin/components/admin-workspace.tsx:240`,
`apps/web/src/features/admin/components/admin-workspace.tsx:351` and
`services/api/app/modules/audit/schemas.py:38`.

## Distinctive JanMaang features to build on these fixes

### Shared: Demand Passport

One permission-aware case page connects the original report, grouped demand,
ranking explanation, recorded allocation, assigned work, evidence and reporter's
verdict. Each role gets a link to the same case but sees only authorised fields.
This extends the existing history and evidence cards rather than replacing them.
Any public version must redact private identity/location data and label demos.

### Shared: Next action and waiting reason

Show which role is responsible now, what information is missing and when the
case entered that stage. Derive this from saved workflow events. Display elapsed
time, not invented overdue or SLA violations. Do not let AI decide who receives
funding or whether a repair is accepted.

### Panchayat: Same-demand comparison and clarification

Compare proposed cluster matches side by side, including anchor evidence,
locations and the effect on unique community support. Show which original report
will retain verification authority. Add structured clarification requests for
incomplete citizen reports rather than forcing rejection or uninformed approval.

### Department: Allocation-to-verification board and decision receipt

Follow every assigned case through work and citizen verification. Preserve the
ranking factors, official inputs, amount, assigned officer and decision note as
they stood when funding was recorded. This explains a historical choice even
after rankings change. Allocations remain records, not expenditure or payments.

### Officer: Correction brief and completion checklist

Bring the original demand, reporter's rejection reason, round-specific photos,
instructions and current responsibilities into one work brief. A category-specific
completion checklist can make photo submissions more useful. Acceptance criteria
must be explicitly defined; photos or checklist ticks never auto-close the case.

### Student: Civic Buildfolio and feedback-to-revision flow

Show team contributions, submitted solutions, received faculty feedback and
revision history linked to the original civic demand. Distinguish a reviewed
proposal from a solution formally adopted by a department and from a verified
repair. Add actual team invitations before presenting team counts as collaboration.

### Institute: Team readiness review

Show the consenting roster, chosen civic problem, submitted work and review
progress before approval. Support approval or a reasoned request for changes.
Separate student participation from measured public impact.

### Faculty: Civic feasibility rubric and revision requests

Extend the current score/comment review with clearly defined criteria such as
feasibility, maintenance, accessibility and relevance to the demand. Return
feedback to the team and review explicit submission versions. An adoption
recommendation is advice to a department, never an allocation or repair approval.

### Industry/CSR: Pledge-to-outcome dossier

Follow the published statement, authorised student progress and any formally
linked civic work/evidence. Show commitments separately from government
allocations, transfers and verified outcomes. These connections require explicit
data relationships; matching titles do not prove a pledge funded a repair.

### Government Admin: Handoff and correction oversight

Surface work awaiting citizen review, repeated correction rounds and waiting
times with the responsible department. Link every flag to the evidence and audit
history. These are review signals, not findings of fraud or automatic escalation.

### Super Admin: Access-change preflight

Before confirmation, show old/new role and organisation, compatible scope
choices, and any open work that blocks the move. Add an accessible explanation of
which workspaces the new role permits, while keeping backend enforcement.

## Recommended build order

1. Fix the lost-information handoffs: student feedback, officer correction
   comments, Department post-funding tracking and safe admin confirmation.
2. Add the retained navigation/search/filter tools alongside the Demand Passport
   and next-action view, using the new scoped reads.
3. Complete team collaboration and institute requests for changes.
4. Add historical decision receipts, structured faculty reviews, Civic Buildfolio
   and pledge-to-outcome views once their data relationships are explicit.

No website/backend code, live data, roles or credentials were changed in this
review. No claim of global uniqueness, real fund transfers or measured impact is
made for these proposals.
