"""Enums shared across modules.

Only genuinely cross-cutting values live here. A value used by one module
belongs in that module's schemas.py — this file is not a dumping ground.
"""

from enum import StrEnum


class ProblemStatus(StrEnum):
    """The agreed report lifecycle. Mirrored by the Flutter mapping in
    apps/mobile/lib/features/report/data/report_dto.dart and documented in
    docs/api/day1-frontend-contract.md — change all three together.

    VERIFIED means validated by the Panchayat. Citizen confirmation of a repair
    is CITIZEN_VERIFIED.
    """

    REPORTED = "reported"
    VERIFIED = "verified"
    REJECTED = "rejected"
    PRIORITISED = "prioritised"
    FUNDED = "funded"
    IN_PROGRESS = "in_progress"
    AWAITING_VERIFICATION = "awaiting_verification"
    CITIZEN_VERIFIED = "citizen_verified"


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
