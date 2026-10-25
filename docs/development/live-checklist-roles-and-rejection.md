# Live checklist — remaining roles, rejection path, repeats and failures

Purpose: finish proving the prototype locally against real Firebase, Supabase
and Cloudinary before deploying. The 25 October journey
([live-journey-2026-10-25.md](live-journey-2026-10-25.md)) covered Citizen,
Panchayat, Department and Officer on the positive path. This checklist covers
the six untested roles, the citizen rejection and correction round, repeated
requests and failures.

Starting data in Supabase (25 October 2026): 2 published problem statements,
2 approved teams, 2 submissions, 1 pledge; clusters — 1 prioritised, 1
in progress (seeded case), 1 citizen verified (JM-4).

**Everything done here is saved permanently in Supabase** (reset is blocked
there, as it should be). Use clearly labelled test text and photos marked
SYNTHETIC TEST ONLY.

**After every step:** sign in fresh (sign out first or use a private window),
do the action, then **refresh the page** and confirm it is still there.

## 0. Setup (5 min)

- [ ] API healthy at <http://localhost:8000/health> (launcher with the CA bundle).
- [ ] Staff web app at <http://localhost:3000>.
- [ ] Citizen app in live mode on port 8080 (allowed by CORS). From `apps/mobile`:

  ```bash
  flutter run -d chrome --web-port 8080 --dart-define-from-file=config/live.local.json
  ```

- [ ] Two synthetic photos ready ("before" and "after, round 2") and one
      non-image file.
- [ ] A results sheet: step, pass/fail, and the exact message if it fails.

## A. The six untested roles (in this order — each depends on the last)

1. **Student** (`/student`)
   - [ ] Create a team (for example "TEST team 25 Oct") for a published statement.
   - [ ] Refresh: it shows under "Your teams", awaiting approval.
   - [ ] Try "Submit solution" now. Expect a refusal: "Your institute must
         approve the team before submission."
2. **Institute** (`/institute`)
   - [ ] The new team appears under "Teams at your institute". Approve it.
   - [ ] Refresh: it shows as approved.
3. **Student** again
   - [ ] Submit a solution (title and an `https://` link).
   - [ ] Refresh: it is listed under "Your submissions".
4. **Faculty** (`/faculty`)
   - [ ] The submission appears under "Submissions to review". Submit a review.
   - [ ] Refresh: your review shows. Try reviewing it again; expect "You have
         already reviewed this submission."
5. **Industry/CSR** (`/industry`)
   - [ ] Record a pledge (for example ₹100) on a published statement.
   - [ ] Refresh: it is under "Your pledges". Nothing should suggest money moved.
6. **Gov admin** (`/admin`)
   - [ ] The summary shows your district only.
   - [ ] "Reports by status", "Work orders by status", allocated and pledged
         amounts (now including the ₹100) look right.
   - [ ] The audit trail lists the team, approval, submission, review and
         pledge, each with the correct person and role.
   - [ ] You **cannot** see the Users list or change roles (super admin only).
7. **Super admin** (`/admin`)
   - [ ] The Users list loads.
   - [ ] **Try changing the Officer's role or department.** The seeded case
         still has open work, so expect a 409 explaining the officer has open
         work orders (audit fix check).
   - [ ] Change a harmless account (for example the Student's institute or
         role) with a reason. Refresh, check the audit trail, then **change it
         back**.
   - [ ] Try changing your own role. Expect a refusal.

## B. Rejection path — on the seeded in-progress case

8. **Officer** (`/officer`): open the in-progress work order.
   - [ ] The citizen's original photo shows before any completion.
   - [ ] **Open the same order in a second tab and leave it** (used in step 11).
   - [ ] Save a progress note, upload the synthetic "after" photo, submit for
         citizen verification. Status becomes awaiting verification.
9. **Citizen** (the original reporter of that case), in the Flutter app
   - [ ] Open the report: before/after evidence and a verify prompt.
   - [ ] **Return it as not fixed** with a comment ("TEST: still broken").
   - [ ] Refresh: it shows as returned, with no verify button.
10. **Officer**, first tab
    - [ ] Refresh: it shows "correction round 2", and the photo caption reads
          "Round 1 · returned by the citizen".
11. **Officer, second (old) tab** — still showing round 1
    - [ ] Try submitting completion photos. Expect a 409 message and nothing
          attached (stale-completion fix check).
12. **Officer**, first tab
    - [ ] Upload the round-2 photo and submit.
13. **Citizen**
    - [ ] Round-2 evidence shows. **Confirm it as fixed.**
    - [ ] Refresh: the report shows Citizen Verified.
14. **Officer**
    - [ ] Press Refresh: the evidence card and status show Citizen verified.
    - [ ] The card shows round 2, and the round-1 photo is still kept.

## C. Repeats and failures

15. **Funding the same case twice** (Department, the prioritised cluster)
    - [ ] Open it in two tabs and fund from both. One succeeds; the other shows
          a 409 "already funded" message.
    - [ ] Gov admin's allocation total rises once, not twice.
    - Note: this uses up the last prioritised cluster. Skip it if you want one
      for the demo.
16. **Failed upload**
    - [ ] Pick the non-image file (or one over 10 MB): a clear error, and
          nothing attached.
17. **Restart**
    - [ ] Restart the API in the middle of section B. Sign in again: everything
          done so far is still there.

## D. When something fails, record

- Step number, role, and the exact on-screen message.
- The time, to match it to the API log.
- A screenshot.

**Expected time:** about 60–90 minutes; section A takes longest because of the
sign-ins. If everything passes, move on to deployment (Render, Vercel,
Firebase Hosting).
