"""Published five-factor ranking. No database, AI, or invented population data."""

from datetime import datetime
from math import expm1

from app.modules.problems.schemas import ScoreFactor

SEVERITY_SCORES = {"low": 30, "medium": 55, "high": 80, "critical": 100}


def score_cluster(
    *,
    supporters: int,
    severity: int,
    anchor_created_at: datetime,
    now: datetime,
    gap: float | None,
    equity: float | None,
    inputs_are_demo: bool,
    is_demo: bool,
) -> tuple[float, list[ScoreFactor]]:
    age_days = max(0.0, (now - anchor_created_at).total_seconds() / 86400)
    factors = [
        ScoreFactor(
            factor="support",
            label="Community support",
            score=-100 * expm1(-supporters / 60),
            weight=0.30,
            is_demo=is_demo,
        ),
        ScoreFactor(
            factor="gap",
            label="Infrastructure gap",
            score=50 if gap is None else gap,
            weight=0.22,
            is_demo=inputs_are_demo or gap is None,
        ),
        ScoreFactor(
            factor="equity",
            label="Equity",
            score=50 if equity is None else equity,
            weight=0.20,
            is_demo=inputs_are_demo or equity is None,
        ),
        ScoreFactor(
            factor="severity",
            label="Severity",
            score=severity,
            weight=0.18,
            is_demo=is_demo,
        ),
        ScoreFactor(
            factor="age",
            label="Age",
            score=min(100, age_days / 90 * 100),
            weight=0.10,
            is_demo=is_demo,
        ),
    ]
    return sum(factor.score * factor.weight for factor in factors), factors
