"""Enums shared across modules.

Only genuinely cross-cutting values live here. A value used by one module
belongs in that module's schemas.py — this file is not a dumping ground.
"""

from enum import StrEnum


class ProblemStatus(StrEnum):
    REPORTED = "reported"
    CLUSTERED = "clustered"
    RANKED = "ranked"
    FUNDED = "funded"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Language(StrEnum):
    """Languages the citizen app and AI pipeline support."""

    EN = "en"
    HI = "hi"
    MR = "mr"
    BN = "bn"
    TA = "ta"
    TE = "te"
    KN = "kn"
    GU = "gu"
