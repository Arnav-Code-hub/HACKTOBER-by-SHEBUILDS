"""Pure evidence selection shared by future views and Cloudinary cards.

Supply owned, authorized assets sorted into their original completion rounds.
This module never trusts a URL supplied by the browser.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from app.core.errors import ConflictError
from app.shared.enums import ProblemStatus as Status


@dataclass(frozen=True)
class EvidenceAsset:
    asset_id: str
    public_id: str


@dataclass(frozen=True)
class EvidenceSelection:
    before: EvidenceAsset
    after: EvidenceAsset | None
    after_round: int | None
    verdict_label: str | None


def select(
    *,
    before: EvidenceAsset,
    status: Status,
    round_: int,
    completions: Mapping[int, EvidenceAsset],
) -> EvidenceSelection:
    """Select the same after image for the endpoint, verification view and card."""
    if round_ < 1:
        raise ValueError("Verification rounds start at 1")
    if status in {Status.AWAITING_VERIFICATION, Status.CITIZEN_VERIFIED}:
        selected_round = round_
        label = (
            "Citizen verified"
            if status == Status.CITIZEN_VERIFIED
            else "Awaiting citizen verification"
        )
    elif status == Status.IN_PROGRESS and round_ > 1:
        selected_round = round_ - 1
        label = f"Round {selected_round} · returned for correction"
    elif status in {Status.FUNDED, Status.IN_PROGRESS}:
        return EvidenceSelection(before, None, None, None)
    else:
        raise ValueError("Evidence requires an assigned work order")
    after = completions.get(selected_round)
    if after is None:
        raise ConflictError("Completion evidence is missing for this round.")
    return EvidenceSelection(before, after, selected_round, label)
