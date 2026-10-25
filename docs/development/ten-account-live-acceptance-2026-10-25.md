# Ten-account live acceptance — 25 October 2026

## Outcome

PASS for fresh Firebase email/password sign-ins for all ten seeded role accounts, each role's committed action, and refresh persistence. Government Admin's committed action is a scoped read, not a write. This is a local browser run against real Firebase, Supabase and Cloudinary; it does not establish hosted readiness or a complete security audit.

The run was interrupted by the tool approval service's usage limit and resumed at the owner's request. The CSR pledge was not duplicated on resumption: a fresh sign-in and reload confirmed the original INR 50 record.

## What was tested

1. Citizen — signed out through Profile, returned through onboarding and entered email/password afresh. Submitted JM-5, titled DEMO ten-account test - handpump, with manually selected demonstration coordinates and approved synthetic before evidence. Full reload and Track retained it. Later reviewed actual before/after evidence, submitted a positive verdict with an explicit synthetic-test comment, and reloaded the report to confirm Citizen Verified.
2. Panchayat — fresh sign-in, validated JM-5, explicitly created a new cluster rather than altering a seeded case. Full reload retained the cluster in the ranked list at score 31.4 with one supporter and labelled demo inputs.
3. Department — fresh sign-in, created and published DEMO ten-account acceptance - handpump reliability. Full reload retained Published. A subsequent fresh sign-in recorded INR 100 for JM-5 and assigned the demo officer. Department reload excluded the funded cluster from the eligible ranking; the assigned Officer and read-only database checks independently confirmed the saved allocation and instructions.
4. Officer — fresh sign-in, opened JM-5, saw its original evidence and INR 100 allocation, saved a synthetic progress note, uploaded approved synthetic completion evidence and submitted it. Full reload retained Awaiting Citizen Verification. Original citizen subsequently verified the case.
5. Student — fresh sign-in, created DEMO acceptance team - 25 Oct for the new statement. Reload retained Awaiting approval, and the solution action was unavailable until approval. Signed in afresh again after approval and submitted DEMO solution - handpump inspection checklist. Reload retained the submission. After the admin test restored this account, another fresh Student sign-in showed its approved team, submission and one review.
6. Institute — fresh sign-in, approved that team. Full reload retained Approved.
7. Faculty — fresh sign-in, reviewed that submission with score 4/5 and synthetic-test feedback. Full reload retained Reviewed and the saved score; database confirms one review.
8. Industry/CSR — fresh sign-in, recorded INR 50 against the new statement. Another fresh sign-in and full reload retained the same single pledge. No payment was made.
9. Government Admin — fresh sign-in, inspected the Yadgir demonstration district's report/work-order counts, recorded funding and pledge totals, and audit history. Full reload retained the data. It showed the student, institute, faculty, department and CSR actions under the correct actors. No Users administration list appeared for this role. At this checkpoint recorded allocations were INR 2,600; the later JM-5 allocation raised the final database total to INR 2,700.
10. Super Admin — fresh sign-in, loaded Users and organization scopes. With explicit owner confirmation, changed the demo Student account to Citizen, reloaded and confirmed that saved role and an audit event. Restored Student with its exact original Yadgir district and Demonstration Institute; reloaded and confirmed restoration and a second audit event. The self-change form was correctly replaced by a message requiring another super administrator. Final fresh Student login proved the restored access worked.

## Persisted identifiers and independent checks

- Report JM-5: f333b6a4-4f8a-44ce-ad97-e17538cafb6e.
- Cluster: 784152cf-c84c-48d5-a9bb-cb9c4eb61730.
- Work order: 2df82ee9-84fb-4cb4-9ab8-6e1f96d0a14a.
- Statement: 79ead1ed-3fdb-4fa6-9817-43dbcde3b7d7.
- Team: 426deee5-5ec3-4eaf-89c1-a1a7a06a0cbb.
- Submission: dd5c2770-c2db-4248-b586-7d4814ffe2ed.
- CSR pledge: a8b399a6-a1a6-42b6-a559-c614f9f34f75.

Final read-only Supabase queries confirmed: citizen_verified; round 1; exactly one JM-5 allocation of 10,000 paise; exactly one positive verdict from the original reporter; published statement; approved team; one faculty review with score 4; pledged sponsorship of 5,000 paise. All ten original roles are present exactly once and active. The Student institute before the temporary change and after restoration is identical. Two user.scope_changed entries have actor_role super_admin and the owner's approved test/restoration reasons.

Final recorded district totals are 270,000 paise allocated and 5,000 paise pledged. They are records only, not transfers.

## Remaining findings

- Moderate — staff navigation permits Department and Super Admin into the Officer workspace, and the login next parameter preserves that route. Their GET work-orders request correctly fails with Only the assigned officer can update this work. Reproduced after switching roles from /officer. Selecting Department or Administration resolves it. Align route/navigation permissions with the backend's assigned-officer endpoint, or implement a separately authorized read-only order view. This does not prevent the committed role actions, but it produces an avoidable error screen during role switching.
- Moderate — citizen onboarding still displays 95% PILOT IMPACT / fewer pending demands in Yadgir without a visible demonstration label on that claim. Observed during the fresh Citizen login and present in onboarding_screen.dart. No measurement supporting it was supplied. Remove the claim or explicitly label it as illustrative demo content before judging.
- Nitpick — narrow staff layouts wrap short Open/Selected button labels across several lines. Actions remain usable; this is visual polish.

One initial Super Admin login attempt showed the generic sign-in failure; explicitly re-entering the supplied demo credentials succeeded, and later fresh logins succeeded. No password was changed; the cause of that isolated first failure was not established.

## Evidence and limits

Local screenshots, UI accessibility evidence and the independent database results are in the parent workspace's .review-artifacts/ten-accounts-20261025 directory, including final-database-evidence.json. No tokens, passwords or service-account keys were included.

All mutations above were made through the real browser forms. Database access was read-only confirmation. Existing seed cases JM-1, JM-2 and JM-3 were preserved; no reset was run. The approved before/after fixtures prominently say SYNTHETIC TEST ONLY - NO REAL REPAIR.

Not covered by this acceptance run: negative verdict/correction rounds, stale-round submissions, concurrency, failed/oversized uploads, other-district adversarial access, optional Gemini, mobile packaging or hosted deployments. Passing this test is not a production-readiness claim.

No application code was changed in this account-testing run.
