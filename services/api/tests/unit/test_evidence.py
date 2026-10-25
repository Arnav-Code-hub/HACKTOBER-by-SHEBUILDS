import pytest

from app.core.errors import ConflictError
from app.core.evidence import EvidenceAsset, select
from app.shared.enums import ProblemStatus as Status

BEFORE = EvidenceAsset("before", "owned/before")
FIRST = EvidenceAsset("first", "owned/first")
SECOND = EvidenceAsset("second", "owned/second")


@pytest.mark.parametrize("status", [Status.FUNDED, Status.IN_PROGRESS])
def test_initial_work_has_no_after_or_card(status: Status) -> None:
    selected = select(before=BEFORE, status=status, round_=1, completions={})
    assert selected.after is None
    assert selected.verdict_label is None


@pytest.mark.parametrize(
    ("status", "label"),
    [
        (Status.AWAITING_VERIFICATION, "Awaiting citizen verification"),
        (Status.CITIZEN_VERIFIED, "Citizen verified"),
    ],
)
def test_current_completion_is_selected(status: Status, label: str) -> None:
    selected = select(before=BEFORE, status=status, round_=2, completions={1: FIRST, 2: SECOND})
    assert selected.after == SECOND
    assert selected.after_round == 2
    assert selected.verdict_label == label


def test_correction_selects_returned_photo_not_empty_current_round() -> None:
    selected = select(before=BEFORE, status=Status.IN_PROGRESS, round_=2, completions={1: FIRST})
    assert selected.after == FIRST
    assert selected.after_round == 1
    assert selected.verdict_label == "Round 1 · returned for correction"


def test_missing_completion_never_uses_another_round_as_proof() -> None:
    with pytest.raises(ConflictError):
        select(before=BEFORE, status=Status.CITIZEN_VERIFIED, round_=2, completions={1: FIRST})


def test_invalid_round_is_rejected() -> None:
    with pytest.raises(ValueError):
        select(before=BEFORE, status=Status.IN_PROGRESS, round_=0, completions={})


def test_a_report_without_photos_has_no_before_but_keeps_the_after_rule() -> None:
    # Report photos are optional; the selection never invents a before image.
    selected = select(
        before=None, status=Status.AWAITING_VERIFICATION, round_=1, completions={1: FIRST}
    )
    assert selected.before is None
    assert (selected.after, selected.after_round) == (FIRST, 1)
