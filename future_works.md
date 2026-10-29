# JanMaang Future Work

This file tracks possible improvements beyond the current prototype. None of the
items below should be treated as complete until implemented and tested.

JanMaang already records workflow and audit history, supports correction rounds,
and groups related reports. The ideas below should extend those features.

## Next improvements

- [ ] **Citizen notifications:** Tell the reporter when a demand is reviewed,
  funded, assigned, or ready for verification.
- [ ] **Similar-report prompt:** Before submission, show nearby related demands so
  the citizen can support an existing one instead of creating a duplicate.
- [ ] **Clear progress timeline:** Present the existing audit history as an easy
  report-to-verification timeline, with the person or role and time for each step.
- [ ] **Correction request experience:** Make it easier for the original reporter
  to explain why work is incomplete and attach new evidence for another review.
- [ ] **Accessibility improvements:** Review screen-reader support, text size,
  contrast, keyboard use and simpler language across both apps.
- [ ] **Unreliable-network support:** Save report drafts and safely retry photo
  uploads when the connection returns.

## Later improvements

- [ ] **Public demand map and filters:** Browse demands by location, category,
  urgency and status while respecting district visibility rules.
- [ ] **Shareable demand pages:** Provide a public link to a demand's status,
  recorded funding, work updates and evidence, without exposing private data.
- [ ] **Abuse reports and moderation:** Let users flag harmful or misleading
  submissions and record how a moderator handled each flag.
- [ ] **Department workload view:** Highlight overdue work and cases waiting for
  staff action, with clear definitions for due dates and escalation.
- [ ] **Evidence-based impact summaries:** Show verified repairs and response
  times from project data, labelled by date and area; do not present projections
  or sample data as measured impact.

## Role-specific workflow and navigation improvements

Keep the [navigation proposal](docs/development/profile-navigation-design-2026-10-29.md):
section shortcuts, back-to-list controls, scoped list search/filtering, result
counts and reset controls. These remain planned, not implemented.

The [role workflow review](docs/development/profile-workflow-review-2026-10-29.md)
records source evidence, failure scenarios and the boundary between existing
features and new proposals.

- [ ] **Shared Demand Passport:** Link the report, cluster, ranking, recorded
  allocation, work and citizen verdict in one role-aware case history.
- [ ] **Next action and waiting reason:** Show the current responsible role and
  saved stage timing without inventing deadlines or automatic decisions.
- [ ] **Panchayat:** Compare candidate clusters using their actual evidence;
  support audited pre-clustering category corrections and clarification requests.
- [ ] **Department:** Track funded work through citizen verification and retain
  a decision receipt with the ranking inputs at allocation time.
- [ ] **Officer:** Show the reporter's correction comments with the relevant
  evidence round; add clearly defined completion checklists.
- [ ] **Student:** Return faculty feedback to the team, support invitations and
  submission revisions, and build an evidence-linked Civic Buildfolio.
- [ ] **Institute:** Show team readiness and roster details, with a recorded
  request-for-changes path as well as approval.
- [ ] **Faculty:** Add a civic feasibility rubric and version-specific revision
  feedback; keep adoption recommendations separate from official repair actions.
- [ ] **Industry/CSR:** Correct personal-versus-organisation scope wording and
  add pledge-to-outcome views only through explicit authorised relationships.
- [ ] **Government Admin:** Make historical audits navigable and show scoped
  handoff/correction bottlenecks with links to their evidence.
- [ ] **Super Admin:** Show compatible scope choices and a named old/new access
  comparison, including open-work constraints, before confirming changes.

## Production limitations

These are larger production goals, not requirements for demonstrating the current
prototype:

- [ ] Connect to verified government systems and workflows.
- [ ] Support real fund transfers; current allocations and pledges are records,
  not payments.
- [ ] Expand language, district, and organization support.
- [ ] Improve operation on unreliable internet and lower-end devices.
- [ ] Complete independent security and privacy reviews, backups, monitoring,
  and reliability planning.
- [ ] Measure outcomes through broader user testing and reliable real-world data.

Funding and repair-verification decisions should remain with authorized people.
AI may assist with suggestions, but should not make these decisions.
