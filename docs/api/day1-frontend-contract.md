# Day 1 frontend/backend handoff

Status: proposed integration contract implemented by Developer B's clients. Developer A must implement or explicitly reconcile it before a live integration test. No backend endpoint is claimed to exist yet.

## Shared conventions

- `API_BASE_URL` / `NEXT_PUBLIC_API_URL` is the API origin, such as `http://localhost:8000`. Clients append `/api/v1` exactly once.
- Business requests carry `Authorization: Bearer <Firebase ID token>`. Passwords are sent only to Firebase through its client SDK.
- The API verifies the token, resolves the Firebase UID to a local user, and enforces role, district, department, assignment and ownership. Client navigation is not authorization.
- JSON uses snake_case. Datetimes are ISO-8601 UTC strings. IDs are opaque strings.
- Non-2xx responses are errors; the client must not treat a login, upload, or report as successful until the relevant operation succeeds. `detail` may be a safe message or a FastAPI validation-error list.
- An empty list is returned as `{"items": []}`. A missing feature returns an explicit error, never a fabricated success.

## Current profile

`GET /api/v1/users/me`

```json
{
  "id": "local-user-id",
  "firebase_uid": "verified-firebase-uid",
  "role": "citizen",
  "display_name": "Demo Citizen",
  "email": "citizen@example.com",
  "district_id": "district-id",
  "department_id": null,
  "institute_id": null
}
```

Roles: `citizen`, `student`, `faculty`, `institute`, `panchayat`, `department`, `officer`, `industry`, `gov_admin`, `super_admin`.

Return 401 for invalid authentication and 403 for an authenticated but unprovisioned/disabled account. A browser-supplied role or UID is never authoritative.

## Photo upload

1. `POST /api/v1/media/signature`

```json
{"filename":"handpump.jpg","content_type":"image/jpeg","bytes":123456,"kind":"report"}
```

Response:

```json
{
  "upload_id": "server-upload-intent-id",
  "upload_url": "https://api.cloudinary.com/v1_1/YOUR_CLOUD/image/upload",
  "parameters": {
    "api_key": "PUBLIC_CLOUDINARY_API_KEY",
    "timestamp": "SERVER_TIMESTAMP",
    "signature": "SERVER_GENERATED_SIGNATURE",
    "public_id": "SERVER_GENERATED_ASSET_ID",
    "overwrite": "false"
  }
}
```

The backend returns the complete exact parameter set, including any signed preset, folder or context. The client forwards those values unchanged with the image as multipart `file`. It must not attach the Firebase bearer token to Cloudinary. Only HTTPS `api.cloudinary.com` upload destinations are accepted.

2. Upload the actual image directly to that URL.
3. `POST /api/v1/media/complete`

```json
{"upload_id":"server-upload-intent-id","public_id":"SERVER_GENERATED_ASSET_ID","version":1234567890,"signature":"CLOUDINARY_RESPONSE_SIGNATURE"}
```

Response:

```json
{"id":"local-media-id","url":"https://res.cloudinary.com/...","thumbnail_url":"https://res.cloudinary.com/..."}
```

The API verifies the asset against the authenticated caller's upload intent, image type, format, size, expected ID and upload result. An ownership failure must never cause deletion of another user's asset. Completion is idempotent. Clean up only expired/rejected assets proven to belong to the caller's own issued intent.

The final report accepts at most three attached media IDs. Allowed formats are JPEG, PNG and WebP, with a maximum of 10 MiB per selected file (10,485,760 bytes); backend and frontend must use this same byte limit. Client checks improve feedback; server checks remain required. Cloudinary/API secrets never enter either frontend.

## Reports

`POST /api/v1/reports` with a stable `Idempotency-Key` header for retries of the same logical submission. Scope keys to the authenticated user, reject a reused key with a different payload, and return the same saved report for an exact retry:

```json
{
  "transcript": "The handpump has stopped working.",
  "title": "Handpump repair",
  "category": "water",
  "severity": "medium",
  "summary": "The handpump has stopped working.",
  "latitude": 16.76,
  "longitude": 77.14,
  "location_label": "Ward 4",
  "channel": "text",
  "media_ids": ["local-media-id"]
}
```

The API derives reporter identity and district from the verified principal and trusted geography. It validates media ownership, count, ranges, text lengths and enums. Category/severity entered by the citizen are provisional suggestions, not trusted ranking inputs. Report creation must work without Gemini success.

`GET /api/v1/reports/{id}` and the creation response return a report read DTO. `GET /api/v1/reports?mine=true` returns `{"items":[...report read DTOs...]}`. Scope report reads server-side.

```json
{
  "id": "report-id",
  "code": "YDG-WTR-0001",
  "title": "Handpump repair",
  "description": "The handpump has stopped working.",
  "transcript": "The handpump has stopped working.",
  "reporter_id": "local-user-id",
  "category": "water",
  "severity": "medium",
  "status": "reported",
  "ward": "Ward 4",
  "district": "Yadgir",
  "latitude": 16.76,
  "longitude": 77.14,
  "created_at": "2026-10-21T10:00:00Z",
  "media": [{"id":"local-media-id","url":"https://res.cloudinary.com/...","thumbnail_url":"https://res.cloudinary.com/..."}]
}
```

Submission media IDs and display URLs are separate fields. Do not put bare IDs into `photoUrls`. Advanced score, cluster and timeline fields may be added later; absence must not turn into invented live figures.

## Optional suggestion

`POST /api/v1/reports/suggest` accepts `{"transcript":"..."}` and returns category, severity, title, summary, mentioned_location and detected_language. This endpoint is optional on Day 1. Failure must leave manual entry/submission available. It must not create or imply a persisted report.

## Integration gate

With real Firebase configuration, a seeded citizen account and the API running: sign in, upload one image, submit a report, refresh, read the same report and image, restart the API, and read it again. The gate is pending until performed against the actual backend; client tests cannot establish database persistence.
