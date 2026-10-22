# Roles and permissions

**Write this out fully before building any dashboard.** Nine roles times twenty
permissions is the largest silent-failure surface in the platform, and getting
it wrong is a data-exposure bug, not a UI bug.

The authoritative version is code:
[`services/api/app/core/permissions.py`](../../services/api/app/core/permissions.py),
asserted by `services/api/tests/unit/test_permissions.py`. This page explains it;
that file enforces it.

## The roles

| Role | Surface | Scope | In one line |
|---|---|---|---|
| Citizen | Mobile | Own reports + local area | Reports a need, verifies the fix |
| Student | Web | Own institute | Forms teams, builds against statements |
| Faculty | Web | Own institute | Mentors, reviews, endorses |
| Institute | Web | Own institute | Manages students, faculty, projects |
| Gram Panchayat | Web | Own panchayat | Moderates and verifies local problems |
| Department | Web | Own department + district | Publishes statements, allocates funds |
| Officer | Web | Assigned problems | Field execution and updates |
| Industry / CSR | Web | Own sponsorships | Funds work, reads impact |
| Government Admin | Web | State-wide | Oversight, funding, audit |
| Super Admin | Web | Everything | Platform configuration |

## Design rules

**Endpoints require permissions, never roles.** `require(Permission.FUNDING_ALLOCATE)`,
not `if role == "department"`. Adding a role later then needs no endpoint edits.

**Scope is enforced separately from permission.** Holding `PROBLEM_MODERATE` does
not mean moderating *every* problem — a Panchayat moderates its own panchayat.
Permission answers *what*; the principal's `district_id` / `department_id` /
`institute_id` answers *which*. Both are checked.

**The web mirrors this for UX only.** `apps/web/src/lib/auth/roles.ts` hides
navigation the user cannot use. Hiding a button is not access control.

## TODO

- [ ] Scope rule per role (which rows, not just which verbs)
- [ ] Role transitions — a student graduating, an officer transferring
- [ ] Multi-role users — can one account be Faculty *and* Institute?
- [ ] Delegation — can a Department Officer act for a Department?
