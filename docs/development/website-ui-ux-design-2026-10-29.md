# Website UX improvements

## Direction

The user clarified that the UI is satisfactory and wants UX improvements only.
Keep current colors, typography, layouts and branding. Use ui-ux-pro-max and
frontend-design for interaction and accessibility guidance; add no packages.

## Scope

- Provide citizen-app links on landing and sign-in, and replace outdated and
  technical guidance with plain language. Keep the current page structure.
- Keep Department and Super Admin out of the Officer workspace and its preserved
  login destination, matching the assigned-officer API. Retain their other access.
- Identify invalid fields inline in shared forms, link to them from a focused
  error summary, and preserve entered values and retry/idempotency behavior.
- Manage keyboard focus for confirmation, cancellation and saved feedback.
- Add an accessible show/hide password control without changing authentication.
- Add skip-to-content links and keyboard-scrollable table regions. Keep action
  labels readable and controls usable on narrow screens.

## Approaches considered

1. UX-only changes in shared components: proposed. Fixes repeated friction across
   the role workspaces while retaining the current appearance.
2. Visual redesign: rejected by the user; the current UI is satisfactory.
3. Notifications and offline features: deferred; require separate product and
   backend work.

## Boundaries

This covers the Next.js website, not the separate Flutter citizen application.
Keep existing API requests, role permissions, funding, uploads and workflow
transitions intact. Do not introduce demo credentials or sample impact claims.
Use the existing automatic light/dark theme support and verify both themes.
No deployment or Git push is included.

## Validation

Run website unit tests, type checking, lint and production build. Add tests for
field errors, confirmation focus, password visibility and corrected role routing.
Check keyboard navigation and narrow layouts locally. Simulated browser checks
do not establish hosted-account acceptance.
