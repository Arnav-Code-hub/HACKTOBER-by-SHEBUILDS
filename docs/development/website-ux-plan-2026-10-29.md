# Website UX Implementation Plan

**Goal:** Remove navigation and form friction while keeping the existing UI.
**Architecture:** Change the shared Next.js components and client role routing.
Keep API authorization and request formats intact.
**Tech Stack:** Existing React, Next.js, TypeScript, CSS and Vitest.
**Spec:** [Approved UX scope](website-ui-ux-design-2026-10-29.md).

## Constraints

- No new dependencies, visual redesign, deployment or Git push.
- Retain failed form values, stable retry keys and confirmations.
- Existing unrelated untracked files remain untouched.

## Review focus

- Multiple invalid fields must each have a specific accessible message.
- Failed server requests must preserve input and unchanged retry keys.
- Confirmation cancellation must restore keyboard focus without submitting.
- Department/Super Admin login must not retain an unsupported Officer route.
- Password visibility must not clear the password or submit the form.

## Tasks

- [x] Role navigation: update `src/lib/auth/roles.test.ts` for Officer-only
  access and login fallback, confirm failure, then update `roles.ts`. Run the
  routing tests; preserve every other role mapping.
- [x] Shared forms: add tests in `components/workspace/workspace.test.tsx`
  for inline errors, error-summary links/focus, confirmation/cancellation focus,
  and retained inputs. Confirm failure; update `action-form.tsx` using existing
  field IDs, money parsing and idempotency logic. Run shared component tests.
- [x] Sign-in and entry points: add a test for `login-form.tsx` password
  visibility and non-submission; implement the toggle and plain-language copy.
  Add direct citizen-app links on landing and sign-in, update obsolete landing
  copy, and add a root skip link with focusable main-content targets.
- [x] Tables and validation: name table scroll regions, enable keyboard focus,
  and keep compact buttons legible/touchable through small shared CSS changes.
  Run website unit tests, typecheck, lint, build and local browser checks.

## Execution notes

- Baseline tests require an unsandboxed run because esbuild cannot traverse the
  project configuration under the restricted filesystem.
- Read-only source inspection confirmed the Officer API rejects non-officers.
- This is local UX verification, not a repeat of hosted-account acceptance.
- Baseline: 122 tests passed. Updated suite: 126 tests passed in 18 files.
  TypeScript, lint and both production builds passed, including the final
  link-affordance adjustment. Windows CRLF-aware whitespace check passed.
- Independent static review reported no actionable regressions.
- Browser checks at the available 1102px viewport confirmed distinct entry
  points, skip-link focus, password visibility controls and no horizontal
  overflow. Exhaustive device-width and authenticated hosted checks were not run.
