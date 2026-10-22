# `@janmaang/ui`

React primitives shared across the web app's role dashboards.

**Web only.** React and Flutter share nothing at the component level, so the
mobile app does not consume this package — it consumes `@janmaang/tokens` and
renders its own `Jm*` widgets. Share tokens, not components.

Domain-specific components (a problem card, a funding row) live in
`apps/web/src/features/*/components`, not here. This package holds primitives
only: button, dialog, table, field. If a component knows what a "problem" is,
it does not belong here.
