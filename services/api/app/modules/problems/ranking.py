"""Published six-factor ranking. No database, AI, or invented population data.

Six factors (weights sum to 1.0):
  support    0.27  — unique citizens who reported or explicitly supported
  gap        0.20  — infrastructure gap score set by the responsible department
  equity     0.18  — equity index set by the responsible department
  severity   0.16  — highest severity across cluster member reports
  age        0.09  — how long the anchor report has been open
  senior     0.10  — any member report flagged as affecting seniors/disability

senior_flag is transparent: it appears in score_breakdown so citizens and
staff can see exactly why a cluster received the bonus.
"""

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
    affects_seniors: bool = False,
) -> tuple[float, list[ScoreFactor]]:
    """`is_demo` marks only seeded or neutral-default *inputs* (gap, equity).

    Support, severity, age and senior_flag are computed from recorded data,
    so they are never labelled demo values, even when the records belong to
    the demo dataset.
    """
    age_days = max(0.0, (now - anchor_created_at).total_seconds() / 86400)
    factors = [
        ScoreFactor(
            factor="support",
            label="Community support",
            score=-100 * expm1(-supporters / 60),
            weight=0.27,
            is_demo=False,
        ),
        ScoreFactor(
            factor="gap",
            label="Infrastructure gap",
            score=50 if gap is None else gap,
            weight=0.20,
            is_demo=inputs_are_demo or gap is None,
        ),
        ScoreFactor(
            factor="equity",
            label="Equity",
            score=50 if equity is None else equity,
            weight=0.18,
            is_demo=inputs_are_demo or equity is None,
        ),
        ScoreFactor(
            factor="severity",
            label="Severity",
            score=severity,
            weight=0.16,
            is_demo=False,
        ),
        ScoreFactor(
            factor="age",
            label="Age",
            score=min(100, age_days / 90 * 100),
            weight=0.09,
            is_demo=False,
        ),
        ScoreFactor(
            factor="senior_flag",
            label="Affects seniors / disability",
            score=100 if affects_seniors else 0,
            weight=0.10,
            is_demo=False,
        ),
    ]
    return sum(factor.score * factor.weight for factor in factors), factors
