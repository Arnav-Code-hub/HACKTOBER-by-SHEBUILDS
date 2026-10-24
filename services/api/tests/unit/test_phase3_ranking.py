from datetime import UTC, datetime, timedelta
from math import exp
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.problems.ranking import SEVERITY_SCORES, score_cluster
from app.modules.problems.schemas import AssignCluster, RankingInputs, ValidateReport
from app.shared.geo import cluster_radius_m, distance_m

NOW = datetime(2026, 10, 24, tzinfo=UTC)


def score(**overrides: object):
    values = {
        "supporters": 60,
        "severity": 80,
        "anchor_created_at": NOW - timedelta(days=45),
        "now": NOW,
        "gap": None,
        "equity": None,
        "inputs_are_demo": True,
        "is_demo": False,
    }
    return score_cluster(**(values | overrides))


def test_published_formula_and_neutral_defaults_are_explainable() -> None:
    total, factors = score()
    values = {factor.factor: factor for factor in factors}
    assert values["support"].score == pytest.approx(100 * (1 - exp(-1)))
    assert [factor.weight for factor in factors] == [0.30, 0.22, 0.20, 0.18, 0.10]
    assert total == pytest.approx(
        0.30 * 100 * (1 - exp(-1)) + 0.22 * 50 + 0.20 * 50 + 0.18 * 80 + 0.10 * 50
    )
    assert values["gap"].score == values["equity"].score == 50
    assert values["gap"].is_demo and values["equity"].is_demo
    assert not values["support"].is_demo
    assert SEVERITY_SCORES == {"low": 30, "medium": 55, "high": 80, "critical": 100}


@pytest.mark.parametrize(("days", "expected"), [(-2, 0), (0, 0), (45, 50), (90, 100), (200, 100)])
def test_age_is_bounded_and_uses_fractional_elapsed_days(days: int, expected: int) -> None:
    _, factors = score(anchor_created_at=NOW - timedelta(days=days))
    assert factors[-1].score == expected


def test_official_inputs_and_seed_provenance_are_independent() -> None:
    total, factors = score(gap=0, equity=100, inputs_are_demo=False, is_demo=True)
    assert 0 <= total <= 100
    assert [factor.is_demo for factor in factors] == [True, False, False, True, True]
    _, factors = score(gap=None, equity=25, inputs_are_demo=False)
    assert factors[1].is_demo and not factors[2].is_demo


def test_support_saturates_without_becoming_a_population_estimate() -> None:
    assert score(supporters=0)[1][0].score == 0
    assert score(supporters=100000)[1][0].score == 100


def test_distance_and_category_radii() -> None:
    assert distance_m(16.76, 77.14, 16.76, 77.14) == 0
    assert distance_m(0, 0, 0.001, 0) == pytest.approx(111.195, abs=0.01)
    assert distance_m(0, 179.999, 0, -179.999) == pytest.approx(222.39, abs=0.01)
    assert distance_m(0, 0, 0, 180) == pytest.approx(20_015_114, abs=1)
    assert cluster_radius_m("water") == cluster_radius_m("lighting") == 100
    assert cluster_radius_m("roads") == cluster_radius_m("sanitation") == 500


@pytest.mark.parametrize(
    "body",
    [{}, {"new": False}, {"new": 1}, {"new": "true"}, {"new": True, "cluster_id": str(uuid4())}],
)
def test_cluster_target_must_be_explicit_and_unambiguous(body: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AssignCluster.model_validate(body)


@pytest.mark.parametrize("value", [-1, 101, True, "50", float("nan"), float("inf")])
def test_ranking_inputs_reject_invalid_numbers(value: object) -> None:
    with pytest.raises(ValidationError):
        RankingInputs.model_validate({"infrastructure_gap": value, "equity_index": 50})


def test_rejection_requires_a_visible_reason() -> None:
    with pytest.raises(ValidationError):
        ValidateReport.model_validate({"decision": "reject", "reason": " "})
    assert AssignCluster.model_validate({"cluster_id": str(uuid4())}).cluster_id is not None
