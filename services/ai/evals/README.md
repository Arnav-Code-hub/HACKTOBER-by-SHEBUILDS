# AI evaluation

**Evals are not tests.** Tests assert deterministic behaviour and run on every PR.
Evals measure *quality* against a golden set, produce a score you compare over
time, are non-deterministic, slow, and cost real money.

    make evals        # nightly + manual only, never on the PR path

## Layout

- `datasets/` — golden sets. Small ones are committed; anything large goes to
  object storage or DVC. Never commit model weights.
- `suites/` — one suite per capability, each declaring its metric and threshold.
- `report.py` — runs suites and prints a comparable score table.

## Metrics

| Capability | Metric | Why it is the one that matters |
|---|---|---|
| Classification | Macro F1 per category | Rare categories must not be drowned by common ones |
| Deduplication | Precision / recall | A false merge silences a real citizen; recall alone is misleading |
| Prioritisation | Rank correlation vs. human ranking | The public claim is a defensible ranking |
| Translation | chrF + spot review | Adequacy over fluency for civic text |
| Statement generation | Rubric score | Judged, not measured |

## Rule

A prompt change without a re-run eval is not reviewable. Attach the before/after
score table to the PR.
