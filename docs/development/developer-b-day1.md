# Developer B — Day 1

This handoff covers the citizen Flutter web client and the staff Next.js client. Firebase project creation, credentials, Developer A's API and external deployment are deferred at the user's request. No live authentication/upload/persistence result should be claimed before those dependencies exist.

## What you can run without accounts

From the repository root in PowerShell:

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd --filter @janmaang/web dev
```

The staff login shows the missing-configuration state until its public Firebase values are provided. It must not invent a user or accept a browser-supplied role.

For the citizen demonstration:

```powershell
Set-Location apps/mobile
flutter pub get
flutter run -d chrome --dart-define=DEMO_SIGNED_IN=true
```

This is explicitly sample data. To test the live client's missing-configuration behavior:

```powershell
flutter run -d chrome --dart-define=USE_MOCKS=false
```

Live mode must display a configuration error instead of falling back to sample data. Future-phase operations without a live implementation must fail visibly instead of reporting success.

## Configuration to provide later

Only public client configuration belongs in these apps. Never provide a Firebase service-account JSON, Cloudinary API secret, Gemini key, database password or Redis password to the frontends.

For Next.js, copy `apps/web/.env.example` to `.env.local` and fill its `NEXT_PUBLIC_FIREBASE_*` fields and `NEXT_PUBLIC_API_URL`. Restart the dev server after editing. Build-time environment values must also be set in the hosting provider before its production build.

For Flutter, use the public Firebase dart-defines plus `API_BASE_URL` and `USE_MOCKS=false`. The API base is the origin, such as `https://your-api.onrender.com`, without a duplicated `/api/v1` prefix. Copy `apps/mobile/config/live.example.json` to `apps/mobile/config/live.local.json`, fill the public values, and run `flutter run -d chrome --dart-define-from-file=config/live.local.json` from `apps/mobile`. The local configuration is ignored by Git.

Firebase setup, when ready:

1. Create a Firebase project and register a web app.
2. Enable Authentication → Email/Password.
3. Copy the public web configuration into each client's configuration.
4. Add the actual hosted domains and local development domain to the project's relevant authorized-domain configuration.
5. Have Developer A provision Firebase accounts and corresponding local roles/scopes. Creating an identity alone does not grant a platform role.
6. Configure API CORS for exact local/hosted frontend origins, bearer Authorization and Idempotency-Key headers. CORS is not a substitute for authentication or scope checks.

## Developer A handoff

See `docs/api/day1-frontend-contract.md`. Treat it as a proposed contract to reconcile, not evidence that the API is already implemented. Required Day 1 routes are current profile, media signature/completion, report creation, report detail and the current citizen's report list.

Unsent drafts and retry keys are retained in memory across in-app navigation and cleared on account changes; closing/reloading the tab is not durable offline storage. Media caches are scoped per account.

The API must authorize reports/media itself. Role-aware client navigation only improves usability. The Cloudinary secret and signing/ownership validation stay on Developer A's backend.

## Build and verification

```powershell
pnpm.cmd --filter @janmaang/web typecheck
pnpm.cmd --filter @janmaang/web lint
pnpm.cmd --filter @janmaang/web test
pnpm.cmd --filter @janmaang/web build
Set-Location apps/mobile
flutter analyze
flutter test
flutter build web
```

On this machine the Flutter SDK's automatic version check stalled during baseline validation. The installed SDK was invoked directly with `--no-version-check`; the SDK was not upgraded or edited. Normal CLI commands above are the intended workflow. If the version check stalls, `flutter --no-version-check ...` uses the same installed SDK without that network check.

## Deployment later

- Vercel: repository root is the monorepo; use the web build, including generated design tokens, and configure the public build-time environment. Test the signed-out login route and a protected route before sharing the URL.
- Firebase Hosting: build the Flutter web app with its live configuration, serve `build/web`, and rewrite browser routes to `index.html`. Select the actual Firebase project explicitly; do not deploy the unconfigured/demo build as a live platform.
- Do not put secrets in browser bundles. Firebase web configuration is public; Cloudinary signing and Gemini remain backend-only.

Official references: [Firebase password authentication](https://firebase.google.com/docs/auth/web/password-auth), [Flutter web hosting](https://firebase.google.com/docs/hosting/frameworks/flutter), [Cloudinary signed uploads](https://cloudinary.com/documentation/upload_images).

## Paste into Notion

**Goal:** make the existing citizen UI work in a browser and prepare real client/backend integration.

**Decision:** retain Flutter/Next.js/FastAPI; replace browser filesystem photo previews with byte-backed previews. Use Firebase SDK identity and backend-resolved roles. Keep asset IDs separate from delivery URLs. Manual reporting remains possible when AI suggestions fail.

**Trade-off:** without Firebase configuration and the backend, local builds and client tests establish only client behavior. Live login, upload ownership, report persistence and hosted integration remain pending.

**Evidence:** attach the actual check results and screenshots from this implementation. Record failures and fixes honestly; do not mark the live integration gate complete from mocked tests.
