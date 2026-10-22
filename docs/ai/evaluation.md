# AI evaluation

**Evals are not tests.** Tests assert deterministic behaviour and gate every PR.
Evals measure quality against a golden set, are non-deterministic, slow, and cost
real money. Nightly and manual only.

```bash
make evals                    # all suites
make evals suite=classification
```

## Metrics

| Capability | Metric | Why this one |
|---|---|---|
| Classification | Macro F1 per category | Rare categories must not be drowned by common ones |
| Deduplication | Precision **and** recall | A false merge silences a real citizen; recall alone hides that |
| Prioritisation | Rank correlation vs. human ranking | The public claim is a defensible ranking |
| Translation | chrF + spot review | Adequacy over fluency for civic text |
| Statement generation | Rubric score | Judged, not measured |
| OCR | Character error rate | Field photos, not scans |

## The review rule

**A prompt change without a re-run eval is not reviewable.** Prompts change model
behaviour the way code changes program behaviour. Paste the before/after score
table into the PR.

## Cost control

`DAILY_TOKEN_BUDGET` refuses calls past the cap. A runaway retry loop against a
paid API is a real way to lose a hackathon; the CI eval job sets a hard, lower
cap of its own.

## Safety

Citizen report text is **untrusted input reaching a model**. Prompts delimit it
explicitly and instruct the model to treat it as data. A report reading "ignore
previous instructions" must be classified as a report, not obeyed. Every model
output is validated against a Pydantic schema before anything persists it.

Golden datasets containing real reports must be anonymised: no names, no phone
numbers, no precise coordinates.
