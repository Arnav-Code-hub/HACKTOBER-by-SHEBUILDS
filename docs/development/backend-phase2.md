# Backend Phase 2 — implementation and setup

Implemented locally on branch `test` in the OneDrive checkout. The user confirmed
that Firebase, Cloudinary, Supabase and Render are not configured yet. Therefore
the hosted exit gate remains **pending**. Provider doubles used by tests do not
establish that real sign-in, Cloudinary uploads or deployment work.

## Implemented

- Firebase Admin token verification in a thread, including revocation/disabled
  identity checks. Initialization is lazy and serialized across concurrent first
  requests. Unconfigured authentication returns 503; bad tokens return 401;
  unknown, disabled or invalidly scoped database accounts return 403.
- Roles and organization scope come from PostgreSQL. The Firebase UID identifies
  the account; client role fields and token role claims grant no permissions.
- `GET /api/v1/users/me`.
- `POST /api/v1/media/signature` and `POST /api/v1/media/complete`.
  Migration `0002` adds durable upload intents, taking the schema to 19 tables.
  Only citizens upload report photos; only officers upload completion photos.
- Upload authorization uses a server-generated public ID under the user's own
  folder, a signed preset, allowed formats and `overwrite=false`. All multipart
  parameters are strings. Secrets stay on the API.
- Completion locks the intent, verifies ownership and response signature, then
  fetches Cloudinary Admin metadata. It checks public ID, version, resource and
  delivery type, JPEG/PNG/WebP format, size, dimensions and upload date before
  attaching a local media record. Declared and provider byte sizes must agree;
  leave incoming transformations disabled in the preset.
- Three-photo maximum on report submissions. Photos must be the citizen's own
  unused report assets. Stable row-lock ordering prevents concurrent submissions
  consuming the same photo twice. Completion retries reuse the original media ID.
- Fifteen-minute upload window by default. An image uploaded within the window
  can still be completed after an API outage; an upload made after expiry fails.
- Signed `c_limit` image delivery with bounded 320×320 thumbnails and 1280×1280
  detail variants, `f_auto,q_auto`, preserving aspect ratio.
- `POST /api/v1/reports`, `GET /api/v1/reports?mine=true`,
  `GET /api/v1/reports/{id}`. Citizens see only their own reports in their assigned
  district. Staff report actions remain Phase 3 work and return 403 here.
  Lists accept `limit` (default 100, maximum 200) and `offset` (default 0).
- Report creation reserves the request key before business writes; report,
  media attachment, audit and stored response commit together. Same key/payload
  replays the original 201; a different payload conflicts. Effective status uses
  the shared lifecycle selector and real transition timestamp.
- Request transactions finish before a success response is sent. FastAPI's
  `scope="function"` dependency support requires the raised minimum version;
  the lockfile is updated. A failed commit produces an error and leaves no report.
- OpenAPI and generated TypeScript contracts. Existing Dart HTTP adapters keep
  their explicit mappings; their requested fields match these endpoints. No Dart
  generator is claimed to exist.
- Production startup runs migrations before one Uvicorn worker, respecting
  Render's `PORT`. A free-service Render Blueprint is supplied in `render.yaml`.

Authentication follows [Firebase's token verification API](https://firebase.google.com/docs/auth/admin/verify-id-tokens).
The transaction dependency timing follows [FastAPI's scope documentation](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/).
Upload signing and response checks follow [Cloudinary signatures](https://cloudinary.com/documentation/authentication_signatures).

## 1. Configure Firebase

Create a Firebase project and register a web app. Enable Email/Password in
Authentication. Add `localhost` and the actual hosted frontend domains to the
authorized domains list. Copy the web app's public config for both frontends.
Phone SMS and the legacy Firestore business functions are not needed.

Create at least the citizen email/password account in Firebase Authentication.
For the later demonstration, create the remaining nine role accounts as well.
Copy `services/api/seeds/demo/users.json` to the gitignored
`services/api/seeds/demo/users.local.json`. Replace the null Firebase UIDs for
accounts you created. Null entries stay disabled. Do not put passwords in JSON.

Download a Firebase Admin service-account JSON and keep it outside the repository.
For local development, set `FIREBASE_PROJECT_ID` and
`FIREBASE_CREDENTIALS_PATH` to that file's absolute path in the API `.env`.
For Render use the server-side `FIREBASE_CREDENTIALS_JSON` secret instead.
Both must refer to the same Firebase project used by the frontends.

## 2. Configure Cloudinary

Create a product environment and note its cloud name, API key and API secret.
Set these only in `services/api/.env` or Render's environment settings.

Create a **signed** upload preset named `janmaang_signed`, or set
`CLOUDINARY_UPLOAD_PRESET` to your chosen name. Allow `jpg,jpeg,png,webp` and let
the signed request specify the public ID. Keep incoming transformations,
filename-based public IDs, folder/prefix overrides and automatic format
conversion off. The originals must retain their format and bytes for completion
verification. Do not enable paid add-ons.

Cloudinary's current documentation says upload presets do **not** support a
per-preset size cap. This implementation checks 10,485,760 bytes on the client,
at authorization and again against actual Admin metadata at completion. It does
not claim that a preset rejects oversized network transfers.
[Cloudinary upload preset documentation](https://cloudinary.com/documentation/upload_presets).

Enable Strict transformations for the hosted demo and test the generated signed
thumbnail/detail URLs. Before/after comparisons, evidence cards and measured
delivery savings remain Phase 5 work.

## 3. Run the API locally

From the repository root, copy `services/api/.env.example` to
`services/api/.env`, then configure Firebase and Cloudinary as above. Use a
generated `AUTH_SECRET` of at least 16 characters. Leave Redis unset.

Start only the local database:

```bash
docker compose -f docker-compose.prototype.yml up -d postgres
```

From `services/api`:

```bash
uv sync --frozen --all-groups
uv run alembic upgrade head
uv run python -m app.seeds --users-file seeds/demo/users.local.json
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The example database URL selects this local PostgreSQL. Use exact frontend
origins in `CORS_ORIGINS`, such as `http://localhost:3000,http://localhost:8080`.
`GET http://localhost:8000/health` is public. `/docs` exposes the local API schema.

Docker-only API startup is also possible with the prototype Compose file, but
apply `alembic upgrade head` and run the seed command inside the API container
before using its business endpoints.

## 4. Connect the existing frontends

Copy `apps/mobile/config/live.example.json` to the ignored `live.local.json` in
the same folder. Set `USE_MOCKS` to `false`, `API_BASE_URL` to
`http://localhost:8000`, and fill the public Firebase web configuration.
From `apps/mobile`:

```bash
flutter run -d chrome --web-port=8080 --dart-define-from-file=config/live.local.json
```

For the staff workspace copy `apps/web/.env.example` to `.env.local`, fill the
public Firebase values and `NEXT_PUBLIC_API_URL`, then run the existing Next.js
development command. The profile endpoint works for provisioned staff; their
remaining dashboard data/actions are implemented in later phases.

Use the API origin only in both clients; they append `/api/v1`. Firebase Admin,
Cloudinary secret and database credentials never belong in client configuration.

## 5. Prepare Supabase and Render

Create a dedicated demonstration Supabase project. Copy its **session-pooler**
URL and use the `postgresql+asyncpg://` driver prefix. Preserve the
project-specific username and session port. Percent-encode special characters
in the password. Only the API connects to this database.
[Supabase connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres).

Grant Render access to this private GitHub repository. After these changes have
been reviewed and pushed, create a Blueprint from `render.yaml`, selecting
branch `test`, or create an equivalent Docker web service with:

- Docker context `services/api`, Dockerfile `services/api/Dockerfile`.
- `ENVIRONMENT=staging`, the dedicated `DATABASE_URL`, server Firebase and
  Cloudinary settings, `CLOUDINARY_UPLOAD_PRESET`, and a generated `AUTH_SECRET`.
- `CORS_ORIGINS` containing the exact hosted Flutter and Next.js origins.
- Public health path `/health`. Keep the image's default startup command:
  `python -m app.start`. It migrates first and runs one worker on `$PORT`.

The Blueprint requests `plan: free` and disables automatic deployments.
Confirm eligibility/capacity in your account before creating it.
[Render Blueprint specification](https://render.com/docs/blueprint-spec).

Seed the hosted database using the same command from a trusted local API
environment configured with its database URL and your ignored users file.
This does not require keeping seed UIDs or passwords in Render's source tree.
Leave reset disabled. For an intentional demo reset use the Phase 1 guard and
the exact hosted username/host/port/database identity.

Set both hosted clients' API origins to the Render HTTPS URL, rebuild their
public configuration, and add their domains in Firebase. Warm the API before
judging because a free service can sleep.

## 6. Verify the live exit gate

This checklist is **not run yet** because provider accounts are not configured:

1. Sign into the Flutter app with the provisioned Firebase citizen account.
2. Upload an approved JPEG/PNG/WebP photo, submit a report, and record its code.
3. Refresh and reopen Track/detail. The same report, image and code must appear.
4. Restart the API and repeat the read. Business data must remain in Postgres.
5. Retry a failed completion/submission. Confirm one report and one media asset.
6. Verify another citizen cannot read that report or use its media.
7. Verify thumbnail/detail URLs on the hosted pages with Strict transformations.

Local automated checks cover these boundaries with real PostgreSQL and mocked
provider responses; SDK adapter tests also check real signing utilities and the
Firebase verification call. They do not replace this live checklist.

Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run mypy app`, and `uv run lint-imports` from `services/api`.

Local verification: **140 tests passed** against PostgreSQL 16; Ruff lint and
format checks, strict mypy, module boundaries, OpenAPI drift check, and generated
TypeScript type checking passed. Four pre-existing deprecation warnings remain.
The production Docker image also built and passed a disposable PostgreSQL smoke
test: automatic migration to `0002`, startup on an explicitly configured port,
public health, and an explicit 503 for unconfigured Firebase. The build CA was
absent from the running image.

For local networks with a trusted HTTPS-scanning CA, the Dockerfile accepts an
optional BuildKit secret named `build_ca`. Supply a PEM for your already-trusted
public CA with `docker build --secret id=build_ca,src=/path/to/ca.pem ...`.
It is used only during dependency installation and is not copied into the image.
TLS verification stays enabled. Normal hosted builds need no such secret.

Generate contracts with `uv run python -m app.export_openapi`, then from the repo
root run `pnpm --dir packages/contracts exec openapi-typescript
openapi/openapi.json -o src/generated/api.ts`. The Bash wrapper is
`scripts/gen-contracts.sh`. No database or live provider connection is needed
for schema export, but the API's required settings must exist.

## Decision record — 24 October 2026, owner: Codex

- Need: prove a Cloudinary asset came from an upload issued to this caller.
  Options: trust arbitrary URLs, encode a stateless token, or persist intent
  identity/expiry/completion. Choice: a separate `0002` intent table. Trade-off:
  one extra table and query; retries and ownership survive process restarts.
- Need: avoid success before commit. Choice: function-scoped transaction
  dependencies. Trade-off: a newer FastAPI minimum; tested commit failures return
  an error and roll back report, media attachment, audit and idempotency state.
- Need: preserve a timely upload during an API outage. Choice: validate its
  provider upload timestamp against the intent window, rather than expiring
  completion retries solely by wall-clock time.
- Need: fit the demo deployment and preserve migrations. Choice: one worker and
  migration-first startup. Trade-off: startup waits for migration completion;
  deployment tests and live provider checks remain distinct evidence.

Expired/invalid remote-asset cleanup, broad rate limiting and staff workflows are
not implemented here. Rejected references never trigger deletion of another
user's asset. Existing Phase 1 reset semantics now include `upload_intents`.
