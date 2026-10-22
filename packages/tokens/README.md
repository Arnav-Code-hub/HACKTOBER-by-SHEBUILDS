# `@janmaang/tokens`

One JSON source of design tokens → CSS custom properties (web) **and** Dart
constants (mobile).

```
src/tokens.json
   ├─► dist/tokens.css                              apps/web
   └─► apps/mobile/lib/core/theme/janmaang_colors.dart   apps/mobile
```

## Why this package exists

The five-tier density palette is load-bearing: the README commits to the map
legend and the wordmark being the same colours. The moment the web platform
exists, that palette exists twice — and two copies of a brand palette diverge.

This is the *right* kind of sharing: a data file, generated into each ecosystem's
native form. Compare with UI components, which are **not** shared — React and
Flutter have nothing in common at the component level. Share tokens, not widgets.

## Rules

- Edit `src/tokens.json` only. Never edit generated output.
- `pnpm --filter @janmaang/tokens build` regenerates both targets.
- Colour is never the only signal — tiers also carry size and weight changes, so
  the ranking survives greyscale and colour-blindness.
