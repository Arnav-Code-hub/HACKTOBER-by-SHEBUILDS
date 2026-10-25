# Architecture Decision Records

One file per significant decision: `NNNN-short-title.md`.

An ADR is how a disagreement gets resolved **once**. Without them the same
debate reopens every few weeks, and nobody can reconstruct what was already
considered and rejected.

## Format

```markdown
# NNNN. Title

Date: YYYY-MM-DD
Status: proposed | accepted | superseded by NNNN

## Context
What forces are in play? What did we know at the time?

## Decision
What we are doing.

## Consequences
What gets easier. What gets harder. What we accept as a cost.

## Alternatives considered
What we rejected, and why — this is the most valuable section.
```

A decision that turns out wrong is not edited. It is marked superseded, and the
replacement links back to it. The history is the point.
