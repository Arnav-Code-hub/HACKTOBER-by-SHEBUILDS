# Real-provider browser journey — 25 October 2026

Result: PASS for one positive report-to-verification journey on local frontends and API, using real Firebase, Supabase and Cloudinary. This is not evidence of a hosted deployment or a real public repair.

## Test case

- Report: JM-4, `5559250a-6dd9-470c-b233-7e796a46e3ac`.
- Title: E2E DEMO - handpump repair - 25 Oct 2026.
- Cluster: `4d20de9e-7145-4017-94a1-e01d293d59ef`.
- Work order: `ce5cd1c1-846c-4da7-9d7f-08ad73c997ab`, round 1.
- User approved two synthetic diagrams for public Cloudinary upload. Both say SYNTHETIC TEST ONLY - NO REAL REPAIR. Report text, officer instructions, progress note and citizen comment also identify the simulation.
- Fixed demonstration coordinates were selected manually in Yadgir. Device GPS was not accessed.
- No reset was run and existing seeded cases were not modified.

## Actions exercised through the browser

1. Citizen: entered description, title, Water category and Medium severity; pinned a location; attached the synthetic before image; submitted JM-4. Full reload retained the report and photo.
2. Panchayat: fresh Firebase email/password sign-in; reviewed JM-4 and its Cloudinary image; validated it; explicitly created a separate cluster. Ranked list showed one supporter and a score of 31.4 with demo inputs labelled.
3. Department: fresh sign-in; selected JM-4; recorded a INR 100 allocation and assigned the demo officer. No money moved.
4. Officer: fresh sign-in; saw original evidence before completion; saved progress; uploaded the synthetic after image; submitted round-1 completion. Case became awaiting_verification.
5. Citizen: original reporter opened the real before/after evidence and generated pending card; entered a synthetic-test comment; confirmed the positive verdict. Report displayed Citizen Verified.
6. Officer: refreshed the selected work order and evidence. Final card and status both showed Citizen Verified.

## Independent persistence checks

Read-only Supabase queries confirmed citizen_verified, one allocation of 10,000 paise, one round-1 positive verdict, and that the verifier was the original reporter. Audit records include creation, Panchayat validation/clustering, Department funding, Officer progress/completion and citizen verification with the corresponding actor roles. Business records survived an API restart between completion and verification.

Two owned media assets were attached to the correct report/work order. Completion evidence has round 1. The final Cloudinary card returned HTTP 200 (image/png, 18,546 response-body bytes) and visually displayed both labelled fixtures, upload dates, JM-4 and Citizen verified.

## Measured delivery

Measurements used actual Cloudinary response bodies with a browser image Accept header and identity content encoding. Original sizes are stored Cloudinary upload metadata, not the pre-upload local source file size (the citizen app re-encodes its image).

- Before: original 57,736 bytes; thumbnail 3,320 bytes (94.25% smaller); detail 8,162 bytes (85.86%); comparison panel 6,848 bytes (88.14%).
- After: original 33,109 bytes; thumbnail 3,438 bytes (89.62% smaller); detail 8,098 bytes (75.54%); comparison panel 6,748 bytes (79.62%).
- All six variants returned HTTP 200, image/webp. These results apply to these synthetic fixtures only; they are not a general savings promise.

## Defects found and corrected locally

- Moderate: Select on Map called GPS instead of opening a picker. Denied location permission prevented using the advertised manual fallback. Added a real map picker with explicit pin confirmation, existing-point preservation and cancellation. Four regression tests cover no assumed location, GPS-independent selection, cancellation and clearing an earlier GPS error.
- Moderate: long evidence-card signatures returned HTTP 401 with strict transformations in this real account. Standard signed URLs returned 200. Generator now explicitly uses the standard signature; composition-tampering tests remain enforced. Strict transformations stayed enabled.
- Moderate: Officer Refresh refetched only the work-order list, leaving the selected evidence/card at the old citizen verdict. Refresh now invalidates the work-order query family, including selected evidence. A regression test reproduces another role recording a verdict.
- Nitpick: the report photo target overflowed at narrow widths because it forced long text into a fixed height. It now uses a minimum height and grows with content; the report-screen regression tests run at 430px width without overflow.

## Automated verification

- Flutter: all 177 tests pass; changed-file Dart analysis clean; live web build succeeds.
- Backend: all 109 unit tests pass, including the 27 media/provider tests; changed backend files pass ruff lint and format checks.
- Staff web: all 119 tests pass; typecheck and lint pass.
- One initial backend unit run failed because the sandbox could not access pytest's existing temp directory; rerun with a fresh workspace temp directory passed. Initial web test invocation likewise needed access for the installed esbuild resolver; permitted rerun passed.

## Limits and evidence location

This run covers the positive journey only. It does not establish all-role live workflow coverage, concurrency/retry behavior, a negative citizen correction round, device camera/GPS behavior or hosted deployments. Optional Gemini suggestions were not called. Existing automated tests cover additional cases separately.

Local screenshots, synthetic source images, downloaded cards, public card URLs and read-only database/measurement results are under the parent workspace's `.review-artifacts/journey-20261025/`. No credentials or passwords were written into this report. No changes were committed or pushed as part of this test.
