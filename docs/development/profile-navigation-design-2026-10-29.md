# Role workspace navigation and tools

The user accepted these navigation ideas as useful and requested deeper,
role-specific features before implementation. Retain this baseline alongside
[the source-level workflow review](profile-workflow-review-2026-10-29.md).

## Intent

Improve navigability and add useful features to each website role dashboard.
Retain the current UI, the preceding UX improvements, API authorization and
existing business rules. The separate Flutter citizen app is outside this scope.

## Recommended approach

Extend the existing shared list and workspace components with navigation,
search and role-specific filters. This gives all profiles useful tools without
adding dependencies or new server workflows. A visual rebuild conflicts with
the user's stated preference; notifications, new assignments and other server
workflows should be scoped separately.

## Shared navigation

- Add named section shortcuts for each workspace's queues and actions.
- Provide clear ways to open details and return to the relevant list, preserving
  the user's current search/filter while the workspace stays open.
- Show search/filter result counts, distinguish no matches from no records, and
  offer a clear reset action.
- Support keyboard navigation and narrow screens using the existing components.
- Search and filter only records already returned within the account's scope;
  label this limitation. Do not present client filtering as a global search.

## Profile-specific tools

- Panchayat: search reports by code/title/location and filter by category in the
  validation and clustering queues.
- Department: search/filter ranked demands by category while preserving official
  rank order; find draft versus published problem statements.
- Officer: search assigned work and filter by current work/verification status.
- Student: search published statements and teams; filter teams by approval and
  submissions by whether feedback is available.
- Institute: search teams and switch between awaiting approval and approved teams.
- Faculty: search submissions and switch between awaiting review and reviewed by
  the current faculty member.
- Industry/CSR: search published opportunities and the account's recorded pledge
  history; keep the distinction between a pledge and a payment explicit.
- Government Admin: jump between summary and audit history; search/filter loaded
  audit events by action and actor role.
- Super Admin: the oversight tools above plus account search and role filtering.
  Role changes keep existing confirmation, reason and audit requirements.

## Boundaries and checks

No API permissions, funding rules, uploaded evidence or role ownership changes.
No new dependencies, cross-district search, fake counts, Git push or deployment.
Preserve all current approval/confirmation gates. Test filtering, resets,
empty/loading/error states, official rank preservation, role access and keyboard
navigation, then run website tests, lint, type checking and production build.
