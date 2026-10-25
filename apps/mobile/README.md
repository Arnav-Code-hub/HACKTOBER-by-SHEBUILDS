# JanMaang — citizen app

Flutter. The citizen experience: report a local need by voice or photo, track it
through clustering, ranking and funding, and verify the fix.

Run everything from the repository root with `make mobile`, or from here with
`flutter run`.

## Stack

Flutter · Dart · Material 3 · Riverpod 3 · go_router · flutter_map +
OpenStreetMap. The Day 1 live path uses Firebase Auth, the FastAPI business API,
and signed Cloudinary photo uploads. Earlier Firebase Functions/rules remain
as historical reference; the live client does not write Firestore or Firebase
Storage. Gemini remains server-side and is not required to submit manually.

The brief asked for Framer Motion and Leaflet. Both are React libraries and
cannot run in Flutter, so their roles are filled by the platform equivalents:
**flutter_map** renders the same OpenStreetMap tiles under the same ODbL
attribution, and the motion system in `lib/core/theme/motion.dart` provides the
page transitions, staggered entrances, counters and press feedback. Every
animation honours the platform reduce-motion setting.

## Running it

The app runs out of the box against in-memory repositories seeded with the same
figures the designs were reviewed with, so no Firebase project is needed to see
or test the whole UI:

```bash
flutter run
```

For demos and screenshots, skip the OTP step:

```bash
flutter run --dart-define=DEMO_SIGNED_IN=true
```

Against the live backend (configuration and Developer A's API are required):

```bash
# Copy config/live.example.json to config/live.local.json and fill PUBLIC values.
flutter run -d chrome --dart-define-from-file=config/live.local.json
```

Missing configuration shows a setup screen. Email/password sign-in uses
Firebase Auth; report submission, Track and citizen verification use the
business API. These operations never silently fall back to sample responses.
Photo uploads use Cloudinary signatures obtained from the API; no Cloudinary
secret belongs in this app. See [the backend contract](../../docs/api/day1-frontend-contract.md).

Home's community pulse, nearby examples and map, plus Ranks and Public Ledger,
keep their original demo fixtures available in both modes. Each view is labelled
**Demo data**. The map shows approximate sample locations; ranks and allocations
are not a signed-in citizen's real activity or live funding records. In a live
build, sample report links open `/demo/demand/:id`, a read-only preview with no
verification or ranking-write actions. Report and Track still use the real
account and API, separately from these examples.

Live cluster-detail/suggestion adapters and ranking appeals remain unavailable.
Connecting those capabilities must not replace this explicit demo labelling with
an automatic fallback when a live request fails.

## Architecture

```
lib/
  core/        config · constants · theme · routing · services · errors · utils
  features/    onboarding auth home report demands ledger verification profile
                 each with data/ domain/ presentation/
  shared/      models · widgets (the design-system component library)
```

Repositories are interfaces in `domain/` and selected in
`lib/core/providers.dart`. Demo mode uses labelled in-memory data. The Day 1
live adapters use Firebase SDK authentication and authenticated HTTP for reports.
Later-phase live operations fail explicitly rather than using demo records.
Tests inject fake transports; they do not establish a working deployed backend.

See [../../docs/architecture/mobile.md](../../docs/architecture/mobile.md) for the data model,
the Firestore collections and the Cloud Function boundaries.

> **Migration in progress.** Per
> [ADR 0002](../../docs/architecture/decisions/0002-postgres-over-firestore.md), the
> domain is moving from Firestore to the Postgres-backed API. The repository
> interfaces in `domain/` do not change — only the datasource behind
> `data/*_repository_impl.dart`. The mock implementations stay, and remain the
> offline demo path.

## Brand and photography

Two asset slots, both with graceful fallbacks so the build never breaks on a
missing file:

- `assets/brand/` — the logo lockup and square mark. `JmLogo` falls back to a
  typographic lockup. Launcher icons, favicon and splash are generated from the
  mark via `flutter_launcher_icons.yaml` and `flutter_native_splash.yaml`.
- `assets/gallery/` — the four infrastructure photographs behind the
  auto-scrolling gallery on Home (`roads.jpg`, `transit.jpg`, `civic.jpg`,
  `water.jpg`). Until they land, each slide renders a designed gradient card
  with its icon and caption.

See the README in each directory for sizes and export settings.

## Security

No server-side credential belongs in the app. The API verifies Firebase ID
tokens and authorizes business data. Cloudinary signing and ownership checks
remain on the backend. Older Firestore rules are not the enforcement point for
the FastAPI live path. See [../../SECURITY.md](../../SECURITY.md).

## Checks

```bash
flutter analyze
flutter test

# or, from the repository root:
make test-mobile
```

## Platform status

| Target | State |
|---|---|
| Android | builds; toolchain configured against SDK 36.1.0 + JDK 17 |
| Web | builds and runs; used for UI verification in this environment |
| iOS | needs a full Xcode install (only Command Line Tools present) plus CocoaPods |
