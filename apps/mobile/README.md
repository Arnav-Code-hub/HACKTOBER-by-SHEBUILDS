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

Missing configuration shows a setup screen; live mode never silently falls back
to sample data. Email/password sign-in is available through Firebase Auth.
Photo uploads use Cloudinary signatures obtained from the API; no Cloudinary
secret belongs in this app. See [Developer B Day 1](../../docs/development/developer-b-day1.md)
and [the backend contract](../../docs/api/day1-frontend-contract.md).

Day 1 implements authentication/profile verification, report creation, photo
uploads and the current citizen's report list. Clustering, ranking, ledger,
verification and other later-phase live features show an explicit unavailable
state until their backend adapters are implemented. Live persistence and
external services remain unverified until the configuration and API exist.

Google Maps surfaces stay as styled placeholders until a platform key is
provisioned; enable them with `--dart-define=MAPS_ENABLED=true`.

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
