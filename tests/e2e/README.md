# End-to-end journeys

The only tests that do **not** live beside the code they test — a cross-service
journey belongs to no single service.

Everything else is colocated: `services/api/tests/`, `services/ai/tests/`,
`apps/mobile/test/`, and `*.test.tsx` next to the component. A top-level suite
mirroring the whole system rots, because nobody updates a test three directories
away from what they changed.

## What belongs here

The four demo-critical journeys, in priority order:

1. **Citizen report → cluster → rank** — a report is submitted, deduplicated
   against an existing cluster, and the cluster's rank updates
2. **Rank → problem statement → funding** — a department publishes a statement
   from a ranked cluster and allocates funds
3. **Student → team → project submission** — against a published statement
4. **Execution → citizen verification → ledger** — the loop closes publicly

## What does not

Per-role permission checks. Those are asserted directly in
`services/api/tests/unit/test_permissions.py` — nine roles times twenty
permissions through a browser would be slow and would tell you less.
